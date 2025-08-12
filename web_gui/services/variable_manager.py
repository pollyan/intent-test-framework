"""
变量管理服务 - 生产级版本
基于POC实现，支持数据库持久化存储
"""
import json
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

from ..models import db, ExecutionVariable, VariableReference

logger = logging.getLogger(__name__)

class VariableManager:
    """
    生产级变量管理器
    支持数据库持久化、类型安全、错误处理
    """
    
    def __init__(self, execution_id: str):
        """
        初始化变量管理器
        
        Args:
            execution_id: 执行ID，用于变量作用域隔离
        """
        self.execution_id = execution_id
        self._cache = {}  # 内存缓存提升性能
        self._cache_dirty = False
        
    def store_variable(self, 
                      variable_name: str, 
                      value: Any, 
                      source_step_index: int,
                      source_api_method: str = None,
                      source_api_params: Dict = None) -> bool:
        """
        存储变量到数据库
        
        Args:
            variable_name: 变量名
            value: 变量值
            source_step_index: 来源步骤索引
            source_api_method: 来源API方法
            source_api_params: 来源API参数
            
        Returns:
            bool: 存储是否成功
        """
        try:
            # 检测数据类型
            data_type = self._detect_data_type(value)
            
            # 检查是否已存在同名变量（同一执行中更新）
            existing_var = ExecutionVariable.query.filter_by(
                execution_id=self.execution_id,
                variable_name=variable_name
            ).first()
            
            if existing_var:
                # 更新现有变量
                existing_var.variable_value = json.dumps(value, ensure_ascii=False)
                existing_var.data_type = data_type
                existing_var.source_step_index = source_step_index
                existing_var.source_api_method = source_api_method
                existing_var.source_api_params = json.dumps(source_api_params or {})
                existing_var.created_at = datetime.utcnow()
            else:
                # 创建新变量
                new_var = ExecutionVariable(
                    execution_id=self.execution_id,
                    variable_name=variable_name,
                    variable_value=json.dumps(value, ensure_ascii=False),
                    data_type=data_type,
                    source_step_index=source_step_index,
                    source_api_method=source_api_method,
                    source_api_params=json.dumps(source_api_params or {})
                )
                db.session.add(new_var)
            
            db.session.commit()
            
            # 更新缓存
            self._cache[variable_name] = {
                'value': value,
                'data_type': data_type,
                'source_step_index': source_step_index,
                'source_api_method': source_api_method
            }
            
            logger.info(f"变量存储成功: {variable_name} = {value} (类型: {data_type})")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"变量存储失败: {variable_name}, 错误: {str(e)}")
            return False
    
    def get_variable(self, variable_name: str) -> Optional[Any]:
        """
        获取变量值
        
        Args:
            variable_name: 变量名
            
        Returns:
            变量值或None
        """
        try:
            # 先检查缓存
            if variable_name in self._cache:
                return self._cache[variable_name]['value']
            
            # 从数据库查询
            var = ExecutionVariable.query.filter_by(
                execution_id=self.execution_id,
                variable_name=variable_name
            ).first()
            
            if var:
                value = var.get_typed_value()
                # 更新缓存
                self._cache[variable_name] = {
                    'value': value,
                    'data_type': var.data_type,
                    'source_step_index': var.source_step_index,
                    'source_api_method': var.source_api_method
                }
                return value
            
            return None
            
        except Exception as e:
            logger.error(f"获取变量失败: {variable_name}, 错误: {str(e)}")
            return None
    
    def get_variable_metadata(self, variable_name: str) -> Optional[Dict]:
        """
        获取变量的元数据信息
        
        Args:
            variable_name: 变量名
            
        Returns:
            变量元数据字典
        """
        try:
            var = ExecutionVariable.query.filter_by(
                execution_id=self.execution_id,
                variable_name=variable_name
            ).first()
            
            if var:
                return {
                    'name': var.variable_name,
                    'value': var.get_typed_value(),
                    'data_type': var.data_type,
                    'source_step_index': var.source_step_index,
                    'source_api_method': var.source_api_method,
                    'source_api_params': json.loads(var.source_api_params) if var.source_api_params else {},
                    'created_at': var.created_at.isoformat() if var.created_at else None,
                    'is_encrypted': var.is_encrypted
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取变量元数据失败: {variable_name}, 错误: {str(e)}")
            return None
    
    def list_variables(self) -> List[Dict]:
        """
        列出当前执行的所有变量
        
        Returns:
            变量列表
        """
        try:
            variables = ExecutionVariable.query.filter_by(
                execution_id=self.execution_id
            ).order_by(ExecutionVariable.source_step_index).all()
            
            return [var.to_dict() for var in variables]
            
        except Exception as e:
            logger.error(f"列出变量失败: {str(e)}")
            return []
    
    def resolve_variable_references(self, text: str, step_index: int = None) -> str:
        """
        解析文本中的变量引用
        
        Args:
            text: 包含变量引用的文本
            step_index: 当前步骤索引（用于记录引用关系）
            
        Returns:
            解析后的文本
        """
        if not isinstance(text, str):
            return text
        
        # 匹配 ${variable_name} 和 ${variable.property} 格式
        pattern = r'\$\{([^}]+)\}'
        
        def replace_variable(match):
            reference = match.group(1)  # 提取变量引用部分
            original_expression = match.group(0)  # 完整的${...}表达式
            
            try:
                # 解析变量路径
                resolved_value = self._resolve_variable_path(reference)
                
                # 记录变量引用关系（如果提供了步骤索引）
                if step_index is not None:
                    self._record_variable_reference(
                        step_index=step_index,
                        variable_name=reference.split('.')[0],  # 主变量名
                        reference_path=reference,
                        original_expression=original_expression,
                        resolved_value=str(resolved_value),
                        resolution_status='success'
                    )
                
                return str(resolved_value) if resolved_value is not None else original_expression
                
            except Exception as e:
                logger.warning(f"变量引用解析失败: {reference}, 错误: {str(e)}")
                
                # 记录失败的引用
                if step_index is not None:
                    self._record_variable_reference(
                        step_index=step_index,
                        variable_name=reference.split('.')[0],
                        reference_path=reference,
                        original_expression=original_expression,
                        resolved_value=None,
                        resolution_status='failed',
                        error_message=str(e)
                    )
                
                return original_expression  # 保持原样
        
        return re.sub(pattern, replace_variable, text)
    
    def _resolve_variable_path(self, reference: str) -> Any:
        """
        解析变量路径（支持嵌套属性访问）
        
        Args:
            reference: 变量引用路径，如 "product_info.price"
            
        Returns:
            解析后的值
        """
        parts = reference.split('.')
        variable_name = parts[0]
        
        # 获取基础变量值
        value = self.get_variable(variable_name)
        if value is None:
            raise ValueError(f"变量不存在: {variable_name}")
        
        # 逐级访问属性
        current_value = value
        for part in parts[1:]:
            if isinstance(current_value, dict):
                if part in current_value:
                    current_value = current_value[part]
                else:
                    raise ValueError(f"属性不存在: {part} in {parts[:-1]}")
            elif isinstance(current_value, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current_value):
                        current_value = current_value[index]
                    elif -len(current_value) <= index < 0:  # 支持负数索引
                        current_value = current_value[index]
                    else:
                        raise ValueError(f"数组索引超出范围: {index}")
                except ValueError:
                    raise ValueError(f"无效的数组索引: {part}")
            else:
                raise ValueError(f"无法访问属性 {part}，当前值类型: {type(current_value)}")
        
        return current_value
    
    def _record_variable_reference(self, step_index: int, variable_name: str, reference_path: str,
                                 original_expression: str, resolved_value: str = None,
                                 resolution_status: str = 'success', error_message: str = None):
        """
        记录变量引用关系到数据库
        """
        try:
            reference_record = VariableReference(
                execution_id=self.execution_id,
                step_index=step_index,
                variable_name=variable_name,
                reference_path=reference_path,
                original_expression=original_expression,
                resolved_value=resolved_value,
                resolution_status=resolution_status,
                error_message=error_message
            )
            
            db.session.add(reference_record)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"记录变量引用失败: {str(e)}")
    
    def _detect_data_type(self, value: Any) -> str:
        """
        检测数据类型
        
        Args:
            value: 要检测的值
            
        Returns:
            数据类型字符串
        """
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
            return 'string'  # 默认转为字符串
    
    def clear_variables(self) -> bool:
        """
        清理当前执行的所有变量
        
        Returns:
            bool: 清理是否成功
        """
        try:
            # 删除数据库中的变量记录
            ExecutionVariable.query.filter_by(execution_id=self.execution_id).delete()
            VariableReference.query.filter_by(execution_id=self.execution_id).delete()
            
            db.session.commit()
            
            # 清理缓存
            self._cache.clear()
            
            logger.info(f"已清理执行 {self.execution_id} 的所有变量")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"清理变量失败: {str(e)}")
            return False
    
    def export_variables(self) -> Dict:
        """
        导出所有变量数据
        
        Returns:
            包含所有变量的字典
        """
        try:
            variables = self.list_variables()
            references = VariableReference.query.filter_by(execution_id=self.execution_id).all()
            
            return {
                'execution_id': self.execution_id,
                'variables': variables,
                'references': [ref.to_dict() for ref in references],
                'exported_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"导出变量失败: {str(e)}")
            return {}

class VariableManagerFactory:
    """
    变量管理器工厂类
    管理多个执行的变量管理器实例
    """
    
    _instances = {}
    
    @classmethod
    def get_manager(cls, execution_id: str) -> VariableManager:
        """
        获取指定执行ID的变量管理器实例
        
        Args:
            execution_id: 执行ID
            
        Returns:
            VariableManager实例
        """
        if execution_id not in cls._instances:
            cls._instances[execution_id] = VariableManager(execution_id)
        
        return cls._instances[execution_id]
    
    @classmethod
    def cleanup_manager(cls, execution_id: str):
        """
        清理指定执行ID的变量管理器实例
        
        Args:
            execution_id: 执行ID
        """
        if execution_id in cls._instances:
            manager = cls._instances[execution_id]
            manager.clear_variables()
            del cls._instances[execution_id]
            logger.info(f"已清理变量管理器: {execution_id}")
    
    @classmethod
    def cleanup_all(cls):
        """
        清理所有变量管理器实例
        """
        for execution_id in list(cls._instances.keys()):
            cls.cleanup_manager(execution_id)
        
        logger.info("已清理所有变量管理器")