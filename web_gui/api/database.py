"""
Database相关API模块
数据库状态检查和测试数据创建
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid

# 导入数据库模型
try:
    from models import db, TestCase, ExecutionHistory, StepExecution
except ImportError:
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution

# 从主蓝图导入
from . import api_bp

@api_bp.route('/db-status', methods=['GET'])
def get_db_status():
    """数据库状态全面检查"""
    try:
        db_info = {
            'status': 'healthy',
            'connection': True,
            'tables': [],
            'counts': {},
            'errors': [],
            'last_check': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        
        print("🔍 开始数据库状态检查...")
        
        # 检查数据库连接
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            print("✅ 数据库连接正常")
        except Exception as conn_error:
            db_info['connection'] = False
            db_info['errors'].append(f"连接测试失败: {str(conn_error)}")
            print(f"❌ 数据库连接失败: {conn_error}")
        
        # 检查表结构
        try:
            # 检查主要表
            tables_to_check = ['test_cases', 'execution_history', 'step_executions', 'templates']
            for table_name in tables_to_check:
                try:
                    count = db.session.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar()
                    db_info['tables'].append(table_name)
                    db_info['counts'][table_name] = count
                    print(f"📊 {table_name}: {count} 条记录")
                except Exception as table_error:
                    db_info['errors'].append(f"表 {table_name} 检查失败: {str(table_error)}")
                    print(f"❌ 表 {table_name} 检查失败: {table_error}")
            
            db.session.commit()
        except Exception as table_check_error:
            db_info['errors'].append(f"表结构检查失败: {str(table_check_error)}")
            print(f"❌ 表结构检查失败: {table_check_error}")
        
        # 检查最近的执行记录
        recent_executions = []
        try:
            executions = ExecutionHistory.query.order_by(ExecutionHistory.created_at.desc()).limit(5).all()
            for exec in executions:
                recent_executions.append({
                    'execution_id': exec.execution_id,
                    'test_case_id': exec.test_case_id,
                    'status': exec.status,
                    'created_at': exec.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if exec.created_at else None
                })
            print(f"📊 最近执行记录: {len(recent_executions)} 条")
        except Exception as exec_error:
            db_info['errors'].append(f"获取执行记录失败: {str(exec_error)}")
            print(f"❌ 获取执行记录失败: {exec_error}")
        
        # 环境信息
        import os
        env_info = {
            'database_url': os.getenv('DATABASE_URL', 'Not set')[:50] + '...' if os.getenv('DATABASE_URL') else 'Not set',
            'environment': os.getenv('VERCEL_ENV', 'local'),
            'region': os.getenv('VERCEL_REGION', 'unknown')
        }
        
        return jsonify({
            'code': 200,
            'data': {
                'database': db_info,
                'recent_executions': recent_executions,
                'environment': env_info
            }
        })
    except Exception as e:
        print(f"❌ 数据库状态检查失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'数据库状态检查失败: {str(e)}'
        }), 500

@api_bp.route('/db-status/create-test-data', methods=['POST'])
def create_test_data():
    """创建测试数据来验证数据库功能"""
    try:
        # 确保数据库表存在
        db.create_all()
        
        # 创建测试用例
        test_case = TestCase(
            name='测试用例 - 数据库验证',
            description='用于验证数据库功能的测试用例',
            steps='[{"action": "navigate", "params": {"url": "https://www.baidu.com"}, "description": "打开百度首页"}]',
            category='系统测试',
            priority=3,
            created_by='系统',
            created_at=datetime.utcnow()
        )
        
        db.session.add(test_case)
        db.session.flush()  # 获取ID
        
        # 创建执行历史记录
        execution_records = []
        for i in range(5):
            execution_id = str(uuid.uuid4())
            status = ['success', 'failed', 'success', 'success', 'failed'][i]
            
            execution = ExecutionHistory(
                execution_id=execution_id,
                test_case_id=test_case.id,
                status=status,
                mode='headless',
                start_time=datetime.utcnow() - timedelta(days=i),
                end_time=datetime.utcnow() - timedelta(days=i) + timedelta(minutes=2),
                duration=120,
                steps_total=3,
                steps_passed=3 if status == 'success' else 2,
                steps_failed=0 if status == 'success' else 1,
                executed_by='系统',
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            execution_records.append(execution)
            db.session.add(execution)
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '测试数据创建成功',
            'data': {
                'test_case_id': test_case.id,
                'execution_count': len(execution_records)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'创建测试数据失败: {str(e)}'
        }), 500