#!/usr/bin/env python3
"""
VariableResolverService 单元测试
测试变量管理器的所有功能
"""

import pytest
import json
import time
import threading
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.services.variable_resolver_service import VariableManager, VariableManagerFactory
from web_gui.models import db, ExecutionVariable, VariableReference, TestCase, ExecutionHistory
from web_gui.app_enhanced import create_app


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def test_execution_id():
    """测试执行ID"""
    return "test-exec-001"


@pytest.fixture
def variable_manager(app, test_execution_id):
    """创建变量管理器实例"""
    with app.app_context():
        # 创建必要的测试数据
        test_case = TestCase(
            name="Test Case for Variable Manager",
            description="测试用例",
            steps='[]',
            created_by='test'
        )
        db.session.add(test_case)
        db.session.commit()
        
        execution = ExecutionHistory(
            execution_id=test_execution_id,
            test_case_id=test_case.id,
            status='running',
            start_time=datetime.utcnow(),
            steps_total=5,
            steps_passed=0,
            steps_failed=0,
            executed_by='test'
        )
        db.session.add(execution)
        db.session.commit()
        
        manager = VariableManager(test_execution_id)
        yield manager
        
        # 清理
        manager.clear_variables()


class TestVariableManager:
    """VariableManager 测试类"""
    
    def test_init(self, app, test_execution_id):
        """测试初始化"""
        with app.app_context():
            manager = VariableManager(test_execution_id)
            assert manager.execution_id == test_execution_id
            assert len(manager._cache) == 0
            assert manager._max_cache_size == 1000
    
    def test_store_variable_basic_types(self, app, variable_manager):
        """测试存储基础数据类型"""
        with app.app_context():
            test_cases = [
                ('string_var', 'hello world', 'string'),
                ('number_int', 42, 'number'),
                ('number_float', 3.14, 'number'),
                ('boolean_true', True, 'boolean'),
                ('boolean_false', False, 'boolean'),
                ('null_var', None, 'null')
            ]
            
            for var_name, value, expected_type in test_cases:
                success = variable_manager.store_variable(
                    variable_name=var_name,
                    value=value,
                    source_step_index=1,
                    source_api_method='test_method'
                )
                
                assert success == True
                
                # 验证数据库存储
                stored_var = ExecutionVariable.query.filter_by(
                    execution_id=variable_manager.execution_id,
                    variable_name=var_name
                ).first()
                
                assert stored_var is not None
                assert stored_var.data_type == expected_type
                assert stored_var.source_step_index == 1
                assert stored_var.source_api_method == 'test_method'
                
                # 验证值正确性
                if value is None:
                    assert stored_var.get_typed_value() is None
                else:
                    assert stored_var.get_typed_value() == value
    
    def test_store_variable_complex_types(self, app, variable_manager):
        """测试存储复杂数据类型"""
        with app.app_context():
            # 测试对象类型
            object_data = {'name': 'test', 'value': 123, 'nested': {'key': 'value'}}
            success = variable_manager.store_variable(
                variable_name='object_var',
                value=object_data,
                source_step_index=2,
                source_api_method='aiQuery',
                source_api_params={'query': 'test query'}
            )
            
            assert success == True
            retrieved_value = variable_manager.get_variable('object_var')
            assert retrieved_value == object_data
            
            # 测试数组类型
            array_data = [1, 'two', {'three': 3}, [4, 5]]
            success = variable_manager.store_variable(
                variable_name='array_var',
                value=array_data,
                source_step_index=3,
                source_api_method='aiQuery'
            )
            
            assert success == True
            retrieved_value = variable_manager.get_variable('array_var')
            assert retrieved_value == array_data
    
    def test_get_variable(self, app, variable_manager):
        """测试获取变量"""
        with app.app_context():
            # 存储测试变量
            test_value = {'test': 'data', 'number': 42}
            variable_manager.store_variable('test_var', test_value, 1)
            
            # 第一次获取（从数据库）
            retrieved_value = variable_manager.get_variable('test_var')
            assert retrieved_value == test_value
            
            # 第二次获取（从缓存）
            retrieved_value = variable_manager.get_variable('test_var')
            assert retrieved_value == test_value
            
            # 获取不存在的变量
            non_existent = variable_manager.get_variable('non_existent')
            assert non_existent is None
    
    def test_get_variable_metadata(self, app, variable_manager):
        """测试获取变量元数据"""
        with app.app_context():
            # 存储测试变量
            source_params = {'query': 'test query', 'options': {}}
            variable_manager.store_variable(
                variable_name='meta_test_var',
                value='test_value',
                source_step_index=5,
                source_api_method='aiString',
                source_api_params=source_params
            )
            
            # 获取元数据
            metadata = variable_manager.get_variable_metadata('meta_test_var')
            
            assert metadata is not None
            assert metadata['variable_name'] == 'meta_test_var'
            assert metadata['data_type'] == 'string'
            assert metadata['source_step_index'] == 5
            assert metadata['source_api_method'] == 'aiString'
            assert metadata['source_api_params'] == source_params
            assert 'created_at' in metadata
            
            # 获取不存在变量的元数据
            non_existent_meta = variable_manager.get_variable_metadata('non_existent')
            assert non_existent_meta is None
    
    def test_list_variables(self, app, variable_manager):
        """测试列出所有变量"""
        with app.app_context():
            # 存储多个变量
            test_variables = [
                ('var1', 'value1', 1, 'aiString'),
                ('var2', 42, 2, 'aiNumber'),
                ('var3', {'key': 'value'}, 3, 'aiQuery'),
                ('var4', [1, 2, 3], 4, 'aiQuery')
            ]
            
            for var_name, value, step_index, api_method in test_variables:
                variable_manager.store_variable(var_name, value, step_index, api_method)
            
            # 列出所有变量
            variables = variable_manager.list_variables()
            
            assert len(variables) == 4
            
            # 验证排序（按step_index排序）
            assert variables[0]['variable_name'] == 'var1'
            assert variables[1]['variable_name'] == 'var2'
            assert variables[2]['variable_name'] == 'var3'
            assert variables[3]['variable_name'] == 'var4'
            
            # 验证变量内容
            for i, var_dict in enumerate(variables):
                expected_name, expected_value, expected_step, expected_method = test_variables[i]
                assert var_dict['variable_name'] == expected_name
                assert var_dict['value'] == expected_value
                assert var_dict['source_step_index'] == expected_step
                assert var_dict['source_api_method'] == expected_method
    
    def test_clear_variables(self, app, variable_manager):
        """测试清理变量"""
        with app.app_context():
            # 存储一些变量
            variable_manager.store_variable('var1', 'value1', 1)
            variable_manager.store_variable('var2', 'value2', 2)
            
            # 验证变量存在
            assert variable_manager.get_variable('var1') == 'value1'
            assert variable_manager.get_variable('var2') == 'value2'
            
            # 清理变量
            success = variable_manager.clear_variables()
            assert success == True
            
            # 验证变量已清理
            assert variable_manager.get_variable('var1') is None
            assert variable_manager.get_variable('var2') is None
            
            # 验证数据库记录已删除
            db_vars = ExecutionVariable.query.filter_by(
                execution_id=variable_manager.execution_id
            ).all()
            assert len(db_vars) == 0
    
    def test_export_variables(self, app, variable_manager):
        """测试导出变量"""
        with app.app_context():
            # 存储测试变量
            variable_manager.store_variable('export_var1', 'value1', 1, 'aiString')
            variable_manager.store_variable('export_var2', 42, 2, 'aiNumber')
            
            # 导出变量
            export_data = variable_manager.export_variables()
            
            assert 'execution_id' in export_data
            assert 'export_time' in export_data
            assert 'variable_count' in export_data
            assert 'variables' in export_data
            
            assert export_data['execution_id'] == variable_manager.execution_id
            assert export_data['variable_count'] == 2
            assert len(export_data['variables']) == 2
    
    def test_cache_mechanism(self, app, variable_manager):
        """测试缓存机制"""
        with app.app_context():
            # 存储变量
            variable_manager.store_variable('cache_test', 'cached_value', 1)
            
            # 第一次访问会加载到缓存
            value1 = variable_manager.get_variable('cache_test')
            assert value1 == 'cached_value'
            assert 'cache_test' in variable_manager._cache
            
            # 第二次访问应该从缓存获取
            value2 = variable_manager.get_variable('cache_test')
            assert value2 == 'cached_value'
            
            # 验证缓存统计
            stats = variable_manager.get_cache_stats()
            assert stats['cache_size'] == 1
            assert stats['max_cache_size'] == 1000
    
    def test_data_type_detection(self, app, variable_manager):
        """测试数据类型检测"""
        with app.app_context():
            test_cases = [
                ('string', 'hello', 'string'),
                ('int', 42, 'number'),
                ('float', 3.14, 'number'),
                ('bool_true', True, 'boolean'),
                ('bool_false', False, 'boolean'),
                ('list', [1, 2, 3], 'array'),
                ('dict', {'key': 'value'}, 'object'),
                ('none', None, 'null')
            ]
            
            for var_name, value, expected_type in test_cases:
                detected_type = variable_manager._detect_data_type(value)
                assert detected_type == expected_type
    
    def test_variable_update(self, app, variable_manager):
        """测试变量更新"""
        with app.app_context():
            # 初始存储
            variable_manager.store_variable('update_var', 'initial_value', 1, 'aiString')
            assert variable_manager.get_variable('update_var') == 'initial_value'
            
            # 更新变量
            variable_manager.store_variable('update_var', 'updated_value', 2, 'aiString')
            assert variable_manager.get_variable('update_var') == 'updated_value'
            
            # 验证只有一条数据库记录
            db_vars = ExecutionVariable.query.filter_by(
                execution_id=variable_manager.execution_id,
                variable_name='update_var'
            ).all()
            assert len(db_vars) == 1
            assert db_vars[0].variable_value == '"updated_value"'  # JSON存储
            assert db_vars[0].source_step_index == 2


class TestVariableManagerFactory:
    """VariableManagerFactory 测试类"""
    
    def teardown_method(self):
        """清理工厂实例"""
        VariableManagerFactory.cleanup_all()
    
    def test_get_manager_singleton(self, app):
        """测试单例模式"""
        with app.app_context():
            manager1 = VariableManagerFactory.get_manager('exec-001')
            manager2 = VariableManagerFactory.get_manager('exec-001')
            
            assert manager1 is manager2
            assert manager1.execution_id == 'exec-001'
    
    def test_get_manager_different_executions(self, app):
        """测试不同执行ID的管理器"""
        with app.app_context():
            manager1 = VariableManagerFactory.get_manager('exec-001')
            manager2 = VariableManagerFactory.get_manager('exec-002')
            
            assert manager1 is not manager2
            assert manager1.execution_id == 'exec-001'
            assert manager2.execution_id == 'exec-002'
    
    def test_cleanup_manager(self, app):
        """测试清理指定管理器"""
        with app.app_context():
            manager = VariableManagerFactory.get_manager('exec-cleanup')
            assert 'exec-cleanup' in VariableManagerFactory.get_active_managers()
            
            VariableManagerFactory.cleanup_manager('exec-cleanup')
            assert 'exec-cleanup' not in VariableManagerFactory.get_active_managers()
    
    def test_cleanup_all(self, app):
        """测试清理所有管理器"""
        with app.app_context():
            VariableManagerFactory.get_manager('exec-001')
            VariableManagerFactory.get_manager('exec-002')
            VariableManagerFactory.get_manager('exec-003')
            
            assert len(VariableManagerFactory.get_active_managers()) == 3
            
            VariableManagerFactory.cleanup_all()
            assert len(VariableManagerFactory.get_active_managers()) == 0
    
    def test_get_active_managers(self, app):
        """测试获取活跃管理器列表"""
        with app.app_context():
            VariableManagerFactory.get_manager('exec-001')
            VariableManagerFactory.get_manager('exec-002')
            
            active_managers = VariableManagerFactory.get_active_managers()
            assert len(active_managers) == 2
            assert 'exec-001' in active_managers
            assert 'exec-002' in active_managers
    
    def test_get_factory_stats(self, app):
        """测试获取工厂统计信息"""
        with app.app_context():
            VariableManagerFactory.get_manager('exec-001')
            VariableManagerFactory.get_manager('exec-002')
            
            stats = VariableManagerFactory.get_factory_stats()
            assert stats['active_managers'] == 2
            assert len(stats['manager_ids']) == 2


class TestPerformance:
    """性能测试"""
    
    def test_storage_performance(self, app, variable_manager):
        """测试存储性能"""
        with app.app_context():
            start_time = time.time()
            
            # 存储100个变量
            for i in range(100):
                variable_manager.store_variable(f'perf_var_{i}', f'value_{i}', i)
            
            storage_time = time.time() - start_time
            assert storage_time < 5.0  # 100个变量存储应在5秒内完成
            
            print(f"存储100个变量耗时: {storage_time:.3f}秒")
    
    def test_retrieval_performance(self, app, variable_manager):
        """测试检索性能"""
        with app.app_context():
            # 先存储100个变量
            for i in range(100):
                variable_manager.store_variable(f'perf_var_{i}', f'value_{i}', i)
            
            start_time = time.time()
            
            # 检索100个变量
            for i in range(100):
                value = variable_manager.get_variable(f'perf_var_{i}')
                assert value == f'value_{i}'
            
            retrieval_time = time.time() - start_time
            assert retrieval_time < 1.0  # 100个变量检索应在1秒内完成
            
            print(f"检索100个变量耗时: {retrieval_time:.3f}秒")
    
    def test_cache_performance(self, app, variable_manager):
        """测试缓存性能"""
        with app.app_context():
            # 存储变量
            variable_manager.store_variable('cache_perf_var', 'cached_value', 1)
            
            # 第一次访问（从数据库）
            start_time = time.time()
            value1 = variable_manager.get_variable('cache_perf_var')
            db_time = time.time() - start_time
            
            # 第二次访问（从缓存）
            start_time = time.time()
            value2 = variable_manager.get_variable('cache_perf_var')
            cache_time = time.time() - start_time
            
            assert value1 == value2
            # 缓存访问应该更快
            assert cache_time < db_time
            
            print(f"数据库访问: {db_time:.6f}秒, 缓存访问: {cache_time:.6f}秒")


class TestConcurrency:
    """并发测试"""
    
    def test_concurrent_storage(self, app):
        """测试并发存储"""
        with app.app_context():
            manager = VariableManager('concurrent-test')
            errors = []
            
            def store_variables(thread_id):
                try:
                    for i in range(10):
                        success = manager.store_variable(
                            f'thread_{thread_id}_var_{i}',
                            f'value_{thread_id}_{i}',
                            i
                        )
                        if not success:
                            errors.append(f'Thread {thread_id} failed to store var {i}')
                except Exception as e:
                    errors.append(f'Thread {thread_id} error: {str(e)}')
            
            # 创建5个线程并发存储
            threads = []
            for i in range(5):
                thread = threading.Thread(target=store_variables, args=(i,))
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            # 检查结果
            assert len(errors) == 0, f"并发存储出现错误: {errors}"
            
            # 验证所有变量都被正确存储
            variables = manager.list_variables()
            assert len(variables) == 50  # 5个线程 × 10个变量
            
            manager.clear_variables()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])