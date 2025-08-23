"""
系统健康检查和监控API测试
测试系统状态、错误监控、性能指标等接口
"""

import pytest
import json


class TestHealthCheckAPI:
    """基础健康检查API测试"""
    
    def test_should_return_basic_health_status(self, api_client, assert_api_response):
        """测试基础健康检查端点"""
        response = api_client.get('/api/health')
        data = assert_api_response(response, 200, {
            'status': str,
            'timestamp': str,
            'version': str
        })
        
        assert data['data']['status'] == 'ok'
        assert 'timestamp' in data['data']
        assert 'version' in data['data']
    
    def test_should_return_detailed_health_status(self, api_client, assert_api_response):
        """测试详细健康检查"""
        response = api_client.get('/api/health/detailed')
        data = assert_api_response(response, 200, {
            'status': str,
            'components': dict,
            'timestamp': str
        })
        
        assert data['data']['status'] in ['ok', 'degraded', 'down']
        assert 'database' in data['data']['components']
        assert 'midscene_service' in data['data']['components']
        
        # 检查组件健康状态
        db_status = data['data']['components']['database']
        assert 'status' in db_status
        assert 'response_time' in db_status
        assert db_status['status'] in ['ok', 'error']
    
    def test_should_check_database_connectivity(self, api_client, assert_api_response):
        """测试数据库连接健康检查"""
        response = api_client.get('/api/health/database')
        data = assert_api_response(response, 200, {
            'status': str,
            'connection': str,
            'response_time': (int, float)
        })
        
        assert data['data']['status'] == 'ok'
        assert data['data']['connection'] in ['ok', 'error']
        assert data['data']['response_time'] >= 0
    
    def test_should_check_midscene_service_status(self, api_client):
        """测试MidScene服务健康检查"""
        response = api_client.get('/api/health/midscene')
        
        # MidScene服务可能不在运行，所以状态码可能是200或503
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.get_json()
            assert data['data']['status'] in ['ok', 'error']
            assert 'response_time' in data['data']
        else:
            # 服务不可用的情况
            data = response.get_json()
            assert data['data']['status'] == 'error'


class TestSystemMetricsAPI:
    """系统指标监控API测试"""
    
    def test_should_get_system_metrics(self, api_client, assert_api_response):
        """测试获取系统指标"""
        response = api_client.get('/api/health/metrics')
        data = assert_api_response(response, 200, {
            'cpu_usage': (int, float),
            'memory_usage': (int, float),
            'disk_usage': (int, float),
            'uptime': (int, float)
        })
        
        assert 0 <= data['data']['cpu_usage'] <= 100
        assert 0 <= data['data']['memory_usage'] <= 100
        assert 0 <= data['data']['disk_usage'] <= 100
        assert data['data']['uptime'] >= 0
    
    def test_should_get_application_metrics(self, api_client, create_test_testcase, 
                                           create_test_execution, assert_api_response):
        """测试获取应用程序指标"""
        # 创建测试数据以产生应用指标
        testcase = create_test_testcase({
            'name': '指标测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'success'
        })
        
        response = api_client.get('/api/health/metrics/application')
        data = assert_api_response(response, 200, {
            'active_connections': int,
            'total_requests': int,
            'request_rate': (int, float),
            'error_rate': (int, float),
            'avg_response_time': (int, float)
        })
        
        assert data['data']['active_connections'] >= 0
        assert data['data']['total_requests'] >= 0
        assert data['data']['request_rate'] >= 0
        assert 0 <= data['data']['error_rate'] <= 100
    
    def test_should_get_database_metrics(self, api_client, assert_api_response):
        """测试获取数据库指标"""
        response = api_client.get('/api/health/metrics/database')
        data = assert_api_response(response, 200, {
            'connection_pool_size': int,
            'active_connections': int,
            'query_count': int,
            'slow_queries': int,
            'avg_query_time': (int, float)
        })
        
        assert data['data']['connection_pool_size'] >= 0
        assert data['data']['active_connections'] >= 0
        assert data['data']['query_count'] >= 0
        assert data['data']['slow_queries'] >= 0
        assert data['data']['avg_query_time'] >= 0


class TestErrorMonitoringAPI:
    """错误监控API测试"""
    
    def test_should_get_recent_errors_empty(self, api_client, assert_api_response):
        """测试获取空的最近错误列表"""
        response = api_client.get('/api/health/errors')
        data = assert_api_response(response, 200, {
            'errors': list,
            'total_count': int,
            'error_rate': (int, float)
        })
        
        assert data['data']['errors'] == []
        assert data['data']['total_count'] == 0
        assert data['data']['error_rate'] == 0
    
    def test_should_get_recent_errors_with_data(self, api_client, create_test_testcase, 
                                               create_test_execution, assert_api_response):
        """测试获取包含数据的最近错误"""
        # 创建失败的执行记录以产生错误
        testcase = create_test_testcase({
            'name': '错误监控测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'failed',
            'error_message': 'Element not found: 登录按钮',
            'error_stack': 'ElementNotFoundError: Could not locate element...'
        })
        
        response = api_client.get('/api/health/errors')
        data = assert_api_response(response, 200)
        
        assert data['data']['total_count'] >= 1
        assert len(data['data']['errors']) >= 1
        assert data['data']['error_rate'] > 0
        
        # 检查错误数据结构
        error = data['data']['errors'][0]
        assert 'timestamp' in error
        assert 'level' in error
        assert 'message' in error
        assert 'source' in error
    
    def test_should_get_error_statistics(self, api_client, create_test_testcase, 
                                        create_test_execution, assert_api_response):
        """测试获取错误统计数据"""
        # 创建不同类型的错误
        testcase = create_test_testcase({
            'name': '错误统计测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        error_types = [
            'Element not found: 按钮',
            'Timeout waiting for element',
            'Element not found: 输入框',
            'Network error: Connection refused'
        ]
        
        for error_msg in error_types:
            create_test_execution({
                'test_case_id': testcase['id'],
                'status': 'failed',
                'error_message': error_msg
            })
        
        response = api_client.get('/api/health/errors/stats')
        data = assert_api_response(response, 200, {
            'total_errors': int,
            'error_categories': list,
            'most_common_errors': list,
            'error_trends': list
        })
        
        assert data['data']['total_errors'] >= 4
        assert len(data['data']['error_categories']) >= 1
        assert len(data['data']['most_common_errors']) >= 1
    
    def test_should_support_error_filtering(self, api_client, create_test_testcase, 
                                           create_test_execution, assert_api_response):
        """测试错误过滤功能"""
        testcase = create_test_testcase({
            'name': '错误过滤测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'failed',
            'error_message': 'Element not found: 搜索按钮'
        })
        
        # 按错误级别过滤
        response = api_client.get('/api/health/errors?level=error')
        assert response.status_code == 200
        
        # 按时间范围过滤
        response = api_client.get('/api/health/errors?hours=24')
        assert response.status_code == 200
        
        # 按错误类型过滤
        response = api_client.get('/api/health/errors?type=ElementNotFound')
        assert response.status_code == 200


class TestPerformanceMonitoringAPI:
    """性能监控API测试"""
    
    def test_should_get_performance_metrics(self, api_client, create_test_testcase, 
                                           create_test_execution, assert_api_response):
        """测试获取性能指标"""
        # 创建带有执行时间的测试数据
        testcase = create_test_testcase({
            'name': '性能监控测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'success',
            'duration': 5000  # 5秒
        })
        
        response = api_client.get('/api/health/performance')
        data = assert_api_response(response, 200, {
            'avg_response_time': (int, float),
            'max_response_time': (int, float),
            'min_response_time': (int, float),
            'requests_per_second': (int, float),
            'slow_requests_count': int
        })
        
        assert data['data']['avg_response_time'] >= 0
        assert data['data']['max_response_time'] >= data['data']['avg_response_time']
        assert data['data']['min_response_time'] <= data['data']['avg_response_time']
        assert data['data']['requests_per_second'] >= 0
        assert data['data']['slow_requests_count'] >= 0
    
    def test_should_get_performance_trends(self, api_client, create_test_testcase, 
                                          create_test_execution, assert_api_response):
        """测试获取性能趋势数据"""
        testcase = create_test_testcase({
            'name': '性能趋势测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 创建不同执行时间的记录
        durations = [3000, 4000, 5000, 3500, 4500]
        for duration in durations:
            create_test_execution({
                'test_case_id': testcase['id'],
                'status': 'success',
                'duration': duration
            })
        
        response = api_client.get('/api/health/performance/trends')
        data = assert_api_response(response, 200, {
            'hourly_trends': list,
            'daily_trends': list,
            'response_time_trends': list
        })
        
        assert len(data['data']['hourly_trends']) >= 0
        assert len(data['data']['daily_trends']) >= 0
        assert len(data['data']['response_time_trends']) >= 0


class TestHealthAPIErrorHandling:
    """健康检查API错误处理测试"""
    
    def test_should_handle_service_unavailable(self, api_client):
        """测试处理服务不可用情况"""
        # 测试访问不存在的健康检查端点
        response = api_client.get('/api/health/nonexistent-service')
        assert response.status_code == 404
    
    def test_should_handle_invalid_parameters(self, api_client):
        """测试处理无效参数"""
        # 无效的时间范围
        response = api_client.get('/api/health/errors?hours=invalid')
        assert response.status_code in [200, 400]  # 应该容错处理或返回400
        
        # 无效的错误级别
        response = api_client.get('/api/health/errors?level=invalid')
        assert response.status_code in [200, 400]
    
    def test_should_maintain_health_check_performance(self, api_client):
        """测试健康检查接口的响应性能"""
        import time
        
        # 健康检查应该快速响应（< 1秒）
        start_time = time.time()
        response = api_client.get('/api/health')
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 健康检查应该在1秒内响应
        
        # 详细健康检查也应该相对快速（< 3秒）
        start_time = time.time()
        response = api_client.get('/api/health/detailed')
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 3.0