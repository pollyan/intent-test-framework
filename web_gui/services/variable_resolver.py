"""
变量解析服务 - VariableResolverService
处理测试步骤中的变量引用解析和替换
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from web_gui.models import db, ExecutionVariable, VariableReference

logger = logging.getLogger(__name__)

class VariableResolverService:
    """变量解析服务"""
    
    # 变量引用的正则表达式模式
    VARIABLE_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._variable_cache = {}
        self._load_variables()
    
    def _load_variables(self):
        """加载执行中的所有变量到缓存"""
        try:
            variables = ExecutionVariable.query.filter_by(
                execution_id=self.execution_id
            ).all()
            
            self._variable_cache = {}
            for var in variables:
                self._variable_cache[var.variable_name] = {
                    'value': var.get_typed_value(),
                    'data_type': var.data_type,
                    'source_step_index': var.source_step_index,
                    'source_api_method': var.source_api_method
                }
            
            logger.info(f"加载了 {len(self._variable_cache)} 个变量到缓存")
            
        except Exception as e:
            logger.error(f"加载变量失败: {e}")
            self._variable_cache = {}
    
    def resolve_step_parameters(self, step_params: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """
        解析步骤参数中的变量引用
        
        Args:
            step_params: 步骤参数字典
            step_index: 当前步骤索引
            
        Returns:
            解析后的参数字典
        """
        try:
            resolved_params = {}
            
            for param_name, param_value in step_params.items():
                resolved_value, references = self._resolve_value(param_value, step_index, param_name)
                resolved_params[param_name] = resolved_value
                
                # 记录变量引用
                for ref in references:
                    self._record_variable_reference(ref, step_index, param_name)
            
            return resolved_params
            
        except Exception as e:
            logger.error(f"解析步骤参数失败: {e}")
            return step_params
    
    def _resolve_value(self, value: Any, step_index: int, param_name: str) -> Tuple[Any, List[Dict]]:
        """
        递归解析值中的变量引用
        
        Args:
            value: 要解析的值
            step_index: 步骤索引
            param_name: 参数名
            
        Returns:
            (解析后的值, 变量引用列表)
        """
        references = []
        
        if isinstance(value, str):
            # 字符串类型，查找变量引用
            resolved_value, refs = self._resolve_string_value(value, step_index)
            references.extend(refs)
            return resolved_value, references
            
        elif isinstance(value, dict):
            # 字典类型，递归解析每个值
            resolved_dict = {}
            for k, v in value.items():
                resolved_v, refs = self._resolve_value(v, step_index, f"{param_name}.{k}")
                resolved_dict[k] = resolved_v
                references.extend(refs)
            return resolved_dict, references
            
        elif isinstance(value, list):
            # 列表类型，递归解析每个元素
            resolved_list = []
            for i, item in enumerate(value):
                resolved_item, refs = self._resolve_value(item, step_index, f"{param_name}[{i}]")
                resolved_list.append(resolved_item)
                references.extend(refs)
            return resolved_list, references
            
        else:
            # 其他类型直接返回
            return value, references
    
    def _resolve_string_value(self, text: str, step_index: int) -> Tuple[str, List[Dict]]:
        """
        解析字符串中的变量引用
        
        Args:
            text: 包含变量引用的字符串
            step_index: 步骤索引
            
        Returns:
            (解析后的字符串, 变量引用列表)
        """
        references = []
        resolved_text = text
        
        # 查找所有变量引用
        matches = self.VARIABLE_PATTERN.finditer(text)
        
        for match in matches:
            full_expression = match.group(0)  # ${variable.property}
            reference_path = match.group(1)   # variable.property
            
            try:
                # 解析变量引用
                resolved_value = self._resolve_reference_path(reference_path)
                
                # 替换文本中的引用
                resolved_text = resolved_text.replace(full_expression, str(resolved_value))
                
                # 记录成功的引用
                references.append({
                    'variable_name': reference_path.split('.')[0],
                    'reference_path': reference_path,
                    'original_expression': full_expression,
                    'resolved_value': str(resolved_value),
                    'resolution_status': 'success',
                    'error_message': None
                })
                
            except Exception as e:
                # 记录失败的引用
                references.append({
                    'variable_name': reference_path.split('.')[0],
                    'reference_path': reference_path,
                    'original_expression': full_expression,
                    'resolved_value': None,
                    'resolution_status': 'failed',
                    'error_message': str(e)
                })
                
                logger.warning(f"变量引用解析失败: {full_expression} - {e}")
        
        return resolved_text, references
    
    def _resolve_reference_path(self, reference_path: str) -> Any:
        """
        解析变量引用路径
        
        Args:
            reference_path: 变量引用路径，如 'product.name' 或 'items[0].price' 或 'product.tags[0]'
            
        Returns:
            解析后的值
            
        Raises:
            KeyError: 变量不存在
            AttributeError: 属性不存在
            IndexError: 数组索引越界
        """
        # 将路径拆分为变量名和剩余路径
        # 变量名是第一个点号或第一个方括号之前的部分
        first_dot = reference_path.find('.')
        first_bracket = reference_path.find('[')
        
        # 找到第一个分隔符的位置
        separators = [pos for pos in [first_dot, first_bracket] if pos != -1]
        
        if separators:
            first_separator = min(separators)
            variable_name = reference_path[:first_separator]
            
            if first_separator == first_dot:
                remaining_path = reference_path[first_dot + 1:]
            else:  # first_separator == first_bracket
                remaining_path = reference_path[first_bracket:]
        else:
            variable_name = reference_path
            remaining_path = ''
        
        # 检查变量是否存在
        if variable_name not in self._variable_cache:
            raise KeyError(f"变量 '{variable_name}' 不存在")
        
        current_value = self._variable_cache[variable_name]['value']
        
        # 如果没有剩余路径，直接返回变量值
        if not remaining_path:
            return current_value
        
        # 处理剩余路径
        return self._resolve_path_components(current_value, remaining_path)
    
    def _resolve_path_components(self, current_value: Any, path: str) -> Any:
        """
        递归解析路径组件，支持属性访问和数组索引的任意组合
        
        Args:
            current_value: 当前值
            path: 路径，如 'name' 或 'specs.color' 或 'tags[0]' 或 'items[0].name'
        """
        if not path:
            return current_value
        
        # 找到下一个分隔符（. 或 [）
        next_dot = path.find('.')
        next_bracket = path.find('[')
        
        # 确定下一个要处理的部分
        if next_bracket != -1 and (next_dot == -1 or next_bracket < next_dot):
            # 下一个是数组索引
            property_name = path[:next_bracket] if next_bracket > 0 else ''
            
            # 如果有属性名，先访问属性
            if property_name:
                current_value = self._resolve_property_access(current_value, property_name)
            
            # 处理数组索引
            bracket_end = path.find(']', next_bracket)
            if bracket_end == -1:
                raise ValueError(f"无效的数组索引语法: {path}")
            
            index_str = path[next_bracket + 1:bracket_end]
            try:
                index = int(index_str)
            except ValueError:
                raise ValueError(f"无效的数组索引: {index_str}")
            
            # 获取数组元素
            if isinstance(current_value, (list, tuple)):
                if 0 <= index < len(current_value):
                    current_value = current_value[index]
                else:
                    raise IndexError(f"数组索引 {index} 越界，长度为 {len(current_value)}")
            else:
                raise TypeError(f"不是数组类型，无法使用索引: {type(current_value)}")
            
            # 递归处理剩余路径
            remaining_path = path[bracket_end + 1:]
            if remaining_path.startswith('.'):
                remaining_path = remaining_path[1:]
            
            return self._resolve_path_components(current_value, remaining_path)
            
        elif next_dot != -1:
            # 下一个是属性访问
            property_name = path[:next_dot]
            current_value = self._resolve_property_access(current_value, property_name)
            
            # 递归处理剩余路径
            remaining_path = path[next_dot + 1:]
            return self._resolve_path_components(current_value, remaining_path)
            
        else:
            # 最后一个属性或处理剩余的数组索引
            if '[' in path and ']' in path:
                # 处理单独的数组索引，如 [0]
                bracket_start = path.find('[')
                property_name = path[:bracket_start] if bracket_start > 0 else ''
                
                if property_name:
                    current_value = self._resolve_property_access(current_value, property_name)
                
                bracket_end = path.find(']')
                index_str = path[bracket_start + 1:bracket_end]
                try:
                    index = int(index_str)
                except ValueError:
                    raise ValueError(f"无效的数组索引: {index_str}")
                
                if isinstance(current_value, (list, tuple)):
                    if 0 <= index < len(current_value):
                        return current_value[index]
                    else:
                        raise IndexError(f"数组索引 {index} 越界，长度为 {len(current_value)}")
                else:
                    raise TypeError(f"不是数组类型，无法使用索引: {type(current_value)}")
            else:
                # 单个属性访问
                return self._resolve_property_access(current_value, path)
    
    def _resolve_array_and_properties(self, current_value: Any, path: str) -> Any:
        """
        处理数组索引和属性访问的组合
        
        Args:
            current_value: 当前值
            path: 剩余路径，如 "[0].name" 或 "[1].specs.color"
        """
        while path:
            if path.startswith('['):
                # 处理数组索引
                bracket_end = path.find(']')
                if bracket_end == -1:
                    raise ValueError(f"无效的数组索引语法: {path}")
                
                index_str = path[1:bracket_end]
                try:
                    index = int(index_str)
                except ValueError:
                    raise ValueError(f"无效的数组索引: {index_str}")
                
                # 获取数组元素
                if isinstance(current_value, (list, tuple)):
                    if 0 <= index < len(current_value):
                        current_value = current_value[index]
                    else:
                        raise IndexError(f"数组索引 {index} 越界，长度为 {len(current_value)}")
                else:
                    raise TypeError(f"不是数组类型，无法使用索引: {type(current_value)}")
                
                # 更新剩余路径
                path = path[bracket_end + 1:]
                if path.startswith('.'):
                    path = path[1:]  # 移除点号
                    
            elif '.' in path:
                # 处理属性访问
                next_dot = path.find('.')
                next_bracket = path.find('[')
                
                if next_bracket != -1 and next_bracket < next_dot:
                    # 下一个是数组索引
                    property_name = path[:next_bracket]
                    current_value = self._resolve_property_access(current_value, property_name)
                    path = path[next_bracket:]
                else:
                    # 下一个是属性
                    property_name = path[:next_dot]
                    current_value = self._resolve_property_access(current_value, property_name)
                    path = path[next_dot + 1:]
            else:
                # 最后一个属性
                if path:
                    current_value = self._resolve_property_access(current_value, path)
                break
        
        return current_value
    
    def _resolve_property_access(self, current_value: Any, property_name: str) -> Any:
        """
        解析单个属性访问
        
        Args:
            current_value: 当前值
            property_name: 属性名
            
        Returns:
            属性值
        """
        if isinstance(current_value, dict) and property_name in current_value:
            return current_value[property_name]
        elif hasattr(current_value, property_name):
            return getattr(current_value, property_name)
        else:
            raise AttributeError(f"属性 '{property_name}' 不存在")
    
    def _record_variable_reference(self, reference_info: Dict, step_index: int, param_name: str):
        """记录变量引用到数据库"""
        try:
            variable_ref = VariableReference(
                execution_id=self.execution_id,
                step_index=step_index,
                variable_name=reference_info['variable_name'],
                reference_path=reference_info['reference_path'],
                parameter_name=param_name,
                original_expression=reference_info['original_expression'],
                resolved_value=reference_info['resolved_value'],
                resolution_status=reference_info['resolution_status'],
                error_message=reference_info['error_message']
            )
            
            db.session.add(variable_ref)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"记录变量引用失败: {e}")
            db.session.rollback()
    
    def store_step_output(self, variable_name: str, value: Any, step_index: int, 
                         api_method: str, api_params: Dict = None) -> bool:
        """
        存储步骤输出变量
        
        Args:
            variable_name: 变量名
            value: 变量值
            step_index: 步骤索引
            api_method: API方法名
            api_params: API参数
            
        Returns:
            是否存储成功
        """
        try:
            # 确定数据类型
            data_type = self._determine_data_type(value)
            
            # 检查变量是否已存在
            existing_var = ExecutionVariable.query.filter_by(
                execution_id=self.execution_id,
                variable_name=variable_name
            ).first()
            
            if existing_var:
                # 更新现有变量
                existing_var.variable_value = json.dumps(value, ensure_ascii=False)
                existing_var.data_type = data_type
                existing_var.source_step_index = step_index
                existing_var.source_api_method = api_method
                existing_var.source_api_params = json.dumps(api_params or {}, ensure_ascii=False)
            else:
                # 创建新变量
                new_var = ExecutionVariable(
                    execution_id=self.execution_id,
                    variable_name=variable_name,
                    variable_value=json.dumps(value, ensure_ascii=False),
                    data_type=data_type,
                    source_step_index=step_index,
                    source_api_method=api_method,
                    source_api_params=json.dumps(api_params or {}, ensure_ascii=False)
                )
                db.session.add(new_var)
            
            db.session.commit()
            
            # 更新缓存
            self._variable_cache[variable_name] = {
                'value': value,
                'data_type': data_type,
                'source_step_index': step_index,
                'source_api_method': api_method
            }
            
            logger.info(f"存储变量成功: {variable_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"存储变量失败: {e}")
            db.session.rollback()
            return False
    
    def _determine_data_type(self, value: Any) -> str:
        """确定变量的数据类型"""
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
        else:
            return 'string'  # 默认为字符串
    
    def get_available_variables(self) -> List[Dict[str, Any]]:
        """获取当前可用的变量列表"""
        variables = []
        
        for var_name, var_info in self._variable_cache.items():
            variables.append({
                'name': var_name,
                'data_type': var_info['data_type'],
                'value': var_info['value'],
                'source_step_index': var_info['source_step_index'],
                'source_api_method': var_info['source_api_method'],
                'properties': self._extract_properties(var_info['value'])
            })
        
        return variables
    
    def _extract_properties(self, value: Any, max_depth: int = 3, current_depth: int = 0) -> List[str]:
        """
        提取对象的属性路径，用于智能提示
        
        Args:
            value: 要提取属性的值
            max_depth: 最大深度
            current_depth: 当前深度
            
        Returns:
            属性路径列表
        """
        if current_depth >= max_depth:
            return []
        
        properties = []
        
        if isinstance(value, dict):
            for key in value.keys():
                properties.append(key)
                if isinstance(value[key], (dict, list)) and current_depth < max_depth - 1:
                    sub_properties = self._extract_properties(
                        value[key], max_depth, current_depth + 1
                    )
                    for sub_prop in sub_properties:
                        properties.append(f"{key}.{sub_prop}")
        
        elif isinstance(value, list) and len(value) > 0:
            # 为数组提供索引示例
            properties.append("[0]")
            if isinstance(value[0], (dict, list)) and current_depth < max_depth - 1:
                sub_properties = self._extract_properties(
                    value[0], max_depth, current_depth + 1
                )
                for sub_prop in sub_properties:
                    properties.append(f"[0].{sub_prop}")
        
        return properties
    
    def validate_variable_references(self, text: str, step_index: int) -> List[Dict[str, Any]]:
        """
        验证文本中的变量引用是否有效
        
        Args:
            text: 包含变量引用的文本
            step_index: 当前步骤索引
            
        Returns:
            验证结果列表
        """
        validation_results = []
        
        matches = self.VARIABLE_PATTERN.finditer(text)
        
        for match in matches:
            full_expression = match.group(0)
            reference_path = match.group(1)
            
            try:
                # 尝试解析引用
                resolved_value = self._resolve_reference_path(reference_path)
                
                validation_results.append({
                    'expression': full_expression,
                    'reference_path': reference_path,
                    'is_valid': True,
                    'resolved_value': str(resolved_value),
                    'error_message': None
                })
                
            except Exception as e:
                validation_results.append({
                    'expression': full_expression,
                    'reference_path': reference_path,
                    'is_valid': False,
                    'resolved_value': None,
                    'error_message': str(e)
                })
        
        return validation_results
    
    def refresh_cache(self):
        """刷新变量缓存"""
        self._load_variables()
    
    def clear_cache(self):
        """清空变量缓存"""
        self._variable_cache = {}