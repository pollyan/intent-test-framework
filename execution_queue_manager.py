#!/usr/bin/env python3
"""
执行队列管理器
支持异步执行和结果缓存，针对免费云服务器优化
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import uuid

from lightweight_resource_manager import resource_manager, execution_queue
from intelligent_fallback_service import fallback_service

logger = logging.getLogger(__name__)

class ExecutionCache:
    """执行结果缓存"""
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.access_times: Dict[str, datetime] = {}
        
    def _generate_cache_key(self, testcase_data: Dict[str, Any], mode: str) -> str:
        """生成缓存键"""
        # 使用测试用例内容和模式生成唯一键
        content = json.dumps({
            'name': testcase_data.get('name', ''),
            'steps': testcase_data.get('steps', ''),
            'mode': mode
        }, sort_keys=True)
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, testcase_data: Dict[str, Any], mode: str) -> Optional[Dict]:
        """获取缓存结果"""
        cache_key = self._generate_cache_key(testcase_data, mode)
        
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            cache_time = datetime.fromisoformat(cached_result['cached_at'])
            
            # 检查是否过期
            if datetime.utcnow() - cache_time < timedelta(hours=self.ttl_hours):
                self.access_times[cache_key] = datetime.utcnow()
                logger.info(f"缓存命中: {cache_key[:8]}...")
                return cached_result['result']
            else:
                # 过期删除
                del self.cache[cache_key]
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
        
        return None
    
    def set(self, testcase_data: Dict[str, Any], mode: str, result: Dict):
        """设置缓存结果"""
        cache_key = self._generate_cache_key(testcase_data, mode)
        
        # 清理过期缓存
        self._cleanup_expired()
        
        # 如果缓存满了，删除最少访问的
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # 添加到缓存
        self.cache[cache_key] = {
            'result': result,
            'cached_at': datetime.utcnow().isoformat(),
            'testcase_name': testcase_data.get('name', '未知')
        }
        self.access_times[cache_key] = datetime.utcnow()
        
        logger.info(f"缓存存储: {cache_key[:8]}... - {testcase_data.get('name', '未知')}")
    
    def _cleanup_expired(self):
        """清理过期缓存"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for cache_key, cached_data in self.cache.items():
            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if current_time - cache_time >= timedelta(hours=self.ttl_hours):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
    
    def _evict_lru(self):
        """驱逐最少访问的缓存"""
        if not self.access_times:
            return
        
        # 找到最少访问的键
        lru_key = min(self.access_times, key=self.access_times.get)
        
        del self.cache[lru_key]
        del self.access_times[lru_key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        current_time = datetime.utcnow()
        
        # 计算缓存命中率（简化实现）
        total_size = len(self.cache)
        
        return {
            'total_cached': total_size,
            'max_size': self.max_size,
            'ttl_hours': self.ttl_hours,
            'cache_usage': f"{total_size}/{self.max_size}"
        }

class AsyncExecutionManager:
    """异步执行管理器"""
    
    def __init__(self):
        self.running_executions: Dict[str, Dict] = {}
        self.completed_executions: Dict[str, Dict] = {}
        self.execution_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.cache = ExecutionCache()
        self.background_thread = None
        self.shutdown_event = threading.Event()
        
    def start_background_processor(self):
        """启动后台处理器"""
        if self.background_thread is None or not self.background_thread.is_alive():
            self.background_thread = threading.Thread(target=self._background_processor)
            self.background_thread.daemon = True
            self.background_thread.start()
            logger.info("后台执行处理器已启动")
    
    def stop_background_processor(self):
        """停止后台处理器"""
        self.shutdown_event.set()
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=10)
            logger.info("后台执行处理器已停止")
    
    def _background_processor(self):
        """后台处理器线程"""
        while not self.shutdown_event.is_set():
            try:
                # 处理执行队列
                self._process_queue()
                
                # 清理完成的执行
                self._cleanup_completed_executions()
                
                # 等待一段时间再继续
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"后台处理器异常: {e}")
                time.sleep(10)
    
    def _process_queue(self):
        """处理执行队列"""
        if execution_queue.processing:
            return
        
        next_execution = execution_queue.get_next_execution()
        if not next_execution:
            return
        
        execution_id = next_execution['execution_id']
        testcase_data = next_execution['testcase_data']
        mode = next_execution['mode']
        
        logger.info(f"从队列中处理执行: {execution_id}")
        
        # 检查缓存
        cached_result = self.cache.get(testcase_data, mode)
        if cached_result:
            # 使用缓存结果
            result = cached_result.copy()
            result['execution_id'] = execution_id
            result['from_cache'] = True
            result['cached_execution'] = True
            
            self.completed_executions[execution_id] = result
            self._notify_callbacks(execution_id, result)
            return
        
        # 标记为处理中
        execution_queue.processing = True
        
        try:
            # 异步执行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    fallback_service.execute_with_fallback(testcase_data, mode)
                )
                
                # 更新结果
                result['execution_id'] = execution_id
                result['from_queue'] = True
                
                # 缓存结果
                if result.get('status') == 'completed':
                    self.cache.set(testcase_data, mode, result)
                
                self.completed_executions[execution_id] = result
                self._notify_callbacks(execution_id, result)
                
                logger.info(f"队列执行完成: {execution_id}")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"队列执行失败: {execution_id} - {e}")
            
            # 创建失败结果
            error_result = {
                'execution_id': execution_id,
                'status': 'failed',
                'error': str(e),
                'from_queue': True,
                'end_time': datetime.utcnow().isoformat()
            }
            
            self.completed_executions[execution_id] = error_result
            self._notify_callbacks(execution_id, error_result)
            
        finally:
            execution_queue.processing = False
    
    def _cleanup_completed_executions(self):
        """清理完成的执行记录"""
        current_time = datetime.utcnow()
        cleanup_threshold = timedelta(hours=1)  # 1小时后清理
        
        cleanup_keys = []
        for execution_id, result in self.completed_executions.items():
            if 'end_time' in result:
                end_time = datetime.fromisoformat(result['end_time'])
                if current_time - end_time > cleanup_threshold:
                    cleanup_keys.append(execution_id)
        
        for key in cleanup_keys:
            del self.completed_executions[key]
            if key in self.execution_callbacks:
                del self.execution_callbacks[key]
    
    def _notify_callbacks(self, execution_id: str, result: Dict):
        """通知回调函数"""
        callbacks = self.execution_callbacks.get(execution_id, [])
        for callback in callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
    
    def submit_execution(self, testcase_data: Dict[str, Any], mode: str = "headless", 
                        callback: Optional[Callable] = None) -> str:
        """提交执行任务"""
        execution_id = str(uuid.uuid4())
        
        # 检查缓存
        cached_result = self.cache.get(testcase_data, mode)
        if cached_result:
            # 立即返回缓存结果
            result = cached_result.copy()
            result['execution_id'] = execution_id
            result['from_cache'] = True
            result['cached_execution'] = True
            
            self.completed_executions[execution_id] = result
            
            if callback:
                callback(result)
            
            return execution_id
        
        # 注册回调
        if callback:
            self.execution_callbacks[execution_id].append(callback)
        
        # 检查是否可以立即执行
        can_execute, reason = resource_manager.can_start_execution()
        
        if can_execute:
            # 立即执行
            self.running_executions[execution_id] = {
                'testcase_data': testcase_data,
                'mode': mode,
                'start_time': datetime.utcnow().isoformat(),
                'status': 'running'
            }
            
            # 在后台线程中执行
            thread = threading.Thread(
                target=self._execute_in_background,
                args=(execution_id, testcase_data, mode)
            )
            thread.daemon = True
            thread.start()
            
        else:
            # 添加到队列
            queue_data = {
                'execution_id': execution_id,
                'testcase_data': testcase_data,
                'mode': mode
            }
            
            if execution_queue.add_to_queue(queue_data):
                logger.info(f"执行任务已加入队列: {execution_id} - {reason}")
            else:
                # 队列满了，返回错误
                error_result = {
                    'execution_id': execution_id,
                    'status': 'rejected',
                    'error': '执行队列已满',
                    'end_time': datetime.utcnow().isoformat()
                }
                
                self.completed_executions[execution_id] = error_result
                if callback:
                    callback(error_result)
        
        return execution_id
    
    def _execute_in_background(self, execution_id: str, testcase_data: Dict[str, Any], mode: str):
        """在后台执行任务"""
        try:
            # 注册执行任务
            if not resource_manager.register_execution(execution_id, testcase_data['name']):
                raise Exception("无法注册执行任务")
            
            # 创建事件循环执行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    fallback_service.execute_with_fallback(testcase_data, mode)
                )
                
                # 更新结果
                result['execution_id'] = execution_id
                result['from_background'] = True
                
                # 缓存结果
                if result.get('status') == 'completed':
                    self.cache.set(testcase_data, mode, result)
                
                self.completed_executions[execution_id] = result
                self._notify_callbacks(execution_id, result)
                
                logger.info(f"后台执行完成: {execution_id}")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"后台执行失败: {execution_id} - {e}")
            
            # 创建失败结果
            error_result = {
                'execution_id': execution_id,
                'status': 'failed',
                'error': str(e),
                'from_background': True,
                'end_time': datetime.utcnow().isoformat()
            }
            
            self.completed_executions[execution_id] = error_result
            self._notify_callbacks(execution_id, error_result)
            
        finally:
            # 清理
            if execution_id in self.running_executions:
                del self.running_executions[execution_id]
            resource_manager.unregister_execution(execution_id)
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """获取执行状态"""
        # 检查正在运行的执行
        if execution_id in self.running_executions:
            return self.running_executions[execution_id]
        
        # 检查完成的执行
        if execution_id in self.completed_executions:
            return self.completed_executions[execution_id]
        
        # 检查队列中的执行
        for queued_item in execution_queue.queue:
            if queued_item['execution_id'] == execution_id:
                return {
                    'execution_id': execution_id,
                    'status': 'queued',
                    'queued_at': queued_item['queued_at'],
                    'queue_position': execution_queue.queue.index(queued_item) + 1
                }
        
        return None
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            'running_executions': len(self.running_executions),
            'completed_executions': len(self.completed_executions),
            'queue_status': execution_queue.get_queue_status(),
            'cache_stats': self.cache.get_cache_stats(),
            'background_processor_running': self.background_thread and self.background_thread.is_alive(),
            'total_callbacks': sum(len(callbacks) for callbacks in self.execution_callbacks.values())
        }

# 全局异步执行管理器实例
async_execution_manager = AsyncExecutionManager()

# 启动后台处理器
async_execution_manager.start_background_processor() 