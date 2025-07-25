"""
API测试配置文件
提供API测试所需的fixtures和配置
"""

import pytest
import json
from web_gui.app_enhanced import create_app
from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template
from tests.unit.factories import TestCaseFactory, ExecutionHistoryFactory, StepExecutionFactory


@pytest.fixture(scope="function")
def api_app():
    """创建API测试应用实例"""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    }
    
    app = create_app(test_config=test_config)
    
    # 确保应用上下文
    with app.app_context():
        # 启用SQLite外键约束
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        # 创建所有表
        db.create_all()
        
        yield app
        
        # 清理
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def api_client(api_app):
    """创建API测试客户端"""
    return api_app.test_client()


@pytest.fixture(scope="function") 
def db_session(api_app):
    """提供数据库会话"""
    with api_app.app_context():
        yield db.session


@pytest.fixture
def sample_testcase_data():
    """提供标准的测试用例数据"""
    return {
        'name': 'API测试用例',
        'description': '用于API测试的示例测试用例',
        'steps': [
            {
                'action': 'navigate',
                'params': {'url': 'https://example.com'},
                'description': '访问示例网站'
            },
            {
                'action': 'ai_input',
                'params': {
                    'text': '测试文本',
                    'locate': '输入框'
                },
                'description': '输入测试文本'
            }
        ],
        'category': 'API测试',
        'priority': 2,
        'tags': ['api', 'test']
    }


@pytest.fixture
def invalid_testcase_data():
    """提供无效的测试用例数据（用于错误测试）"""
    return {
        'name': '',  # 空名称
        'description': None,
        'steps': 'invalid_json',  # 无效的JSON
        'category': 'x' * 200,  # 超长类别
        'priority': 'invalid',  # 无效优先级
        'tags': None
    }


@pytest.fixture
def create_test_testcase(db_session):
    """创建测试用例的工厂函数"""
    def _create_testcase(**kwargs):
        # 设置默认值
        defaults = {
            'name': 'API测试用例',
            'description': '测试描述',
            'steps': json.dumps([
                {'action': 'navigate', 'params': {'url': 'https://example.com'}}
            ]),
            'category': 'API测试',
            'priority': 2,
            'tags': 'api,test',
            'created_by': 'test_user',
            'is_active': True
        }
        defaults.update(kwargs)
        
        testcase = TestCase(**defaults)
        db_session.add(testcase)
        db_session.commit()
        return testcase
    
    return _create_testcase


@pytest.fixture
def assert_json_structure():
    """验证JSON响应结构的辅助函数"""
    def _assert_structure(response_data, expected_fields):
        """验证响应数据包含期望的字段"""
        if isinstance(expected_fields, dict):
            for field, field_type in expected_fields.items():
                assert field in response_data, f"缺少字段: {field}"
                if field_type is not None:
                    assert isinstance(response_data[field], field_type), \
                        f"字段 {field} 类型错误，期望 {field_type}，实际 {type(response_data[field])}"
        elif isinstance(expected_fields, list):
            for field in expected_fields:
                assert field in response_data, f"缺少字段: {field}"
    
    return _assert_structure


@pytest.fixture
def assert_api_response():
    """验证API响应格式的辅助函数"""
    def _assert_response(response, expected_status=200, expected_fields=None):
        """验证API响应的基本格式"""
        assert response.status_code == expected_status, \
            f"状态码错误，期望 {expected_status}，实际 {response.status_code}"
        
        # 验证响应是JSON格式
        assert response.content_type == 'application/json', \
            f"Content-Type错误，期望 application/json，实际 {response.content_type}"
        
        data = response.get_json()
        assert data is not None, "响应体不是有效的JSON"
        
        # 验证基本结构
        assert 'code' in data, "响应缺少code字段"
        assert data['code'] == expected_status, \
            f"响应code字段错误，期望 {expected_status}，实际 {data['code']}"
        
        if expected_status == 200:
            assert 'data' in data or 'message' in data, "成功响应应该包含data或message字段"
        else:
            assert 'message' in data, "错误响应应该包含message字段"
        
        # 验证自定义字段
        if expected_fields:
            if 'data' in data and expected_fields:
                if isinstance(expected_fields, dict):
                    for field, field_type in expected_fields.items():
                        assert field in data['data'], f"响应数据缺少字段: {field}"
                        if field_type is not None:
                            assert isinstance(data['data'][field], field_type), \
                                f"字段 {field} 类型错误"
        
        return data
    
    return _assert_response


# ==================== Steps 测试相关 Fixtures ====================

@pytest.fixture
def sample_goto_step():
    """提供goto步骤数据"""
    return {
        'action': 'goto',
        'params': {
            'url': 'https://example.com'
        },
        'description': '访问示例网站',
        'required': True
    }


@pytest.fixture
def sample_ai_input_step():
    """提供ai_input步骤数据"""
    return {
        'action': 'ai_input',
        'params': {
            'locate': '搜索框',
            'text': '测试搜索内容'
        },
        'description': '在搜索框输入文本',
        'required': True
    }


@pytest.fixture
def sample_ai_tap_step():
    """提供ai_tap步骤数据"""
    return {
        'action': 'ai_tap',
        'params': {
            'locate': '提交按钮'
        },
        'description': '点击提交按钮',
        'required': True
    }


@pytest.fixture
def sample_ai_assert_step():
    """提供ai_assert步骤数据"""
    return {
        'action': 'ai_assert',
        'params': {
            'prompt': '页面显示成功消息'
        },
        'description': '验证操作成功',
        'required': True
    }


@pytest.fixture
def sample_ai_wait_for_step():
    """提供ai_wait_for步骤数据"""
    return {
        'action': 'ai_wait_for',
        'params': {
            'locate': '加载完成提示',
            'timeout': 5000
        },
        'description': '等待页面加载完成',
        'required': True
    }


@pytest.fixture
def sample_sleep_step():
    """提供sleep步骤数据"""
    return {
        'action': 'sleep',
        'params': {
            'duration': 2000
        },
        'description': '等待2秒',
        'required': False
    }


@pytest.fixture
def sample_screenshot_step():
    """提供screenshot步骤数据"""
    return {
        'action': 'screenshot',
        'params': {
            'name': 'test_screenshot'
        },
        'description': '截取屏幕截图',
        'required': False
    }


@pytest.fixture
def create_testcase_with_steps(db_session):
    """创建包含步骤的测试用例工厂函数"""
    def _create_testcase_with_steps(step_count=2, **kwargs):
        # 生成默认步骤
        default_steps = [
            {
                'action': 'goto',
                'params': {'url': f'https://example{i}.com'},
                'description': f'访问网站{i+1}'
            } for i in range(step_count)
        ]
        
        # 设置默认值
        defaults = {
            'name': f'包含{step_count}个步骤的测试用例',
            'description': '用于步骤API测试的测试用例',
            'steps': json.dumps(default_steps),
            'category': '步骤测试',
            'priority': 2,
            'tags': 'steps,api,test',
            'created_by': 'test_user',
            'is_active': True
        }
        defaults.update(kwargs)
        
        testcase = TestCase(**defaults)
        db_session.add(testcase)
        db_session.commit()
        return testcase
    
    return _create_testcase_with_steps


@pytest.fixture
def invalid_step_data():
    """提供无效的步骤数据（用于错误测试）"""
    return [
        # 缺少action字段
        {
            'params': {'url': 'https://example.com'},
            'description': '缺少action字段的步骤'
        },
        # 无效的action类型
        {
            'action': 'invalid_action_type',
            'params': {},
            'description': '无效的动作类型'
        },
        # goto缺少url参数
        {
            'action': 'goto',
            'params': {},
            'description': 'goto动作缺少url参数'
        },
        # ai_input缺少必需参数
        {
            'action': 'ai_input',
            'params': {},
            'description': 'ai_input动作缺少必需参数'
        },
        # ai_tap缺少locate参数
        {
            'action': 'ai_tap',
            'params': {},
            'description': 'ai_tap动作缺少locate参数'
        }
    ]


@pytest.fixture
def all_supported_actions():
    """提供所有支持的动作类型列表"""
    return [
        'goto', 'ai_input', 'ai_tap', 'ai_assert', 'ai_wait_for',
        'ai_scroll', 'ai_drag', 'sleep', 'screenshot', 'refresh',
        'back', 'ai_select', 'ai_upload', 'ai_check'
    ]


# ==================== Execution 测试相关 Fixtures ====================

@pytest.fixture
def sample_execution_data():
    """提供执行创建数据"""
    return {
        'testcase_id': None,  # 将在测试中设置
        'mode': 'headless',
        'browser': 'chrome',
        'executed_by': 'test_user'
    }


@pytest.fixture
def sample_execution_start_data():
    """提供MidScene执行开始通知数据"""
    return {
        'execution_id': 'test-exec-start-001',
        'testcase_id': 1,  # 将在测试中设置为实际的testcase_id
        'mode': 'headless',
        'browser': 'chrome',
        'executed_by': 'midscene_user'
    }


@pytest.fixture
def sample_execution_result_data():
    """提供MidScene执行结果数据"""
    from datetime import datetime
    return {
        'execution_id': 'test-exec-result-001',
        'status': 'success',
        'end_time': datetime.utcnow().isoformat(),
        'duration': 1500,
        'steps_total': 3,
        'steps_passed': 3,
        'steps_failed': 0,
        'result_summary': {
            'total_steps': 3,
            'passed_steps': 3,
            'failed_steps': 0,
            'success_rate': 100.0
        }
    }


@pytest.fixture
def sample_execution_result_with_steps():
    """提供包含步骤详情的MidScene执行结果数据"""
    from datetime import datetime
    return {
        'execution_id': 'test-exec-with-steps-001',
        'status': 'success',
        'end_time': datetime.utcnow().isoformat(),
        'duration': 2000,
        'steps_total': 2,
        'steps_passed': 2,
        'steps_failed': 0,
        'result_summary': {
            'total_steps': 2,
            'passed_steps': 2,
            'failed_steps': 0
        },
        'steps': [
            {
                'index': 0,
                'description': '访问测试网站',
                'status': 'success',
                'start_time': datetime.utcnow().isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'duration': 1000,
                'screenshot_path': '/screenshots/step1.png',
                'ai_confidence': 0.95
            },
            {
                'index': 1,
                'description': '点击按钮',
                'status': 'success',
                'start_time': datetime.utcnow().isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'duration': 500,
                'screenshot_path': '/screenshots/step2.png',
                'ai_confidence': 0.88
            }
        ]
    }


@pytest.fixture
def create_execution_history(db_session):
    """创建执行历史记录的工厂函数"""
    def _create_execution_history(**kwargs):
        from datetime import datetime
        import uuid
        
        # 创建测试用例（如果没有提供test_case_id）
        if 'test_case_id' not in kwargs:
            testcase = TestCase(
                name='测试用例用于执行',
                description='用于执行测试的测试用例',
                steps=json.dumps([
                    {'action': 'goto', 'params': {'url': 'https://example.com'}}
                ]),
                created_by='test_user',
                is_active=True
            )
            db_session.add(testcase)
            db_session.commit()
            kwargs['test_case_id'] = testcase.id
        
        # 设置默认值
        defaults = {
            'execution_id': f'test-exec-{uuid.uuid4().hex[:8]}',
            'status': 'success',
            'mode': 'headless',
            'browser': 'chrome',
            'start_time': datetime.utcnow(),
            'end_time': datetime.utcnow(),
            'duration': 1000,
            'steps_total': 1,
            'steps_passed': 1,
            'steps_failed': 0,
            'result_summary': json.dumps({'total': 1, 'passed': 1, 'failed': 0}),
            'executed_by': 'test_user'
        }
        defaults.update(kwargs)
        
        execution = ExecutionHistory(**defaults)
        db_session.add(execution)
        db_session.commit()
        return execution
    
    return _create_execution_history


@pytest.fixture
def create_step_execution(db_session):
    """创建步骤执行记录的工厂函数"""
    def _create_step_execution(**kwargs):
        from datetime import datetime
        
        # 设置默认值
        defaults = {
            'execution_id': 'test-exec-001',
            'step_index': 0,
            'step_description': '测试步骤',
            'status': 'success',
            'start_time': datetime.utcnow(),
            'end_time': datetime.utcnow(),
            'duration': 500,
            'screenshot_path': '/screenshots/step.png',
            'ai_confidence': 0.9
        }
        defaults.update(kwargs)
        
        step_execution = StepExecution(**defaults)
        db_session.add(step_execution)
        db_session.commit()
        return step_execution
    
    return _create_step_execution


@pytest.fixture
def execution_statuses():
    """提供所有支持的执行状态列表"""
    return ['running', 'success', 'failed', 'stopped']


@pytest.fixture
def browser_types():
    """提供所有支持的浏览器类型列表"""
    return ['chrome', 'firefox', 'safari', 'edge']


@pytest.fixture
def execution_modes():
    """提供所有支持的执行模式列表"""
    return ['headless', 'browser']