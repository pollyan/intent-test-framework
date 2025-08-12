"""
ExecutionVariable和VariableReference模型的简化单元测试
专注于模型逻辑而非数据库约束
"""
import pytest
import json
from datetime import datetime

from web_gui.models import ExecutionVariable, VariableReference


class TestExecutionVariableLogic:
    """ExecutionVariable模型逻辑测试（不涉及数据库）"""
    
    def test_get_typed_value_string(self):
        """测试string类型值转换"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='string_var',
            variable_value='"hello world"',
            data_type='string',
            source_step_index=1
        )
        
        result = var.get_typed_value()
        assert result == "hello world"
        assert isinstance(result, str)
    
    def test_get_typed_value_number(self):
        """测试number类型值转换"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='number_var',
            variable_value='42.5',
            data_type='number',
            source_step_index=1
        )
        
        result = var.get_typed_value()
        assert result == 42.5
        assert isinstance(result, float)
    
    def test_get_typed_value_boolean(self):
        """测试boolean类型值转换"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='bool_var',
            variable_value='true',
            data_type='boolean',
            source_step_index=1
        )
        
        result = var.get_typed_value()
        assert result is True
        assert isinstance(result, bool)
    
    def test_get_typed_value_object(self):
        """测试object类型值转换"""
        test_obj = {"name": "test", "age": 25}
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='obj_var',
            variable_value=json.dumps(test_obj),
            data_type='object',
            source_step_index=1
        )
        
        result = var.get_typed_value()
        assert result == test_obj
        assert isinstance(result, dict)
    
    def test_get_typed_value_array(self):
        """测试array类型值转换"""
        test_array = [1, 2, 3, "test"]
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='array_var',
            variable_value=json.dumps(test_array),
            data_type='array',
            source_step_index=1
        )
        
        result = var.get_typed_value()
        assert result == test_array
        assert isinstance(result, list)
    
    def test_get_typed_value_null(self):
        """测试空值处理"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='null_var',
            variable_value=None,
            data_type='string',
            source_step_index=1
        )
        
        result = var.get_typed_value()
        assert result is None
    
    def test_validate_valid_data(self):
        """测试有效数据验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='valid_var',
            variable_value='"test"',
            data_type='string',
            source_step_index=1
        )
        
        errors = var.validate()
        assert len(errors) == 0
    
    def test_validate_missing_execution_id(self):
        """测试缺少execution_id的验证"""
        var = ExecutionVariable(
            variable_name='test_var',
            data_type='string',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "execution_id是必需的" in errors
    
    def test_validate_missing_variable_name(self):
        """测试缺少variable_name的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            data_type='string',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "variable_name是必需的" in errors
    
    def test_validate_missing_data_type(self):
        """测试缺少data_type的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "data_type是必需的" in errors
    
    def test_validate_invalid_data_type(self):
        """测试无效data_type的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            data_type='invalid_type',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "不支持的数据类型: invalid_type" in errors
    
    def test_validate_negative_step_index(self):
        """测试负数step_index的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            data_type='string',
            source_step_index=-1
        )
        
        errors = var.validate()
        assert "source_step_index必须是非负整数" in errors
    
    def test_to_dict(self):
        """测试to_dict方法"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            variable_value='{"key": "value"}',
            data_type='object',
            source_step_index=1,
            source_api_method='aiQuery',
            source_api_params='{"param": "value"}',
            created_at=datetime(2025, 1, 30, 10, 0, 0)
        )
        
        result = var.to_dict()
        
        assert result['execution_id'] == 'test-exec-001'
        assert result['variable_name'] == 'test_var'
        assert result['variable_value'] == {"key": "value"}
        assert result['data_type'] == 'object'
        assert result['source_step_index'] == 1
        assert result['source_api_method'] == 'aiQuery'
        assert result['source_api_params'] == {"param": "value"}
        assert 'created_at' in result
    
    def test_from_dict(self):
        """测试from_dict类方法"""
        data = {
            'execution_id': 'test-exec-001',
            'variable_name': 'test_var',
            'variable_value': {"key": "value"},
            'data_type': 'object',
            'source_step_index': 1,
            'source_api_method': 'aiQuery',
            'source_api_params': {"param": "value"}
        }
        
        var = ExecutionVariable.from_dict(data)
        
        assert var.execution_id == 'test-exec-001'
        assert var.variable_name == 'test_var'
        assert var.get_typed_value() == {"key": "value"}
        assert var.data_type == 'object'


class TestVariableReferenceLogic:
    """VariableReference模型逻辑测试（不涉及数据库）"""
    
    def test_to_dict(self):
        """测试to_dict方法"""
        ref = VariableReference(
            execution_id='test-exec-001',
            step_index=2,
            variable_name='test_var',
            reference_path='test_var.name',
            parameter_name='input_text',
            original_expression='${test_var.name}',
            resolved_value='John Doe',
            resolution_status='success',
            error_message=None,
            created_at=datetime(2025, 1, 30, 10, 0, 0)
        )
        
        result = ref.to_dict()
        
        assert result['execution_id'] == 'test-exec-001'
        assert result['step_index'] == 2
        assert result['variable_name'] == 'test_var'
        assert result['reference_path'] == 'test_var.name'
        assert result['parameter_name'] == 'input_text'
        assert result['original_expression'] == '${test_var.name}'
        assert result['resolved_value'] == 'John Doe'
        assert result['resolution_status'] == 'success'
        assert result['error_message'] is None
        assert 'created_at' in result