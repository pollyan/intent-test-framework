"""
变量存储管理器 - 用于存储和引用MidSceneJS API返回值
"""
import json
import re
from typing import Any, Dict, Optional
from datetime import datetime


class VariableManager:
    """变量存储和引用管理器"""
    
    def __init__(self):
        self.variables = {}  # 存储变量的字典
        self.execution_context = {}  # 执行上下文，用于临时存储
        
    def store_variable(self, name: str, value: Any, metadata: Optional[Dict] = None) -> None:
        """
        存储变量
        
        Args:
            name: 变量名
            value: 变量值
            metadata: 可选的元数据信息
        """
        self.variables[name] = {
            'value': value,
            'type': type(value).__name__,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        print(f"✅ 变量已存储: {name} = {value} (类型: {type(value).__name__})")
    
    def get_variable(self, name: str) -> Any:
        """
        获取变量值
        
        Args:
            name: 变量名
            
        Returns:
            变量值
            
        Raises:
            KeyError: 变量不存在时抛出
        """
        if name not in self.variables:
            raise KeyError(f"变量 '{name}' 不存在")
        
        return self.variables[name]['value']
    
    def get_variable_info(self, name: str) -> Dict:
        """
        获取变量完整信息
        
        Args:
            name: 变量名
            
        Returns:
            包含值、类型、时间戳和元数据的字典
        """
        if name not in self.variables:
            raise KeyError(f"变量 '{name}' 不存在")
        
        return self.variables[name]
    
    def list_variables(self) -> Dict[str, str]:
        """
        列出所有变量及其类型
        
        Returns:
            变量名到类型的映射
        """
        return {name: info['type'] for name, info in self.variables.items()}
    
    def replace_variable_references(self, text: str) -> str:
        """
        替换文本中的变量引用
        支持格式: ${变量名} 或 {变量名}
        
        Args:
            text: 包含变量引用的文本
            
        Returns:
            替换后的文本
        """
        if not isinstance(text, str):
            return text
        
        # 匹配 ${变量名} 或 {变量名} 格式
        pattern = r'\$?\{([^}]+)\}'
        
        def replace_match(match):
            var_name = match.group(1)
            try:
                value = self.get_variable(var_name)
                # 如果值是字符串，直接返回；如果是其他类型，转换为JSON字符串
                if isinstance(value, str):
                    return value
                else:
                    return json.dumps(value, ensure_ascii=False)
            except KeyError:
                # 如果变量不存在，保持原样
                return match.group(0)
        
        return re.sub(pattern, replace_match, text)
    
    def clear_variables(self) -> None:
        """清除所有变量"""
        self.variables.clear()
        self.execution_context.clear()
        print("🧹 所有变量已清除")
    
    def export_variables(self) -> Dict:
        """导出所有变量（用于调试或保存）"""
        return {
            'variables': self.variables,
            'export_time': datetime.now().isoformat()
        }
    
    def import_variables(self, data: Dict) -> None:
        """导入变量（用于恢复或测试）"""
        if 'variables' in data:
            self.variables.update(data['variables'])
            print(f"📥 已导入 {len(data['variables'])} 个变量")


# 全局变量管理器实例
variable_manager = VariableManager()


def extract_variable_assignment(step_params: Dict) -> Optional[str]:
    """
    从步骤参数中提取变量赋值信息
    
    Args:
        step_params: 步骤参数字典
        
    Returns:
        变量名，如果没有赋值则返回None
    """
    # 支持多种变量赋值格式
    for key in ['store_as', 'save_to', 'assign_to', 'var_name']:
        if key in step_params:
            return step_params[key]
    
    return None


def process_variable_references(params: Dict) -> Dict:
    """
    处理参数中的变量引用
    
    Args:
        params: 原始参数字典
        
    Returns:
        处理后的参数字典
    """
    processed_params = {}
    
    for key, value in params.items():
        if isinstance(value, str):
            processed_params[key] = variable_manager.replace_variable_references(value)
        elif isinstance(value, dict):
            processed_params[key] = process_variable_references(value)
        elif isinstance(value, list):
            processed_params[key] = [
                variable_manager.replace_variable_references(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            processed_params[key] = value
    
    return processed_params