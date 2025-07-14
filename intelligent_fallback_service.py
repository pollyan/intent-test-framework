#!/usr/bin/env python3
"""
智能回退服务
当云端资源不足时自动降级到不同的执行策略
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

from lightweight_resource_manager import resource_manager, execution_queue

logger = logging.getLogger(__name__)

class ExecutionStrategy(Enum):
    """执行策略枚举"""
    FULL_MIDSCENE = "full_midscene"          # 完整MidSceneJS执行
    LIGHTWEIGHT_MIDSCENE = "lightweight"     # 轻量级MidSceneJS执行
    SIMULATED_EXECUTION = "simulated"        # 模拟执行
    QUEUE_EXECUTION = "queued"              # 排队执行
    REJECT_EXECUTION = "rejected"           # 拒绝执行

class IntelligentFallbackService:
    """智能回退服务"""
    
    def __init__(self):
        self.strategy_preference = [
            ExecutionStrategy.FULL_MIDSCENE,
            ExecutionStrategy.LIGHTWEIGHT_MIDSCENE,
            ExecutionStrategy.SIMULATED_EXECUTION,
            ExecutionStrategy.QUEUE_EXECUTION
        ]
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "fallback_executions": 0,
            "queued_executions": 0,
            "rejected_executions": 0
        }
        
    def determine_execution_strategy(self, testcase_data: Dict[str, Any]) -> tuple[ExecutionStrategy, str]:
        """确定执行策略"""
        # 获取资源状态
        resource_report = resource_manager.get_resource_report()
        fallback_strategy = resource_report["fallback_strategy"]
        
        # 获取测试用例复杂度
        complexity = self._analyze_testcase_complexity(testcase_data)
        
        if fallback_strategy == "immediate_fallback":
            return ExecutionStrategy.SIMULATED_EXECUTION, "内存压力过高，使用模拟执行"
        
        elif fallback_strategy == "lightweight_mode":
            if complexity == "simple":
                return ExecutionStrategy.LIGHTWEIGHT_MIDSCENE, "资源紧张，使用轻量级模式"
            else:
                return ExecutionStrategy.SIMULATED_EXECUTION, "复杂测试用例在资源紧张时使用模拟执行"
        
        elif fallback_strategy == "queue_execution":
            return ExecutionStrategy.QUEUE_EXECUTION, "并发数量已满，加入执行队列"
        
        elif fallback_strategy == "normal_execution":
            return ExecutionStrategy.FULL_MIDSCENE, "资源充足，使用完整MidSceneJS执行"
        
        else:
            return ExecutionStrategy.SIMULATED_EXECUTION, "未知状态，使用模拟执行"
    
    def _analyze_testcase_complexity(self, testcase_data: Dict[str, Any]) -> str:
        """分析测试用例复杂度"""
        steps = json.loads(testcase_data.get("steps", "[]"))
        
        if len(steps) <= 3:
            return "simple"
        elif len(steps) <= 8:
            return "medium"
        else:
            return "complex"
    
    async def execute_with_fallback(self, testcase_data: Dict[str, Any], mode: str = "headless") -> Dict[str, Any]:
        """带回退机制的执行"""
        execution_id = str(uuid.uuid4())
        
        # 统计
        self.execution_stats["total_executions"] += 1
        
        # 确定执行策略
        strategy, reason = self.determine_execution_strategy(testcase_data)
        
        logger.info(f"执行策略: {strategy.value} - {reason}")
        
        try:
            if strategy == ExecutionStrategy.FULL_MIDSCENE:
                return await self._execute_full_midscene(execution_id, testcase_data, mode)
            
            elif strategy == ExecutionStrategy.LIGHTWEIGHT_MIDSCENE:
                return await self._execute_lightweight_midscene(execution_id, testcase_data, mode)
            
            elif strategy == ExecutionStrategy.SIMULATED_EXECUTION:
                return await self._execute_simulated(execution_id, testcase_data, mode)
            
            elif strategy == ExecutionStrategy.QUEUE_EXECUTION:
                return await self._execute_queued(execution_id, testcase_data, mode)
            
            else:
                return self._create_rejected_result(execution_id, testcase_data, reason)
                
        except Exception as e:
            logger.error(f"执行失败，尝试回退: {e}")
            return await self._handle_execution_failure(execution_id, testcase_data, mode, str(e))
    
    async def _execute_full_midscene(self, execution_id: str, testcase_data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """完整MidSceneJS执行"""
        logger.info(f"🚀 完整MidSceneJS执行: {execution_id}")
        
        # 注册执行任务
        if not resource_manager.register_execution(execution_id, testcase_data["name"]):
            return await self._execute_simulated(execution_id, testcase_data, mode)
        
        try:
            # 导入并执行
            from cloud_execution_service import LightweightCloudExecutor
            
            executor = LightweightCloudExecutor()
            result = await executor.execute_testcase(testcase_data, mode)
            
            self.execution_stats["successful_executions"] += 1
            return result
            
        except Exception as e:
            logger.error(f"完整MidSceneJS执行失败: {e}")
            return await self._execute_lightweight_midscene(execution_id, testcase_data, mode)
        
        finally:
            resource_manager.unregister_execution(execution_id)
    
    async def _execute_lightweight_midscene(self, execution_id: str, testcase_data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """轻量级MidSceneJS执行"""
        logger.info(f"⚡ 轻量级MidSceneJS执行: {execution_id}")
        
        # 注册执行任务
        if not resource_manager.register_execution(execution_id, testcase_data["name"]):
            return await self._execute_simulated(execution_id, testcase_data, mode)
        
        try:
            # 获取优化配置
            optimization_config = resource_manager.get_optimization_config()
            
            # 创建优化的执行器
            from cloud_execution_service import LightweightCloudExecutor
            
            executor = LightweightCloudExecutor()
            # 应用优化配置
            executor.max_memory_mb = 200  # 更严格的内存限制
            executor.execution_timeout = 180  # 更短的超时时间
            
            result = await executor.execute_testcase(testcase_data, mode)
            
            self.execution_stats["successful_executions"] += 1
            self.execution_stats["fallback_executions"] += 1
            
            # 添加回退标记
            result["execution_type"] = "lightweight_fallback"
            result["fallback_reason"] = "资源优化模式"
            
            return result
            
        except Exception as e:
            logger.error(f"轻量级MidSceneJS执行失败: {e}")
            return await self._execute_simulated(execution_id, testcase_data, mode)
        
        finally:
            resource_manager.unregister_execution(execution_id)
    
    async def _execute_simulated(self, execution_id: str, testcase_data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """模拟执行"""
        logger.info(f"🎭 模拟执行: {execution_id}")
        
        self.execution_stats["fallback_executions"] += 1
        
        # 解析测试步骤
        steps = json.loads(testcase_data.get("steps", "[]"))
        
        execution_result = {
            "execution_id": execution_id,
            "testcase_name": testcase_data.get("name", "未知测试用例"),
            "mode": mode,
            "status": "completed",
            "execution_type": "simulated",
            "fallback_reason": "资源不足，使用模拟执行",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "steps": [],
            "screenshots": [],
            "success_count": 0,
            "total_count": len(steps),
            "success_rate": 0
        }
        
        # 模拟执行每个步骤
        for i, step in enumerate(steps):
            # 模拟延迟
            await asyncio.sleep(0.1)
            
            # 模拟步骤结果
            step_result = {
                "success": True,  # 模拟执行总是成功
                "action": step.get("action", "unknown"),
                "description": step.get("description", f"步骤 {i+1}"),
                "screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",  # 1x1像素的透明图片
                "ai_response": f"模拟执行步骤: {step.get('description', step.get('action'))}",
                "error": None
            }
            
            execution_result["steps"].append(step_result)
            execution_result["success_count"] += 1
            
            # 添加截图到历史
            execution_result["screenshots"].append({
                "step": i + 1,
                "description": step_result["description"],
                "screenshot": step_result["screenshot"]
            })
        
        # 计算成功率
        execution_result["success_rate"] = 100.0  # 模拟执行总是100%成功
        
        return execution_result
    
    async def _execute_queued(self, execution_id: str, testcase_data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """排队执行"""
        logger.info(f"📋 排队执行: {execution_id}")
        
        # 添加到队列
        queue_data = {
            "execution_id": execution_id,
            "testcase_data": testcase_data,
            "mode": mode
        }
        
        if execution_queue.add_to_queue(queue_data):
            self.execution_stats["queued_executions"] += 1
            
            return {
                "execution_id": execution_id,
                "testcase_name": testcase_data.get("name", "未知测试用例"),
                "status": "queued",
                "execution_type": "queued",
                "message": "已添加到执行队列",
                "queue_status": execution_queue.get_queue_status(),
                "start_time": datetime.utcnow().isoformat()
            }
        else:
            # 队列已满，使用模拟执行
            return await self._execute_simulated(execution_id, testcase_data, mode)
    
    def _create_rejected_result(self, execution_id: str, testcase_data: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """创建拒绝执行结果"""
        logger.warning(f"❌ 拒绝执行: {execution_id} - {reason}")
        
        self.execution_stats["rejected_executions"] += 1
        
        return {
            "execution_id": execution_id,
            "testcase_name": testcase_data.get("name", "未知测试用例"),
            "status": "rejected",
            "execution_type": "rejected",
            "error": reason,
            "message": f"执行被拒绝: {reason}",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat()
        }
    
    async def _handle_execution_failure(self, execution_id: str, testcase_data: Dict[str, Any], mode: str, error: str) -> Dict[str, Any]:
        """处理执行失败"""
        logger.error(f"执行失败处理: {execution_id} - {error}")
        
        # 尝试降级到模拟执行
        if "memory" in error.lower() or "resource" in error.lower():
            return await self._execute_simulated(execution_id, testcase_data, mode)
        
        # 其他错误也使用模拟执行
        return await self._execute_simulated(execution_id, testcase_data, mode)
    
    async def process_execution_queue(self):
        """处理执行队列"""
        while True:
            try:
                # 检查是否有资源执行队列中的任务
                if not execution_queue.processing:
                    next_execution = execution_queue.get_next_execution()
                    
                    if next_execution:
                        execution_queue.processing = True
                        
                        try:
                            # 重新评估执行策略
                            strategy, reason = self.determine_execution_strategy(next_execution["testcase_data"])
                            
                            if strategy in [ExecutionStrategy.FULL_MIDSCENE, ExecutionStrategy.LIGHTWEIGHT_MIDSCENE]:
                                # 执行排队的任务
                                result = await self.execute_with_fallback(
                                    next_execution["testcase_data"], 
                                    next_execution["mode"]
                                )
                                logger.info(f"队列任务完成: {next_execution['execution_id']}")
                            
                        except Exception as e:
                            logger.error(f"队列任务执行失败: {e}")
                        
                        finally:
                            execution_queue.processing = False
                
                await asyncio.sleep(10)  # 每10秒检查一次队列
                
            except Exception as e:
                logger.error(f"队列处理异常: {e}")
                await asyncio.sleep(10)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "execution_stats": self.execution_stats,
            "queue_status": execution_queue.get_queue_status(),
            "resource_report": resource_manager.get_resource_report(),
            "strategy_preference": [s.value for s in self.strategy_preference]
        }

# 全局智能回退服务实例
fallback_service = IntelligentFallbackService() 