"""
数据库迁移测试套件
测试迁移脚本的各种场景
"""
import pytest
import tempfile
import os
import sqlite3
import shutil
from unittest.mock import patch, MagicMock

from web_gui.models import db, ExecutionVariable, VariableReference, TestCase, ExecutionHistory
from web_gui.app_enhanced import create_app


class TestDatabaseMigration:
    """数据库迁移测试"""
    
    def test_fresh_database_migration(self, app):
        """测试全新数据库迁移"""
        with app.app_context():
            # 创建所有表（模拟迁移）
            db.create_all()
            
            # 验证表是否创建
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            assert 'execution_variables' in tables
            assert 'variable_references' in tables
            assert 'test_cases' in tables
            assert 'execution_history' in tables
    
    def test_existing_database_migration(self, app):
        """测试现有数据库迁移（保持现有数据）"""
        with app.app_context():
            # 先创建基础表和数据
            db.create_all()
            
            # 插入现有测试数据
            test_case = TestCase(
                name='Existing Test',
                description='Pre-migration test',
                steps='[]',
                created_by='test'
            )
            db.session.add(test_case)
            db.session.commit()
            
            # 验证现有数据未受影响
            existing_test = TestCase.query.filter_by(name='Existing Test').first()
            assert existing_test is not None
            assert existing_test.description == 'Pre-migration test'
            
            # 验证新表也已创建
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            assert 'execution_variables' in tables
            assert 'variable_references' in tables
    
    def test_migration_idempotency(self, app):
        """测试重复迁移（幂等性）"""
        with app.app_context():
            # 第一次迁移
            db.create_all()
            
            # 插入测试数据
            test_var = ExecutionVariable(
                execution_id='test-exec',
                variable_name='test_var',
                variable_value='"test"',
                data_type='string',
                source_step_index=1
            )
            db.session.add(test_var)
            db.session.commit()
            
            # 再次执行迁移（应该不影响现有数据）
            db.create_all()
            
            # 验证数据完整性
            retrieved_var = ExecutionVariable.query.filter_by(
                execution_id='test-exec',
                variable_name='test_var'
            ).first()
            
            assert retrieved_var is not None
            assert retrieved_var.get_typed_value() == "test"
    
    def test_migration_indexes_creation(self, app):
        """测试索引创建"""
        with app.app_context():
            db.create_all()
            
            # 验证索引是否创建
            inspector = db.inspect(db.engine)
            
            # 检查execution_variables表索引
            ev_indexes = inspector.get_indexes('execution_variables')
            index_names = [idx['name'] for idx in ev_indexes]
            
            assert 'idx_execution_variable' in index_names
            assert 'idx_execution_step' in index_names
            assert 'idx_variable_type' in index_names
            
            # 检查variable_references表索引
            vr_indexes = inspector.get_indexes('variable_references')
            vr_index_names = [idx['name'] for idx in vr_indexes]
            
            assert 'idx_reference_execution_step' in vr_index_names
            assert 'idx_reference_variable' in vr_index_names
            assert 'idx_reference_status' in vr_index_names
    
    def test_foreign_key_constraints(self, app):
        """测试外键约束"""
        with app.app_context():
            db.create_all()
            
            # 创建测试用例和执行历史
            test_case = TestCase(
                name='FK Test',
                description='Foreign key test',
                steps='[]',
                created_by='test'
            )
            db.session.add(test_case)
            db.session.commit()
            
            execution = ExecutionHistory(
                execution_id='fk-test-exec',
                test_case_id=test_case.id,
                status='success',
                start_time=db.func.now(),
                steps_total=1,
                steps_passed=1,
                steps_failed=0,
                executed_by='test'
            )
            db.session.add(execution)
            db.session.commit()
            
            # 创建变量（应该成功）
            test_var = ExecutionVariable(
                execution_id='fk-test-exec',
                variable_name='fk_var',
                variable_value='"test"',
                data_type='string',
                source_step_index=1
            )
            db.session.add(test_var)
            db.session.commit()
            
            # 验证关联关系
            assert test_var.execution.execution_id == 'fk-test-exec'
            assert test_var.execution.test_case.name == 'FK Test'
    
    def test_unique_constraints(self, app):
        """测试唯一约束"""
        with app.app_context():
            db.create_all()
            
            # 创建第一个变量
            var1 = ExecutionVariable(
                execution_id='unique-test',
                variable_name='unique_var',
                variable_value='"value1"',
                data_type='string',
                source_step_index=1
            )
            db.session.add(var1)
            db.session.commit()
            
            # 尝试创建同名变量（应该失败）
            var2 = ExecutionVariable(
                execution_id='unique-test',
                variable_name='unique_var',  # 重复的变量名
                variable_value='"value2"',
                data_type='string',
                source_step_index=2
            )
            db.session.add(var2)
            
            with pytest.raises(Exception):  # 应该抛出完整性错误
                db.session.commit()
            
            db.session.rollback()


class TestMigrationPerformance:
    """迁移性能测试"""
    
    def test_large_data_migration_performance(self, app):
        """测试大数据量迁移性能"""
        with app.app_context():
            db.create_all()
            
            import time
            
            # 批量插入大量数据
            variables = []
            for i in range(1000):
                var = ExecutionVariable(
                    execution_id=f'perf-test-{i % 10}',
                    variable_name=f'var_{i}',
                    variable_value=f'"value_{i}"',
                    data_type='string',
                    source_step_index=i % 50
                )
                variables.append(var)
            
            start_time = time.time()
            db.session.add_all(variables)
            db.session.commit()
            insert_time = time.time() - start_time
            
            # 验证插入性能（应该在合理时间内完成）
            assert insert_time < 10.0, f"批量插入耗时过长: {insert_time}s"
            
            # 测试索引查询性能
            start_time = time.time()
            result = ExecutionVariable.query.filter_by(
                execution_id='perf-test-0'
            ).all()
            query_time = time.time() - start_time
            
            assert len(result) == 100  # 每个execution有100个变量
            assert query_time < 0.5, f"索引查询耗时过长: {query_time}s"


class TestMigrationSQLScripts:
    """SQL脚本测试"""
    
    def test_manual_sql_migration(self):
        """测试手动SQL迁移脚本"""
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 读取并执行SQL迁移脚本
            sql_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'migrations', 'sql', '001_add_variable_tables.sql'
            )
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 执行迁移脚本
            cursor.executescript(sql_content)
            conn.commit()
            
            # 验证表创建
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'execution_variables' in tables
            assert 'variable_references' in tables
            
            # 验证索引创建
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            assert 'idx_execution_variable' in indexes
            assert 'idx_reference_execution_step' in indexes
            
            conn.close()
            
        finally:
            # 清理临时文件
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_sql_rollback_script(self):
        """测试SQL回滚脚本"""
        # 创建临时数据库并先执行迁移
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 先执行迁移
            migration_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'migrations', 'sql', '001_add_variable_tables.sql'
            )
            
            with open(migration_file, 'r', encoding='utf-8') as f:
                cursor.executescript(f.read())
            
            # 插入测试数据
            cursor.execute("""
                INSERT INTO execution_variables 
                (execution_id, variable_name, variable_value, data_type, source_step_index)
                VALUES ('test', 'var1', '"value"', 'string', 1)
            """)
            conn.commit()
            
            # 执行回滚脚本
            rollback_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'migrations', 'sql', '001_rollback_variable_tables.sql'
            )
            
            with open(rollback_file, 'r', encoding='utf-8') as f:
                cursor.executescript(f.read())
            
            # 验证表已删除
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%variable%'")
            tables = cursor.fetchall()
            
            assert len(tables) == 0, "表未正确删除"
            
            conn.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)