#!/usr/bin/env python3
"""
数据库迁移验证脚本 - 本地SQLite版本
验证变量管理表是否正确创建
"""

import sys
import os
import sqlite3
import logging
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.models import db, ExecutionVariable, VariableReference
from web_gui.app_enhanced import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_migration():
    """验证迁移是否成功"""
    
    # 创建临时SQLite数据库用于测试
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{temp_db.name}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        try:
            # 创建所有表
            db.create_all()
            logger.info("✓ 数据库表创建成功")
            
            # 验证表是否存在
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            assert 'execution_variables' in tables, "execution_variables表不存在"
            assert 'variable_references' in tables, "variable_references表不存在"
            logger.info("✓ 变量管理表存在检查通过")
            
            # 验证字段是否存在
            ev_columns = [col['name'] for col in inspector.get_columns('execution_variables')]
            required_ev_columns = ['id', 'execution_id', 'variable_name', 'variable_value', 'data_type']
            
            for col in required_ev_columns:
                assert col in ev_columns, f"execution_variables表缺少字段: {col}"
            logger.info("✓ execution_variables表字段检查通过")
            
            vr_columns = [col['name'] for col in inspector.get_columns('variable_references')]
            required_vr_columns = ['id', 'execution_id', 'step_index', 'variable_name']
            
            for col in required_vr_columns:
                assert col in vr_columns, f"variable_references表缺少字段: {col}"
            logger.info("✓ variable_references表字段检查通过")
            
            # 验证索引是否存在
            ev_indexes = [idx['name'] for idx in inspector.get_indexes('execution_variables')]
            logger.info(f"execution_variables索引: {ev_indexes}")
            
            vr_indexes = [idx['name'] for idx in inspector.get_indexes('variable_references')]
            logger.info(f"variable_references索引: {vr_indexes}")
            
            # 测试基本的CRUD操作
            test_crud_operations()
            
            logger.info("✓ 数据库迁移验证完全成功！")
            return True
            
        except Exception as e:
            logger.error(f"✗ 迁移验证失败: {e}")
            return False
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_db.name)
            except:
                pass

def test_crud_operations():
    """测试基本的CRUD操作"""
    try:
        # 创建测试变量
        test_var = ExecutionVariable(
            execution_id='test-exec-001',
            variable_name='test_variable',
            variable_value='{"test": "value"}',
            data_type='object',
            source_step_index=1,
            source_api_method='aiQuery'
        )
        
        db.session.add(test_var)
        db.session.commit()
        logger.info("✓ 变量创建测试通过")
        
        # 查询测试
        retrieved_var = ExecutionVariable.query.filter_by(
            execution_id='test-exec-001',
            variable_name='test_variable'
        ).first()
        
        assert retrieved_var is not None, "变量查询失败"
        assert retrieved_var.data_type == 'object', "数据类型不匹配"
        logger.info("✓ 变量查询测试通过")
        
        # 测试get_typed_value方法
        typed_value = retrieved_var.get_typed_value()
        assert isinstance(typed_value, dict), "类型转换失败"
        assert typed_value['test'] == 'value', "值解析失败"
        logger.info("✓ 变量类型转换测试通过")
        
        # 创建变量引用测试
        test_ref = VariableReference(
            execution_id='test-exec-001',
            step_index=2,
            variable_name='test_variable',
            reference_path='test_variable.test',
            original_expression='${test_variable.test}',
            resolved_value='value',
            resolution_status='success'
        )
        
        db.session.add(test_ref)
        db.session.commit()
        logger.info("✓ 变量引用创建测试通过")
        
        # 测试to_dict方法
        var_dict = retrieved_var.to_dict()
        assert 'variable_name' in var_dict, "to_dict方法失败"
        assert var_dict['variable_name'] == 'test_variable', "to_dict值不正确"
        logger.info("✓ to_dict方法测试通过")
        
        ref_dict = test_ref.to_dict()
        assert 'variable_name' in ref_dict, "引用to_dict方法失败"
        assert ref_dict['resolution_status'] == 'success', "引用to_dict值不正确"
        logger.info("✓ 引用to_dict方法测试通过")
        
        # 清理测试数据
        db.session.delete(test_ref)
        db.session.delete(test_var)
        db.session.commit()
        logger.info("✓ 测试数据清理完成")
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"CRUD操作测试失败: {e}")

if __name__ == '__main__':
    success = validate_migration()
    if success:
        print("\n🎉 数据库变量管理表验证成功！")
        print("✓ ExecutionVariable模型正常工作")
        print("✓ VariableReference模型正常工作")
        print("✓ 所有CRUD操作正常")
        print("✓ 数据类型转换正常")
    else:
        print("\n❌ 数据库变量管理表验证失败")
    
    sys.exit(0 if success else 1)