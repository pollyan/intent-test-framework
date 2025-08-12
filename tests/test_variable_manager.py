#!/usr/bin/env python3
"""
测试用的内存VariableManager
不依赖数据库，纯内存操作
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class TestVariableManager:
    """测试用的变量管理器（纯内存版本）"""
    
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._cache = OrderedDict()  # LRU缓存
        self._cache_lock = Lock()
        self._max_cache_size = 1000
        
        logger.info(f"初始化测试变量管理器: execution_id={execution_id}")
    
    def store_variable(
        self,
        variable_name: str,
        value: Any,
        source_step_index: int,
        source_api_method: Optional[str] = None,
        source_api_params: Optional[Dict] = None
    ) -> bool:
        """存储变量到内存缓存"""
        try:
            with self._cache_lock:
                # 检测数据类型
                data_type = self._detect_data_type(value)
                
                # 存储到缓存
                self._update_cache(variable_name, {
                    'value': value,
                    'data_type': data_type,
                    'source_step_index': source_step_index,
                    'source_api_method': source_api_method,
                    'metadata': {
                        'created_at': datetime.utcnow().isoformat(),
                        'source_api_params': source_api_params or {}
                    }
                })
                
                logger.info(f"变量存储成功: {variable_name} = {value} (类型: {data_type})")
                return True
                
        except Exception as e:
            logger.error(f"变量存储失败: {variable_name}, 错误: {str(e)}")
            return False
    
    def get_variable(self, variable_name: str) -> Optional[Any]:
        """获取变量值（从缓存）"""
        try:
            with self._cache_lock:
                if variable_name in self._cache:
                    # 移动到末尾（LRU更新）
                    cache_entry = self._cache.pop(variable_name)
                    self._cache[variable_name] = cache_entry
                    return cache_entry['value']
                
                logger.warning(f"变量不存在: {variable_name}")
                return None
                
        except Exception as e:
            logger.error(f"获取变量失败: {variable_name}, 错误: {str(e)}")
            return None
    
    def list_variables(self):
        """列出所有变量（包含元数据）"""  
        try:
            with self._cache_lock:
                result = []
                for name, data in self._cache.items():
                    var_dict = {
                        'variable_name': name,
                        'data_type': data.get('data_type', 'string'),
                        'source_step_index': data.get('source_step_index', 0),
                        'source_api_method': data.get('source_api_method', ''),
                        'created_at': data.get('metadata', {}).get('created_at', ''),
                        'value': data.get('value')
                    }
                    result.append(var_dict)
                return result
        except Exception as e:
            logger.error(f"列出变量失败: {str(e)}")
            return []
    
    def delete_variable(self, variable_name: str) -> bool:
        """删除变量"""
        try:
            with self._cache_lock:
                if variable_name in self._cache:
                    del self._cache[variable_name]
                    logger.info(f"变量删除成功: {variable_name}")
                    return True
                else:
                    logger.warning(f"要删除的变量不存在: {variable_name}")
                    return False
                    
        except Exception as e:
            logger.error(f"删除变量失败: {variable_name}, 错误: {str(e)}")
            return False
    
    def clear_variables(self) -> bool:
        """清空所有变量"""
        try:
            with self._cache_lock:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"清空变量成功: 共删除 {count} 个变量")
                return True
                
        except Exception as e:
            logger.error(f"清空变量失败: {str(e)}")
            return False
    
    def export_variables(self) -> Dict[str, Any]:
        """导出所有变量"""
        return self.list_variables()
    
    def get_variable_metadata(self, variable_name: str) -> Optional[Dict]:
        """获取变量元数据"""
        try:
            with self._cache_lock:
                if variable_name in self._cache:
                    var_data = self._cache[variable_name]
                    return {
                        'variable_name': variable_name,
                        'data_type': var_data.get('data_type', 'string'),
                        'source_step_index': var_data.get('source_step_index', 0),
                        'source_api_method': var_data.get('source_api_method', ''),
                        'created_at': var_data.get('metadata', {}).get('created_at', ''),
                        'source_api_params': var_data.get('metadata', {}).get('source_api_params', {})
                    }
                return None
        except Exception as e:
            logger.error(f"获取变量元数据失败: {variable_name}, 错误: {str(e)}")
            return None
    
    def _detect_data_type(self, value: Any) -> str:
        """检测数据类型（与真实VariableManager保持一致）"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'number'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        elif value is None:
            return 'null'
        else:
            return 'string'  # 默认转为字符串
    
    def _update_cache(self, variable_name: str, data: Dict[str, Any]):
        """更新LRU缓存"""
        # 如果变量已存在，先删除旧的
        if variable_name in self._cache:
            del self._cache[variable_name]
        
        # 添加新的（到末尾）
        self._cache[variable_name] = data
        
        # 检查缓存大小限制
        while len(self._cache) > self._max_cache_size:
            # 移除最旧的（第一个）
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"LRU缓存移除最旧变量: {oldest_key}")


def get_test_variable_manager(execution_id: str) -> TestVariableManager:
    """获取测试变量管理器实例"""
    return TestVariableManager(execution_id)