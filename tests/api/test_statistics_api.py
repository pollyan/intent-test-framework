"""
统计分析API测试
测试测试报告、统计数据和分析功能接口
"""

import pytest
import json
from datetime import datetime, timedelta


class TestStatisticsReportsAPI:
    """统计报告API测试"""
    
    def test_should_get_failure_analysis_report_empty(self, api_client, assert_api_response):
        """测试获取空的失败分析报告"""
        response = api_client.get('/api/reports/failure-analysis')
        data = assert_api_response(response, 200, {
            'total_failures': int,
            'failure_rate': (int, float),
            'common_failures': list,
            'failure_trends': list
        })
        
        assert data['data']['total_failures'] == 0
        assert data['data']['failure_rate'] == 0
        assert data['data']['common_failures'] == []
    
    def test_should_get_failure_analysis_with_data(self, api_client, create_test_testcase, 
                                                   create_test_execution, assert_api_response):
        """测试获取包含数据的失败分析报告"""
        # 创建失败的执行记录
        testcase = create_test_testcase({
            'name': '失败分析测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'failed',
            'error_message': 'Element not found: 搜索按钮',
            'error_stack': 'Stack trace...'
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'failed',
            'error_message': 'Timeout waiting for element',
            'error_stack': 'Timeout error stack...'
        })
        
        response = api_client.get('/api/reports/failure-analysis')
        data = assert_api_response(response, 200)
        
        assert data['data']['total_failures'] >= 2
        assert data['data']['failure_rate'] > 0
        assert len(data['data']['common_failures']) >= 1
    
    def test_should_get_execution_trends_report(self, api_client, create_test_testcase, 
                                               create_test_execution, assert_api_response):
        """测试获取执行趋势报告"""
        # 创建多个执行记录
        testcase = create_test_testcase({
            'name': '趋势分析测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 创建不同状态的执行记录
        for status in ['success', 'failed', 'success', 'failed', 'success']:
            create_test_execution({
                'test_case_id': testcase['id'],
                'status': status
            })
        
        response = api_client.get('/api/reports/execution-trends')
        data = assert_api_response(response, 200, {
            'daily_trends': list,
            'success_rate_trend': list,
            'execution_count_trend': list
        })
        
        assert len(data['data']['daily_trends']) >= 0
    
    def test_should_get_testcase_performance_report(self, api_client, create_test_testcase, 
                                                   create_test_execution, assert_api_response):
        """测试获取测试用例性能报告"""
        testcase = create_test_testcase({
            'name': '性能测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 创建不同执行时间的记录
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'success',
            'duration': 5000  # 5秒
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'success',
            'duration': 8000  # 8秒
        })
        
        response = api_client.get('/api/reports/performance')
        data = assert_api_response(response, 200, {
            'avg_execution_time': (int, float),
            'slowest_testcases': list,
            'performance_trends': list
        })
        
        assert data['data']['avg_execution_time'] > 0
    
    def test_should_support_date_range_filtering(self, api_client, create_test_testcase, 
                                                 create_test_execution, assert_api_response):
        """测试支持日期范围过滤"""
        testcase = create_test_testcase({
            'name': '日期过滤测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'success'
        })
        
        # 测试最近7天的报告
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        response = api_client.get(f'/api/reports/failure-analysis?start_date={start_date}&end_date={end_date}')
        assert response.status_code == 200
        
        # 测试最近30天的报告
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        response = api_client.get(f'/api/reports/execution-trends?start_date={start_date}&end_date={end_date}')
        assert response.status_code == 200


class TestStatisticsDataAPI:
    """统计数据API测试"""
    
    def test_should_get_system_statistics_empty(self, api_client, assert_api_response):
        """测试获取空的系统统计数据"""
        response = api_client.get('/api/statistics/system')
        data = assert_api_response(response, 200, {
            'total_testcases': int,
            'total_executions': int,
            'active_testcases': int,
            'success_rate': (int, float),
            'avg_execution_time': (int, float)
        })
        
        assert data['data']['total_testcases'] == 0
        assert data['data']['total_executions'] == 0
        assert data['data']['active_testcases'] == 0
    
    def test_should_get_system_statistics_with_data(self, api_client, create_test_testcase, 
                                                   create_test_execution, assert_api_response):
        """测试获取包含数据的系统统计"""
        # 创建测试数据
        testcase1 = create_test_testcase({
            'name': '统计测试用例1',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example1.com'}}]
        })
        
        testcase2 = create_test_testcase({
            'name': '统计测试用例2',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example2.com'}}]
        })
        
        # 创建执行记录
        create_test_execution({'test_case_id': testcase1['id'], 'status': 'success', 'duration': 3000})
        create_test_execution({'test_case_id': testcase1['id'], 'status': 'failed', 'duration': 5000})
        create_test_execution({'test_case_id': testcase2['id'], 'status': 'success', 'duration': 4000})
        
        response = api_client.get('/api/statistics/system')
        data = assert_api_response(response, 200)
        
        assert data['data']['total_testcases'] >= 2
        assert data['data']['total_executions'] >= 3
        assert data['data']['active_testcases'] >= 2
        assert 0 <= data['data']['success_rate'] <= 100
        assert data['data']['avg_execution_time'] > 0
    
    def test_should_get_category_statistics(self, api_client, create_test_testcase, assert_api_response):
        """测试获取分类统计数据"""
        # 创建不同分类的测试用例
        create_test_testcase({
            'name': 'UI测试用例',
            'category': 'UI测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://ui-test.com'}}]
        })
        
        create_test_testcase({
            'name': 'API测试用例',
            'category': 'API测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://api-test.com'}}]
        })
        
        create_test_testcase({
            'name': 'API测试用例2',
            'category': 'API测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://api-test2.com'}}]
        })
        
        response = api_client.get('/api/statistics/categories')
        data = assert_api_response(response, 200, {
            'categories': list
        })
        
        assert len(data['data']['categories']) >= 2
        
        # 检查分类数据结构
        for category in data['data']['categories']:
            assert 'name' in category
            assert 'count' in category
            assert category['count'] > 0
        
        category_names = [cat['name'] for cat in data['data']['categories']]
        assert 'UI测试' in category_names
        assert 'API测试' in category_names
        
        # API测试分类应该有2个用例
        api_category = next(cat for cat in data['data']['categories'] if cat['name'] == 'API测试')
        assert api_category['count'] == 2
    
    def test_should_get_execution_statistics_by_testcase(self, api_client, create_test_testcase, 
                                                        create_test_execution, assert_api_response):
        """测试获取按测试用例分组的执行统计"""
        testcase = create_test_testcase({
            'name': '执行统计测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 创建多个执行记录
        create_test_execution({'test_case_id': testcase['id'], 'status': 'success'})
        create_test_execution({'test_case_id': testcase['id'], 'status': 'success'})
        create_test_execution({'test_case_id': testcase['id'], 'status': 'failed'})
        
        response = api_client.get('/api/statistics/executions-by-testcase')
        data = assert_api_response(response, 200, {
            'testcase_stats': list
        })
        
        assert len(data['data']['testcase_stats']) >= 1
        
        # 检查统计数据结构
        testcase_stat = data['data']['testcase_stats'][0]
        assert 'testcase_id' in testcase_stat
        assert 'testcase_name' in testcase_stat
        assert 'total_executions' in testcase_stat
        assert 'success_count' in testcase_stat
        assert 'failure_count' in testcase_stat
        assert 'success_rate' in testcase_stat
        
        assert testcase_stat['total_executions'] == 3
        assert testcase_stat['success_count'] == 2
        assert testcase_stat['failure_count'] == 1
        assert abs(testcase_stat['success_rate'] - 66.7) < 0.1


class TestStatisticsErrorHandling:
    """统计API错误处理测试"""
    
    def test_should_handle_invalid_date_range(self, api_client):
        """测试处理无效的日期范围"""
        # 无效的日期格式
        response = api_client.get('/api/reports/failure-analysis?start_date=invalid&end_date=2023-12-31')
        # 应该容错处理或返回400错误
        assert response.status_code in [200, 400]
        
        # 结束日期早于开始日期
        response = api_client.get('/api/reports/failure-analysis?start_date=2023-12-31&end_date=2023-01-01')
        assert response.status_code in [200, 400]
    
    def test_should_handle_large_data_queries(self, api_client, create_test_testcase, create_test_execution):
        """测试处理大数据量查询的性能"""
        # 创建大量测试数据（适量，避免测试超时）
        testcase = create_test_testcase({
            'name': '大数据测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 创建50个执行记录
        for i in range(50):
            status = 'success' if i % 2 == 0 else 'failed'
            create_test_execution({
                'test_case_id': testcase['id'],
                'status': status,
                'duration': 1000 + i * 100
            })
        
        # 测试各个统计API是否能处理大数据量
        response = api_client.get('/api/statistics/system')
        assert response.status_code == 200
        
        response = api_client.get('/api/reports/failure-analysis')
        assert response.status_code == 200
        
        response = api_client.get('/api/statistics/executions-by-testcase')
        assert response.status_code == 200
    
    def test_should_handle_nonexistent_endpoints(self, api_client):
        """测试处理不存在的统计端点"""
        response = api_client.get('/api/statistics/nonexistent')
        assert response.status_code == 404
        
        response = api_client.get('/api/reports/nonexistent')
        assert response.status_code == 404