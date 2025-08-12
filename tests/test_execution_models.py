"""
ExecutionVariable和VariableReference模型的单元测试
"""
import pytest
import json
import time
from datetime import datetime
from unittest.mock import patch

from web_gui.models import db, ExecutionVariable, VariableReference, ExecutionHistory, TestCase


@pytest.fixture
def test_execution(db_session):
    """创建测试用的ExecutionHistory记录"""
    # 首先创建测试用例
    test_case = TestCase(
        name='Test Case',
        description='Test Description',
        steps='[]',
        created_by='test'
    )
    db_session.add(test_case)
    db_session.commit()
    
    # 创建执行历史
    execution = ExecutionHistory(
        execution_id='test-exec-001',
        test_case_id=test_case.id,
        status='running',
        start_time=datetime.utcnow(),
        steps_total=5,
        steps_passed=0,
        steps_failed=0,
        executed_by='test'
    )
    db_session.add(execution)
    db_session.commit()
    
    return execution


class TestExecutionVariable:
    """ExecutionVariable模型测试"""
    
    def test_execution_variable_creation(self, app, db_session, test_execution):
        """测试ExecutionVariable创建"""
        # 创建测试数据
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            variable_value='{"name": "test"}',
            data_type='object',
            source_step_index=1,
            source_api_method='aiQuery',
            source_api_params='{"query": "test query"}'
        )
        
        db_session.add(var)
        db_session.commit()
        
        # 验证数据
        assert var.id is not None
        assert var.execution_id == 'test-exec-001'
        assert var.variable_name == 'test_var'
        assert var.get_typed_value() == {"name": "test"}
        assert var.data_type == 'object'
        assert var.source_step_index == 1
    
    def test_get_typed_value_string(self, app, db_session):
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
    
    def test_get_typed_value_number(self, app, db_session):
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
    
    def test_get_typed_value_boolean(self, app, db_session):
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
    
    def test_get_typed_value_object(self, app, db_session):
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
    
    def test_get_typed_value_array(self, app, db_session):
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
    
    def test_get_typed_value_null(self, app, db_session):
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
    
    def test_validate_valid_data(self, app, db_session):
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
    
    def test_validate_missing_execution_id(self, app, db_session):
        """测试缺少execution_id的验证"""
        var = ExecutionVariable(
            variable_name='test_var',
            data_type='string',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "execution_id是必需的" in errors
    
    def test_validate_missing_variable_name(self, app, db_session):
        """测试缺少variable_name的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            data_type='string',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "variable_name是必需的" in errors
    
    def test_validate_missing_data_type(self, app, db_session):
        """测试缺少data_type的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "data_type是必需的" in errors
    
    def test_validate_invalid_data_type(self, app, db_session):
        """测试无效data_type的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            data_type='invalid_type',
            source_step_index=1
        )
        
        errors = var.validate()
        assert "不支持的数据类型: invalid_type" in errors
    
    def test_validate_negative_step_index(self, app, db_session):
        """测试负数step_index的验证"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            data_type='string',
            source_step_index=-1
        )
        
        errors = var.validate()
        assert "source_step_index必须是非负整数" in errors
    
    def test_get_by_execution(self, app, db_session):
        """测试按execution_id查询变量"""
        # 创建测试数据
        var1 = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='var1',
            variable_value='"value1"',
            data_type='string',
            source_step_index=1
        )
        var2 = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='var2',
            variable_value='"value2"',
            data_type='string',
            source_step_index=2
        )
        var3 = ExecutionVariable(
            execution_id='test-exec-002',
            variable_name='var3',
            variable_value='"value3"',
            data_type='string',
            source_step_index=1
        )
        
        db_session.add_all([var1, var2, var3])
        db_session.commit()
        
        # 查询test-exec-001的变量
        variables = ExecutionVariable.get_by_execution('test-exec-001')
        
        assert len(variables) == 2
        assert variables[0].variable_name == 'var1'  # 按step_index排序
        assert variables[1].variable_name == 'var2'
    
    def test_get_variable(self, app, db_session):
        """测试获取指定变量"""
        # 创建测试数据
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='specific_var',
            variable_value='"specific_value"',
            data_type='string',
            source_step_index=1
        )
        
        db_session.add(var)
        db_session.commit()
        
        # 查询指定变量
        result = ExecutionVariable.get_variable('test-exec-001', 'specific_var')
        
        assert result is not None
        assert result.variable_name == 'specific_var'
        assert result.get_typed_value() == 'specific_value'
        
        # 查询不存在的变量
        result = ExecutionVariable.get_variable('test-exec-001', 'nonexistent')
        assert result is None
    
    def test_to_dict(self, app, db_session):
        """测试to_dict方法"""
        var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_var',
            variable_value='{"key": "value"}',
            data_type='object',
            source_step_index=1,
            source_api_method='aiQuery',
            source_api_params='{"param": "value"}'
        )
        
        db_session.add(var)
        db_session.commit()
        
        result = var.to_dict()
        
        assert result['execution_id'] == 'test-exec-001'
        assert result['variable_name'] == 'test_var'
        assert result['variable_value'] == {"key": "value"}
        assert result['data_type'] == 'object'
        assert result['source_step_index'] == 1
        assert result['source_api_method'] == 'aiQuery'
        assert result['source_api_params'] == {"param": "value"}
    
    def test_from_dict(self, app, db_session):
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


class TestVariableReference:
    """VariableReference模型测试"""
    
    def test_variable_reference_creation(self, app, db_session):
        """测试VariableReference创建"""
        ref = VariableReference(
            execution_id='test-exec-001',
            step_index=2,
            variable_name='test_var',
            reference_path='test_var.name',
            parameter_name='input_text',
            original_expression='${test_var.name}',
            resolved_value='John Doe',
            resolution_status='success'
        )
        
        db_session.add(ref)
        db_session.commit()
        
        assert ref.id is not None
        assert ref.execution_id == 'test-exec-001'
        assert ref.step_index == 2
        assert ref.variable_name == 'test_var'
        assert ref.reference_path == 'test_var.name'
        assert ref.resolution_status == 'success'
    
    def test_to_dict(self, app, db_session):
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
            error_message=None
        )
        
        db_session.add(ref)
        db_session.commit()
        
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


class TestModelPerformance:
    """模型性能测试"""
    
    def test_execution_variable_query_performance(self, app, db_session):
        """测试ExecutionVariable查询性能"""
        # 创建大量测试数据
        variables = []
        for i in range(1000):
            var = ExecutionVariable(
                execution_id=f'test-exec-{i % 10}',  # 10个不同的execution
                variable_name=f'var_{i}',
                variable_value=f'"value_{i}"',
                data_type='string',
                source_step_index=i % 20
            )
            variables.append(var)
        
        db_session.add_all(variables)
        db_session.commit()
        
        # 测试按execution_id查询性能
        start_time = time.time()
        result = ExecutionVariable.get_by_execution('test-exec-0')
        query_time = time.time() - start_time
        
        # 验证结果
        assert len(result) == 100  # 每个execution有100个变量
        assert query_time < 0.1  # 查询时间应该小于100ms
        
        # 测试按变量名查询性能
        start_time = time.time()
        result = ExecutionVariable.get_variable('test-exec-0', 'var_0')
        query_time = time.time() - start_time
        
        assert result is not None
        assert query_time < 0.1  # 查询时间应该小于100ms