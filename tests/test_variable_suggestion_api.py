"""
变量建议API测试套件
测试STORY-011的所有验收标准
"""

import pytest
import json
from unittest.mock import Mock, patch
from flask import Flask
from web_gui.api_routes import api_bp
from web_gui.services.variable_suggestion_service import VariableSuggestionService

class TestVariableSuggestionAPI:
    """变量建议API测试类"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """创建模拟服务"""
        with patch('web_gui.services.variable_suggestion_service.VariableSuggestionService.get_service') as mock:
            service = Mock(spec=VariableSuggestionService)
            mock.return_value = service
            yield service
    
    def test_get_variable_suggestions_success(self, client, mock_service):
        """测试AC-1: 变量建议API - 成功场景"""
        # 模拟数据
        mock_service.get_variable_suggestions.return_value = {
            'execution_id': 'test-exec-001',
            'current_step_index': 5,
            'variables': [
                {
                    'name': 'product_info',
                    'data_type': 'object',
                    'source_step_index': 2,
                    'source_api_method': 'aiQuery',
                    'created_at': '2025-01-30T10:00:00Z',
                    'preview_value': '{"name": "iPhone 15", "price": 999}',
                    'properties': [
                        {'name': 'name', 'type': 'string', 'value': 'iPhone 15', 'path': 'product_info.name'},
                        {'name': 'price', 'type': 'number', 'value': 999, 'path': 'product_info.price'}
                    ]
                },
                {
                    'name': 'user_name',
                    'data_type': 'string',
                    'source_step_index': 1,
                    'source_api_method': 'aiInput',
                    'created_at': '2025-01-30T09:30:00Z',
                    'preview_value': '"张三"'
                }
            ],
            'total_count': 2
        }
        
        # 发送请求
        response = client.get('/api/v1/executions/test-exec-001/variable-suggestions?step_index=5')
        
        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['execution_id'] == 'test-exec-001'
        assert data['current_step_index'] == 5
        assert data['total_count'] == 2
        assert len(data['variables']) == 2
        
        # 验证变量数据结构
        product_var = data['variables'][0]
        assert product_var['name'] == 'product_info'
        assert product_var['data_type'] == 'object'
        assert product_var['source_step_index'] == 2
        assert 'properties' in product_var
        
        # 验证服务调用
        mock_service.get_variable_suggestions.assert_called_once_with(
            step_index=5,
            include_properties=True,
            limit=None
        )
    
    def test_get_variable_suggestions_with_params(self, client, mock_service):
        """测试变量建议API - 带参数"""
        mock_service.get_variable_suggestions.return_value = {
            'execution_id': 'test-exec-001',
            'current_step_index': 3,
            'variables': [],
            'total_count': 0
        }
        
        # 带所有参数的请求
        response = client.get(
            '/api/v1/executions/test-exec-001/variable-suggestions'
            '?step_index=3&include_properties=false&limit=5'
        )
        
        assert response.status_code == 200
        
        # 验证参数传递
        mock_service.get_variable_suggestions.assert_called_once_with(
            step_index=3,
            include_properties=False,
            limit=5
        )
    
    def test_get_variable_properties_success(self, client, mock_service):
        """测试AC-2: 对象属性探索API - 成功场景"""
        # 模拟数据
        mock_service.get_variable_properties.return_value = {
            'variable_name': 'product_info',
            'data_type': 'object',
            'properties': [
                {
                    'name': 'name',
                    'type': 'string',
                    'value': 'iPhone 15',
                    'path': 'product_info.name'
                },
                {
                    'name': 'price',
                    'type': 'number',
                    'value': 999,
                    'path': 'product_info.price'
                },
                {
                    'name': 'specs',
                    'type': 'object',
                    'value': {'color': 'blue', 'storage': '128GB'},
                    'path': 'product_info.specs',
                    'properties': [
                        {'name': 'color', 'type': 'string', 'value': 'blue', 'path': 'product_info.specs.color'},
                        {'name': 'storage', 'type': 'string', 'value': '128GB', 'path': 'product_info.specs.storage'}
                    ]
                }
            ]
        }
        
        # 发送请求
        response = client.get('/api/v1/executions/test-exec-001/variables/product_info/properties')
        
        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['variable_name'] == 'product_info'
        assert data['data_type'] == 'object'
        assert len(data['properties']) == 3
        
        # 验证嵌套属性
        specs_prop = data['properties'][2]
        assert specs_prop['name'] == 'specs'
        assert 'properties' in specs_prop
        assert len(specs_prop['properties']) == 2
        
        # 验证服务调用
        mock_service.get_variable_properties.assert_called_once_with('product_info', max_depth=3)
    
    def test_get_variable_properties_not_found(self, client, mock_service):
        """测试属性API - 变量不存在"""
        mock_service.get_variable_properties.return_value = None
        
        response = client.get('/api/v1/executions/test-exec-001/variables/nonexistent/properties')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'nonexistent' in data['error']
    
    def test_search_variables_success(self, client, mock_service):
        """测试AC-3: 模糊搜索API - 成功场景"""
        # 模拟数据
        mock_service.search_variables.return_value = {
            'query': 'prod',
            'matches': [
                {
                    'name': 'product_info',
                    'match_score': 0.95,
                    'highlighted_name': '<mark>prod</mark>uct_info',
                    'data_type': 'object',
                    'source_step_index': 2,
                    'preview_value': '{"name": "iPhone", "price": 999}'
                },
                {
                    'name': 'product_name',
                    'match_score': 0.88,
                    'highlighted_name': '<mark>prod</mark>uct_name',
                    'data_type': 'string',
                    'source_step_index': 1,
                    'preview_value': '"iPhone 15"'
                }
            ],
            'count': 2
        }
        
        # 发送请求
        response = client.get('/api/v1/executions/test-exec-001/variable-suggestions/search?q=prod&limit=10')
        
        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['query'] == 'prod'
        assert data['count'] == 2
        assert len(data['matches']) == 2
        
        # 验证匹配结果
        first_match = data['matches'][0]
        assert first_match['name'] == 'product_info'
        assert first_match['match_score'] == 0.95
        assert '<mark>' in first_match['highlighted_name']
        
        # 验证服务调用
        mock_service.search_variables.assert_called_once_with(
            query='prod',
            limit=10,
            step_index=None
        )
    
    def test_search_variables_empty_query(self, client, mock_service):
        """测试搜索API - 空查询"""
        response = client.get('/api/v1/executions/test-exec-001/variable-suggestions/search?q=')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert '搜索查询不能为空' in data['error']
    
    def test_validate_variable_references_success(self, client, mock_service):
        """测试AC-4: 变量引用验证API - 成功场景"""
        # 模拟数据
        mock_service.validate_references.return_value = [
            {
                'reference': '${product_info.name}',
                'is_valid': True,
                'resolved_value': 'iPhone 15',
                'data_type': 'str'
            },
            {
                'reference': '${product_info.specs.color}',
                'is_valid': True,
                'resolved_value': 'blue',
                'data_type': 'str'
            },
            {
                'reference': '${undefined_var}',
                'is_valid': False,
                'error': "变量 'undefined_var' 未定义",
                'suggestion': '可用变量: product_info, user_name, item_count'
            },
            {
                'reference': '${product_info.invalid_prop}',
                'is_valid': False,
                'error': "属性 'invalid_prop' 在对象中不存在",
                'suggestion': '可用属性: name, price, specs'
            }
        ]
        
        # 请求数据
        request_data = {
            'references': [
                '${product_info.name}',
                '${product_info.specs.color}',
                '${undefined_var}',
                '${product_info.invalid_prop}'
            ],
            'step_index': 5
        }
        
        # 发送请求
        response = client.post(
            '/api/v1/executions/test-exec-001/variables/validate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'validation_results' in data
        results = data['validation_results']
        assert len(results) == 4
        
        # 验证成功的引用
        valid_result = results[0]
        assert valid_result['reference'] == '${product_info.name}'
        assert valid_result['is_valid'] is True
        assert valid_result['resolved_value'] == 'iPhone 15'
        
        # 验证失败的引用
        invalid_result = results[2]
        assert invalid_result['reference'] == '${undefined_var}'
        assert invalid_result['is_valid'] is False
        assert 'undefined_var' in invalid_result['error']
        assert 'suggestion' in invalid_result
        
        # 验证服务调用
        mock_service.validate_references.assert_called_once_with(
            references=request_data['references'],
            step_index=5
        )
    
    def test_validate_variable_references_invalid_request(self, client, mock_service):
        """测试验证API - 无效请求"""
        # 缺少references字段
        response = client.post(
            '/api/v1/executions/test-exec-001/variables/validate',
            data=json.dumps({'step_index': 5}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert '请提供要验证的变量引用' in data['error']
        
        # references不是数组
        response = client.post(
            '/api/v1/executions/test-exec-001/variables/validate',
            data=json.dumps({'references': 'not_a_list'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'references必须是数组' in data['error']
    
    def test_get_variables_status_success(self, client, mock_service):
        """测试AC-5: 实时变量状态API - 成功场景"""
        # 模拟数据
        mock_service.get_variables_status.return_value = {
            'execution_status': 'running',
            'current_step_index': 5,
            'variables_count': 3,
            'variables': [
                {
                    'name': 'product_info',
                    'status': 'available',
                    'last_updated': '2025-01-30T10:05:00Z',
                    'usage_count': 2
                },
                {
                    'name': 'user_name',
                    'status': 'available',
                    'last_updated': '2025-01-30T10:01:00Z',
                    'usage_count': 1
                },
                {
                    'name': 'order_total',
                    'status': 'available',
                    'last_updated': '2025-01-30T10:03:00Z',
                    'usage_count': 0
                }
            ],
            'recent_references': [
                {
                    'step_index': 4,
                    'reference': '${product_info.price}',
                    'status': 'success'
                }
            ]
        }
        
        # 发送请求
        response = client.get('/api/v1/executions/test-exec-001/variables/status')
        
        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['execution_id'] == 'test-exec-001'
        assert data['execution_status'] == 'running'
        assert data['variables_count'] == 3
        assert len(data['variables']) == 3
        assert len(data['recent_references']) == 1
        
        # 验证变量状态
        var_status = data['variables'][0]
        assert var_status['name'] == 'product_info'
        assert var_status['status'] == 'available'
        assert var_status['usage_count'] == 2
        
        # 验证服务调用
        mock_service.get_variables_status.assert_called_once()
    
    def test_api_error_handling(self, client, mock_service):
        """测试API错误处理"""
        # 模拟服务异常
        mock_service.get_variable_suggestions.side_effect = Exception("数据库连接失败")
        
        response = client.get('/api/v1/executions/test-exec-001/variable-suggestions')
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert '数据库连接失败' in data['error']

class TestLegacyAPICompatibility:
    """测试向后兼容的旧API端点"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """创建模拟服务"""
        with patch('web_gui.services.variable_suggestion_service.VariableSuggestionService.get_service') as mock:
            service = Mock(spec=VariableSuggestionService)
            mock.return_value = service
            yield service
    
    def test_legacy_variable_suggestions_api(self, client, mock_service):
        """测试旧版变量建议API"""
        # 模拟数据
        mock_service.get_variable_suggestions.return_value = {
            'execution_id': 'test-exec-001',
            'current_step_index': None,
            'variables': [
                {
                    'name': 'test_var',
                    'data_type': 'string',
                    'source_step_index': 1,
                    'source_api_method': 'aiInput',
                    'created_at': '2025-01-30T10:00:00Z',
                    'preview_value': '"test_value"'
                }
            ],
            'total_count': 1
        }
        
        # 发送请求到旧端点
        response = client.get('/api/executions/test-exec-001/variable-suggestions')
        
        # 验证响应格式符合旧API
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['code'] == 200
        assert 'data' in data
        assert 'message' in data
        assert data['data']['execution_id'] == 'test-exec-001'
        assert len(data['data']['suggestions']) == 1
        
        # 验证数据格式转换
        suggestion = data['data']['suggestions'][0]
        assert suggestion['name'] == 'test_var'
        assert suggestion['dataType'] == 'string'
        assert 'preview' in suggestion
    
    def test_legacy_variable_properties_api(self, client, mock_service):
        """测试旧版变量属性API"""
        # 模拟数据
        mock_service.get_variable_properties.return_value = {
            'variable_name': 'test_obj',
            'data_type': 'object',
            'properties': [
                {'name': 'prop1', 'type': 'string', 'value': 'value1', 'path': 'test_obj.prop1'}
            ]
        }
        
        # 发送请求到旧端点
        response = client.get('/api/executions/test-exec-001/variables/test_obj/properties')
        
        # 验证响应格式符合旧API
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['code'] == 200
        assert 'data' in data
        assert data['data']['variable_name'] == 'test_obj'
        assert len(data['data']['properties']) == 1

class TestAPIPerformance:
    """API性能测试"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()
    
    def test_api_response_time(self, client):
        """测试API响应时间（AC-6: 性能要求）"""
        import time
        
        with patch('web_gui.services.variable_suggestion_service.VariableSuggestionService.get_service') as mock:
            service = Mock(spec=VariableSuggestionService)
            service.get_variable_suggestions.return_value = {
                'execution_id': 'test-exec-001',
                'variables': [],
                'total_count': 0
            }
            mock.return_value = service
            
            # 测试变量建议API响应时间
            start_time = time.time()
            response = client.get('/api/v1/executions/test-exec-001/variable-suggestions')
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            assert response.status_code == 200
            # 注意：这里的测试时间包括了mock开销，实际API应该更快
            assert response_time < 1000  # 允许1秒的测试环境开销
    
    def test_large_dataset_handling(self, client):
        """测试大数据集处理"""
        with patch('web_gui.services.variable_suggestion_service.VariableSuggestionService.get_service') as mock:
            service = Mock(spec=VariableSuggestionService)
            
            # 模拟大量变量
            large_dataset = {
                'execution_id': 'test-exec-001',
                'variables': [
                    {
                        'name': f'var_{i}',
                        'data_type': 'string',
                        'source_step_index': i % 10,
                        'source_api_method': 'aiInput',
                        'preview_value': f'"value_{i}"'
                    }
                    for i in range(100)
                ],
                'total_count': 100
            }
            service.get_variable_suggestions.return_value = large_dataset
            mock.return_value = service
            
            response = client.get('/api/v1/executions/test-exec-001/variable-suggestions')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['total_count'] == 100
            assert len(data['variables']) == 100

if __name__ == '__main__':
    pytest.main([__file__, '-v'])