"""
变量建议服务 - 支持智能变量提示API
实现STORY-011的所有验收标准
"""

import re
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass

from .variable_manager import VariableManagerFactory, VariableManager

logger = logging.getLogger(__name__)

# 简单内存缓存实现（生产环境建议使用Redis）
class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, default=None):
        """获取缓存值"""
        if key in self._cache:
            timestamp = self._timestamps.get(key, datetime.min)
            if datetime.utcnow() - timestamp < timedelta(seconds=300):  # 5分钟过期
                return self._cache[key]
            else:
                # 清理过期数据
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
        return default
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """设置缓存值"""
        self._cache[key] = value
        self._timestamps[key] = datetime.utcnow()
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()

# 全局缓存实例
_cache = SimpleCache()

def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # 转换为毫秒
            logger.info(f"{func.__name__} 执行时间: {duration:.2f}ms")
            return result
        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            logger.error(f"{func.__name__} 执行失败: {str(e)}, 耗时: {duration:.2f}ms")
            raise
    return wrapper

@dataclass
class VariableMatch:
    """变量匹配结果"""
    name: str
    match_score: float
    highlighted_name: str
    data_type: str
    source_step_index: int
    preview_value: str

@dataclass
class PropertyInfo:
    """属性信息"""
    name: str
    type: str
    value: Any
    path: str
    properties: Optional[List['PropertyInfo']] = None

@dataclass
class ValidationResult:
    """验证结果"""
    reference: str
    is_valid: bool
    resolved_value: Any = None
    data_type: str = None
    error: str = None
    suggestion: str = None

class VariableSuggestionService:
    """
    变量建议服务
    为前端智能提示组件提供后端API支持
    """
    
    def __init__(self, variable_manager: VariableManager):
        """
        初始化变量建议服务
        
        Args:
            variable_manager: 变量管理器实例
        """
        self.variable_manager = variable_manager
        self.execution_id = variable_manager.execution_id
        
    @classmethod
    def get_service(cls, execution_id: str) -> 'VariableSuggestionService':
        """
        工厂方法：获取指定执行ID的建议服务实例
        
        Args:
            execution_id: 执行ID
            
        Returns:
            VariableSuggestionService实例
        """
        manager = VariableManagerFactory.get_manager(execution_id)
        return cls(manager)
    
    @performance_monitor
    def get_variable_suggestions(self, 
                                step_index: int = None, 
                                include_properties: bool = True,
                                limit: int = None) -> Dict[str, Any]:
        """
        获取变量建议列表 (AC-1)
        
        Args:
            step_index: 当前步骤索引，只显示之前步骤的变量
            include_properties: 是否包含对象属性信息
            limit: 限制返回数量
            
        Returns:
            变量建议响应数据
        """
        try:
            # 尝试从缓存获取
            cache_key = f"variables:{self.execution_id}:{step_index}:{include_properties}:{limit}"
            cached_result = _cache.get(cache_key)
            if cached_result:
                logger.debug(f"从缓存返回变量建议: {cache_key}")
                return cached_result
            
            # 获取所有变量
            all_variables = self.variable_manager.list_variables()
            logger.info(f"获取到 {len(all_variables)} 个变量")
            
            # 过滤步骤索引
            variables = []
            for var in all_variables:
                var_step_index = var.get('source_step_index', 0)
                if step_index is None or var_step_index < step_index:
                    variables.append(var)
            
            logger.info(f"过滤后剩余 {len(variables)} 个变量 (step_index: {step_index})")
            
            # 转换为建议格式
            suggestions = []
            for var in variables:
                var_name = var.get('variable_name', '')
                var_value = var.get('variable_value')
                data_type = var.get('data_type', 'string')
                
                # 解析JSON值
                if isinstance(var_value, str):
                    try:
                        var_value = json.loads(var_value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                suggestion = {
                    'name': var_name,
                    'data_type': data_type,
                    'source_step_index': var.get('source_step_index', 0),
                    'source_api_method': var.get('source_api_method', 'unknown'),
                    'created_at': var.get('created_at', datetime.utcnow().isoformat()),
                    'preview_value': self._format_preview_value(var_value, data_type)
                }
                
                # 包含属性信息
                if include_properties and data_type in ['object', 'array']:
                    properties = self._extract_properties_shallow(var_value, var_name)
                    suggestion['properties'] = properties
                
                suggestions.append(suggestion)
            
            # 限制数量
            if limit and len(suggestions) > limit:
                suggestions = suggestions[:limit]
            
            result = {
                'execution_id': self.execution_id,
                'current_step_index': step_index,
                'variables': suggestions,
                'total_count': len(suggestions)
            }
            
            # 缓存结果
            _cache.set(cache_key, result)
            logger.debug(f"缓存变量建议结果: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取变量建议失败: {str(e)}")
            raise
    
    @performance_monitor
    def get_variable_properties(self, 
                               variable_name: str, 
                               max_depth: int = 3) -> Optional[Dict[str, Any]]:
        """
        获取变量属性探索信息 (AC-2)
        
        Args:
            variable_name: 变量名
            max_depth: 最大探索深度
            
        Returns:
            属性探索响应数据
        """
        try:
            # 尝试从缓存获取
            cache_key = f"properties:{self.execution_id}:{variable_name}:{max_depth}"
            cached_result = _cache.get(cache_key)
            if cached_result:
                logger.debug(f"从缓存返回变量属性: {cache_key}")
                return cached_result
            # 获取变量元数据
            metadata = self.variable_manager.get_variable_metadata(variable_name)
            if not metadata:
                return None
            
            var_value = metadata.get('value')
            data_type = metadata.get('data_type', 'string')
            
            # 非对象/数组类型返回空属性
            if data_type not in ['object', 'array']:
                return {
                    'variable_name': variable_name,
                    'data_type': data_type,
                    'properties': []
                }
            
            # 深度提取属性
            properties = self._extract_properties_deep(
                var_value, 
                variable_name, 
                max_depth=max_depth
            )
            
            result = {
                'variable_name': variable_name,
                'data_type': data_type,
                'properties': properties
            }
            
            # 缓存结果（属性结构相对稳定，缓存时间更长）
            _cache.set(cache_key, result, ttl_seconds=600)  # 10分钟
            logger.debug(f"缓存变量属性结果: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取变量属性失败: {variable_name}, 错误: {str(e)}")
            raise
    
    @performance_monitor
    def search_variables(self, 
                        query: str, 
                        limit: int = 10, 
                        step_index: int = None) -> Dict[str, Any]:
        """
        模糊搜索变量 (AC-3)
        
        Args:
            query: 搜索查询
            limit: 结果限制
            step_index: 步骤索引过滤
            
        Returns:
            搜索结果响应数据
        """
        try:
            # 尝试从缓存获取
            cache_key = f"search:{self.execution_id}:{hash(query)}:{limit}:{step_index}"
            cached_result = _cache.get(cache_key)
            if cached_result:
                logger.debug(f"从缓存返回搜索结果: {cache_key}")
                return cached_result
            if not query.strip():
                return {
                    'query': query,
                    'matches': [],
                    'count': 0
                }
            
            # 获取变量列表
            all_variables = self.variable_manager.list_variables()
            
            # 过滤步骤索引
            variables = []
            for var in all_variables:
                var_step_index = var.get('source_step_index', 0)
                if step_index is None or var_step_index < step_index:
                    variables.append(var)
            
            # 计算匹配分数
            matches = []
            query_lower = query.lower()
            
            for var in variables:
                var_name = var.get('variable_name', '')
                var_name_lower = var_name.lower()
                
                # 计算基础匹配分数
                base_score = SequenceMatcher(None, query_lower, var_name_lower).ratio()
                
                # 加权计算
                score = base_score
                
                # 精确匹配加分
                if query_lower == var_name_lower:
                    score += 0.5
                # 前缀匹配加分
                elif var_name_lower.startswith(query_lower):
                    score += 0.3
                # 子字符串匹配加分
                elif query_lower in var_name_lower:
                    score += 0.2
                # 模糊匹配（考虑下划线分割）
                elif any(part.startswith(query_lower) for part in var_name_lower.split('_')):
                    score += 0.15
                
                # 最低阈值过滤
                if score >= 0.2:
                    var_value = var.get('variable_value')
                    data_type = var.get('data_type', 'string')
                    
                    # 解析JSON值
                    if isinstance(var_value, str):
                        try:
                            var_value = json.loads(var_value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    matches.append(VariableMatch(
                        name=var_name,
                        match_score=score,
                        highlighted_name=self._highlight_match(var_name, query),
                        data_type=data_type,
                        source_step_index=var.get('source_step_index', 0),
                        preview_value=self._format_preview_value(var_value, data_type)
                    ))
            
            # 按分数排序
            matches.sort(key=lambda x: x.match_score, reverse=True)
            
            # 限制结果数量
            if limit:
                matches = matches[:limit]
            
            # 转换为字典格式
            match_dicts = []
            for match in matches:
                match_dicts.append({
                    'name': match.name,
                    'match_score': match.match_score,
                    'highlighted_name': match.highlighted_name,
                    'data_type': match.data_type,
                    'source_step_index': match.source_step_index,
                    'preview_value': match.preview_value
                })
            
            result = {
                'query': query,
                'matches': match_dicts,
                'count': len(match_dicts)
            }
            
            # 缓存搜索结果（搜索结果变化较快，缓存时间较短）
            _cache.set(cache_key, result, ttl_seconds=60)  # 1分钟
            logger.debug(f"缓存搜索结果: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"变量搜索失败: {query}, 错误: {str(e)}")
            raise
    
    def validate_references(self, 
                           references: List[str], 
                           step_index: int = None) -> List[Dict[str, Any]]:
        """
        验证变量引用 (AC-4)
        
        Args:
            references: 变量引用列表
            step_index: 当前步骤索引
            
        Returns:
            验证结果列表
        """
        try:
            results = []
            
            for ref in references:
                try:
                    result = self._validate_single_reference(ref, step_index)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'reference': ref,
                        'is_valid': False,
                        'error': f'验证异常: {str(e)}'
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"批量验证变量引用失败: {str(e)}")
            raise
    
    @performance_monitor
    def get_variables_status(self) -> Dict[str, Any]:
        """
        获取变量状态概览 (AC-5)
        
        Returns:
            变量状态响应数据
        """
        try:
            # 尝试从缓存获取
            cache_key = f"status:{self.execution_id}"
            cached_result = _cache.get(cache_key)
            if cached_result:
                logger.debug(f"从缓存返回变量状态: {cache_key}")
                return cached_result
            # 获取所有变量
            variables = self.variable_manager.list_variables()
            
            # 获取引用统计
            usage_stats = self._calculate_usage_statistics()
            recent_refs = self._get_recent_references()
            
            # 格式化变量状态
            variable_statuses = []
            for var in variables:
                var_name = var.get('variable_name', '')
                variable_statuses.append({
                    'name': var_name,
                    'status': 'available',
                    'last_updated': var.get('created_at', datetime.utcnow().isoformat()),
                    'usage_count': usage_stats.get(var_name, 0)
                })
            
            result = {
                'execution_status': 'active',  # TODO: 从执行状态获取
                'current_step_index': None,    # TODO: 从执行状态获取
                'variables_count': len(variables),
                'variables': variable_statuses,
                'recent_references': recent_refs
            }
            
            # 缓存状态结果（状态变化频繁，缓存时间很短）
            _cache.set(cache_key, result, ttl_seconds=30)  # 30秒
            logger.debug(f"缓存变量状态结果: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取变量状态失败: {str(e)}")
            raise
    
    def clear_cache(self, variable_name: str = None):
        """
        清理缓存
        
        Args:
            variable_name: 指定变量名清理相关缓存，None则清理所有缓存
        """
        try:
            if variable_name:
                # 清理特定变量相关的缓存
                keys_to_remove = []
                for key in _cache._cache.keys():
                    if key.startswith(f"properties:{self.execution_id}:{variable_name}:"):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    _cache._cache.pop(key, None)
                    _cache._timestamps.pop(key, None)
                
                logger.debug(f"清理变量 {variable_name} 相关缓存，清理了 {len(keys_to_remove)} 个缓存项")
            else:
                # 清理当前执行ID的所有缓存
                keys_to_remove = []
                for key in _cache._cache.keys():
                    if f":{self.execution_id}:" in key:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    _cache._cache.pop(key, None)
                    _cache._timestamps.pop(key, None)
                
                logger.debug(f"清理执行 {self.execution_id} 的所有缓存，清理了 {len(keys_to_remove)} 个缓存项")
                
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
    
    @classmethod
    def clear_all_cache(cls):
        """
        清理全局缓存
        """
        try:
            _cache.clear()
            logger.info("已清理全局缓存")
        except Exception as e:
            logger.error(f"清理全局缓存失败: {str(e)}")
    
    def _validate_single_reference(self, reference: str, step_index: int = None) -> Dict[str, Any]:
        """
        验证单个变量引用
        
        Args:
            reference: 变量引用（如 ${variable.property}）
            step_index: 当前步骤索引
            
        Returns:
            验证结果字典
        """
        # 解析变量引用格式
        var_path = self._parse_variable_reference(reference)
        if not var_path:
            return {
                'reference': reference,
                'is_valid': False,
                'error': '无效的变量引用格式',
                'suggestion': '使用 ${variable_name} 或 ${variable.property} 格式'
            }
        
        # 分解变量路径
        path_parts = var_path.split('.')
        var_name = path_parts[0]
        
        # 检查变量是否存在
        var_value = self.variable_manager.get_variable(var_name)
        if var_value is None:
            # 提供可用变量建议
            available_vars = [v.get('variable_name', '') for v in self.variable_manager.list_variables()]
            return {
                'reference': reference,
                'is_valid': False,
                'error': f"变量 '{var_name}' 未定义",
                'suggestion': f"可用变量: {', '.join(available_vars[:5])}"
            }
        
        # 验证属性路径
        try:
            resolved_value = self._resolve_property_path(var_value, var_path)
            return {
                'reference': reference,
                'is_valid': True,
                'resolved_value': resolved_value,
                'data_type': type(resolved_value).__name__
            }
        except ValueError as e:
            # 提供属性建议
            suggestion = self._get_property_suggestions(var_value, var_path)
            return {
                'reference': reference,
                'is_valid': False,
                'error': str(e),
                'suggestion': suggestion
            }
    
    def _format_preview_value(self, value: Any, data_type: str, max_length: int = 100) -> str:
        """
        格式化预览值
        
        Args:
            value: 变量值
            data_type: 数据类型
            max_length: 最大长度
            
        Returns:
            格式化的预览字符串
        """
        try:
            if value is None:
                return 'null'
            elif data_type == 'string':
                str_val = str(value)
                if len(str_val) > max_length:
                    return f'"{str_val[:max_length-3]}..."'
                return f'"{str_val}"'
            elif data_type == 'number':
                return str(value)
            elif data_type == 'boolean':
                return 'true' if value else 'false'
            elif data_type == 'object':
                if isinstance(value, dict):
                    if len(value) == 0:
                        return '{}'
                    keys = list(value.keys())[:3]
                    preview_parts = []
                    for key in keys:
                        preview_parts.append(f'"{key}": ...')
                    result = '{' + ', '.join(preview_parts)
                    if len(value) > 3:
                        result += ', ...'
                    result += '}'
                    return result
                else:
                    return json.dumps(value, ensure_ascii=False)[:max_length]
            elif data_type == 'array':
                if isinstance(value, list):
                    return f'[{len(value)} items]'
                else:
                    return json.dumps(value, ensure_ascii=False)[:max_length]
            else:
                return str(value)[:max_length]
        except Exception:
            return 'preview unavailable'
    
    def _extract_properties_shallow(self, value: Any, parent_name: str) -> List[Dict[str, Any]]:
        """
        浅层提取对象属性
        
        Args:
            value: 对象值
            parent_name: 父对象名称
            
        Returns:
            属性列表
        """
        if not isinstance(value, dict):
            return []
        
        properties = []
        for key, val in value.items():
            prop_type = self._detect_data_type(val)
            properties.append({
                'name': key,
                'type': prop_type,
                'value': val,
                'path': f"{parent_name}.{key}"
            })
        
        return properties
    
    def _extract_properties_deep(self, 
                                value: Any, 
                                parent_name: str, 
                                max_depth: int = 3, 
                                current_depth: int = 0) -> List[Dict[str, Any]]:
        """
        深度提取对象属性
        
        Args:
            value: 对象值
            parent_name: 父对象名称
            max_depth: 最大深度
            current_depth: 当前深度
            
        Returns:
            属性列表
        """
        if current_depth >= max_depth or not isinstance(value, dict):
            return []
        
        properties = []
        for key, val in value.items():
            prop_type = self._detect_data_type(val)
            prop_path = f"{parent_name}.{key}"
            
            prop_info = {
                'name': key,
                'type': prop_type,
                'value': val,
                'path': prop_path
            }
            
            # 递归处理嵌套对象
            if isinstance(val, dict) and current_depth < max_depth - 1:
                nested_props = self._extract_properties_deep(
                    val, prop_path, max_depth, current_depth + 1
                )
                if nested_props:
                    prop_info['properties'] = nested_props
            
            properties.append(prop_info)
        
        return properties
    
    def _highlight_match(self, text: str, query: str) -> str:
        """
        高亮匹配的文本
        
        Args:
            text: 原始文本
            query: 查询字符串
            
        Returns:
            高亮后的HTML文本
        """
        if not query:
            return text
        
        try:
            # 使用正则表达式进行大小写不敏感的匹配
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            highlighted = pattern.sub(lambda m: f'<mark>{m.group()}</mark>', text)
            return highlighted
        except Exception:
            return text
    
    def _parse_variable_reference(self, reference: str) -> Optional[str]:
        """
        解析变量引用，提取变量路径
        
        Args:
            reference: 变量引用（如 ${variable.property}）
            
        Returns:
            变量路径或None
        """
        pattern = r'^\$\{([^}]+)\}$'
        match = re.match(pattern, reference.strip())
        return match.group(1) if match else None
    
    def _resolve_property_path(self, obj: Any, path: str) -> Any:
        """
        解析属性路径
        
        Args:
            obj: 基础对象
            path: 属性路径（如 variable.property.subprop）
            
        Returns:
            解析后的值
        """
        parts = path.split('.')
        current = obj
        
        # 跳过变量名本身，从第二部分开始解析
        for part in parts[1:]:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    raise ValueError(f"属性 '{part}' 在对象中不存在")
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    elif -len(current) <= index < 0:
                        current = current[index]
                    else:
                        raise ValueError(f"数组索引超出范围: {index}")
                except ValueError as ve:
                    if "invalid literal" in str(ve):
                        raise ValueError(f"无效的数组索引: {part}")
                    raise
            else:
                raise ValueError(f"无法访问属性 '{part}'，当前值类型: {type(current).__name__}")
        
        return current
    
    def _get_property_suggestions(self, obj: Any, failed_path: str) -> str:
        """
        获取属性建议
        
        Args:
            obj: 对象
            failed_path: 失败的路径
            
        Returns:
            建议文本
        """
        try:
            parts = failed_path.split('.')
            
            # 找到最后一个有效的对象
            current = obj
            valid_parts = [parts[0]]  # 变量名总是有效的
            
            for part in parts[1:-1]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                    valid_parts.append(part)
                else:
                    break
            
            # 获取当前对象的可用属性
            if isinstance(current, dict):
                available_props = list(current.keys())[:5]
                if available_props:
                    return f"可用属性: {', '.join(available_props)}"
            elif isinstance(current, list):
                return f"数组长度: {len(current)}，可用索引: 0-{len(current)-1}"
            
            return "无可用属性"
            
        except Exception:
            return "无法提供属性建议"
    
    def _detect_data_type(self, value: Any) -> str:
        """
        检测数据类型
        
        Args:
            value: 要检测的值
            
        Returns:
            数据类型字符串
        """
        if value is None:
            return 'null'
        elif isinstance(value, bool):
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
        else:
            return 'string'
    
    def _calculate_usage_statistics(self) -> Dict[str, int]:
        """
        计算变量使用统计
        
        Returns:
            变量使用次数字典
        """
        try:
            # TODO: 从VariableReference表统计
            # 这里返回模拟数据
            usage_stats = defaultdict(int)
            
            variables = self.variable_manager.list_variables()
            for var in variables:
                var_name = var.get('variable_name', '')
                # 模拟使用次数
                usage_stats[var_name] = hash(var_name) % 10
            
            return dict(usage_stats)
            
        except Exception as e:
            logger.error(f"计算使用统计失败: {str(e)}")
            return {}
    
    def _get_recent_references(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的变量引用记录
        
        Args:
            limit: 记录限制
            
        Returns:
            最近引用列表
        """
        try:
            # TODO: 从VariableReference表查询
            # 这里返回模拟数据
            return [
                {
                    'step_index': 3,
                    'reference': '${product_info.name}',
                    'status': 'success'
                },
                {
                    'step_index': 4,
                    'reference': '${user_data.email}',
                    'status': 'success'
                }
            ]
            
        except Exception as e:
            logger.error(f"获取最近引用失败: {str(e)}")
            return []