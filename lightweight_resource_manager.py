#!/usr/bin/env python3
"""
轻量级资源管理器
针对免费云服务器的资源监控和优化
"""

import asyncio
import psutil
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class ResourceManager:
    """资源管理器 - 监控和优化云端执行资源使用"""
    
    def __init__(self, 
                 max_memory_mb: int = 400,
                 max_execution_time: int = 300,
                 max_concurrent_executions: int = 2):
        self.max_memory_mb = max_memory_mb
        self.max_execution_time = max_execution_time
        self.max_concurrent_executions = max_concurrent_executions
        self.active_executions: Dict[str, Dict] = {}
        self.resource_history: List[Dict] = []
        self.optimization_enabled = True
        
    def get_system_resources(self) -> Dict[str, float]:
        """获取系统资源使用情况"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "memory_used_mb": memory.used / 1024 / 1024,
                "memory_available_mb": memory.available / 1024 / 1024,
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"获取系统资源失败: {e}")
            return {}
    
    def check_resource_limits(self) -> Dict[str, bool]:
        """检查资源限制"""
        resources = self.get_system_resources()
        
        return {
            "memory_ok": resources.get("memory_used_mb", 0) < self.max_memory_mb,
            "cpu_ok": resources.get("cpu_percent", 0) < 80,
            "disk_ok": resources.get("disk_usage_percent", 0) < 90,
            "concurrent_ok": len(self.active_executions) < self.max_concurrent_executions
        }
    
    def can_start_execution(self) -> tuple[bool, str]:
        """检查是否可以启动新的执行"""
        limits = self.check_resource_limits()
        
        if not limits["memory_ok"]:
            return False, "内存使用超过限制"
        if not limits["cpu_ok"]:
            return False, "CPU使用率过高"
        if not limits["concurrent_ok"]:
            return False, "并发执行数量超过限制"
        
        return True, "资源充足"
    
    def register_execution(self, execution_id: str, testcase_name: str) -> bool:
        """注册执行任务"""
        can_start, reason = self.can_start_execution()
        if not can_start:
            logger.warning(f"无法启动执行 {execution_id}: {reason}")
            return False
        
        self.active_executions[execution_id] = {
            "testcase_name": testcase_name,
            "start_time": datetime.utcnow(),
            "last_heartbeat": datetime.utcnow(),
            "memory_at_start": self.get_system_resources().get("memory_used_mb", 0)
        }
        
        logger.info(f"注册执行任务: {execution_id} - {testcase_name}")
        return True
    
    def update_execution_heartbeat(self, execution_id: str):
        """更新执行心跳"""
        if execution_id in self.active_executions:
            self.active_executions[execution_id]["last_heartbeat"] = datetime.utcnow()
    
    def unregister_execution(self, execution_id: str) -> Optional[Dict]:
        """注销执行任务"""
        if execution_id in self.active_executions:
            execution_info = self.active_executions.pop(execution_id)
            execution_info["end_time"] = datetime.utcnow()
            execution_info["duration"] = (execution_info["end_time"] - execution_info["start_time"]).total_seconds()
            
            # 记录到历史
            self.resource_history.append({
                "execution_id": execution_id,
                "testcase_name": execution_info["testcase_name"],
                "duration": execution_info["duration"],
                "memory_used": execution_info["memory_at_start"],
                "timestamp": execution_info["end_time"].isoformat()
            })
            
            logger.info(f"注销执行任务: {execution_id}")
            return execution_info
        
        return None
    
    def cleanup_stale_executions(self):
        """清理过期的执行任务"""
        current_time = datetime.utcnow()
        stale_executions = []
        
        for execution_id, info in self.active_executions.items():
            # 检查超时
            if (current_time - info["start_time"]).total_seconds() > self.max_execution_time:
                stale_executions.append(execution_id)
                logger.warning(f"执行超时: {execution_id}")
            # 检查心跳
            elif (current_time - info["last_heartbeat"]).total_seconds() > 60:
                stale_executions.append(execution_id)
                logger.warning(f"执行心跳超时: {execution_id}")
        
        for execution_id in stale_executions:
            self.unregister_execution(execution_id)
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """获取优化配置"""
        resources = self.get_system_resources()
        memory_pressure = resources.get("memory_percent", 0)
        
        if memory_pressure > 80:
            # 高内存压力 - 极度优化
            return {
                "browser_args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage", 
                    "--disable-gpu",
                    "--disable-web-security",
                    "--single-process",
                    "--memory-pressure-off",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=VizDisplayCompositor,TranslateUI",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images"  # 禁用图片加载
                ],
                "viewport": {"width": 800, "height": 600},
                "screenshot_quality": 60,
                "step_delay": 0.2,
                "timeout": 15
            }
        elif memory_pressure > 60:
            # 中等内存压力 - 标准优化
            return {
                "browser_args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--single-process",
                    "--memory-pressure-off"
                ],
                "viewport": {"width": 1024, "height": 768},
                "screenshot_quality": 80,
                "step_delay": 0.5,
                "timeout": 30
            }
        else:
            # 低内存压力 - 标准配置
            return {
                "browser_args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ],
                "viewport": {"width": 1280, "height": 720},
                "screenshot_quality": 90,
                "step_delay": 1.0,
                "timeout": 30
            }
    
    def suggest_fallback_strategy(self) -> str:
        """建议回退策略"""
        resources = self.get_system_resources()
        memory_pressure = resources.get("memory_percent", 0)
        
        if memory_pressure > 90:
            return "immediate_fallback"  # 立即回退到模拟执行
        elif memory_pressure > 80:
            return "lightweight_mode"   # 轻量级模式
        elif len(self.active_executions) >= self.max_concurrent_executions:
            return "queue_execution"    # 排队执行
        else:
            return "normal_execution"   # 正常执行
    
    def get_resource_report(self) -> Dict[str, Any]:
        """获取资源报告"""
        current_resources = self.get_system_resources()
        
        return {
            "current_resources": current_resources,
            "active_executions": len(self.active_executions),
            "resource_limits": self.check_resource_limits(),
            "optimization_config": self.get_optimization_config(),
            "fallback_strategy": self.suggest_fallback_strategy(),
            "history_count": len(self.resource_history),
            "average_duration": sum(h["duration"] for h in self.resource_history[-10:]) / min(10, len(self.resource_history)) if self.resource_history else 0
        }
    
    async def monitor_resources(self, interval: int = 30):
        """资源监控循环"""
        while True:
            try:
                # 清理过期执行
                self.cleanup_stale_executions()
                
                # 记录资源使用
                resources = self.get_system_resources()
                if resources:
                    logger.info(f"资源使用 - 内存: {resources['memory_percent']:.1f}%, CPU: {resources['cpu_percent']:.1f}%")
                
                # 检查资源压力
                if resources.get("memory_percent", 0) > 90:
                    logger.warning("⚠️ 内存压力过高，建议停止新的执行")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"资源监控异常: {e}")
                await asyncio.sleep(interval)

class ExecutionQueue:
    """执行队列管理器"""
    
    def __init__(self, max_size: int = 10):
        self.queue: List[Dict] = []
        self.max_size = max_size
        self.processing = False
    
    def add_to_queue(self, execution_data: Dict) -> bool:
        """添加到队列"""
        if len(self.queue) >= self.max_size:
            return False
        
        execution_data["queued_at"] = datetime.utcnow().isoformat()
        self.queue.append(execution_data)
        return True
    
    def get_next_execution(self) -> Optional[Dict]:
        """获取下一个执行任务"""
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            "queue_size": len(self.queue),
            "max_size": self.max_size,
            "is_processing": self.processing,
            "estimated_wait_time": len(self.queue) * 60  # 估算等待时间（秒）
        }

# 全局资源管理器实例
resource_manager = ResourceManager()
execution_queue = ExecutionQueue() 