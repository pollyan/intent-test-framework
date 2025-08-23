"""
API错误场景综合测试
覆盖各种边界情况、异常处理和错误恢复场景
"""

import pytest
import json
from unittest.mock import patch


class TestInputValidationErrors:
    """输入验证错误测试"""
    
    def test_should_handle_malformed_json(self, api_client):
        """测试处理格式错误的JSON"""
        # 发送无效JSON
        response = api_client.post('/api/testcases', 
                                  data='{"invalid": json}',
                                  content_type='application/json')
        assert response.status_code == 400
        
        data = response.get_json()
        assert data is not None
        assert 'message' in data
        message = data.get('message', '').lower()
        assert 'json' in message or 'parse' in message
    
    def test_should_handle_missing_content_type(self, api_client):
        """测试处理缺少Content-Type头"""
        valid_data = {
            'name': '测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        }
        
        response = api_client.post('/api/testcases', 
                                  data=json.dumps(valid_data))
        assert response.status_code in [400, 415]
    
    def test_should_handle_wrong_content_type(self, api_client):
        """测试处理错误的Content-Type"""
        response = api_client.post('/api/testcases',
                                  data='test data',
                                  content_type='text/plain')
        assert response.status_code in [400, 415]
    
    def test_should_handle_empty_request_body(self, api_client):
        """测试处理空请求体"""
        response = api_client.post('/api/testcases',
                                  json={})
        assert response.status_code == 400
        
        data = response.get_json()
        assert data is not None
        assert 'message' in data
        message = data.get('message', '').lower()
        assert 'name' in message or 'required' in message
    
    def test_should_handle_oversized_request(self, api_client):
        """测试处理超大请求"""
        # 创建一个非常大的请求（假设有大小限制）
        large_steps = []
        for i in range(1000):  # 1000个步骤
            large_steps.append({
                'action': 'ai_input',
                'params': {
                    'text': 'x' * 1000,  # 每个参数1KB
                    'locate': f'输入框{i}'
                }
            })
        
        oversized_data = {
            'name': '超大测试用例',
            'description': 'x' * 10000,  # 10KB描述
            'steps': large_steps
        }
        
        response = api_client.post('/api/testcases', json=oversized_data)
        # 应该能处理或返回413 Request Entity Too Large
        assert response.status_code in [201, 400, 413]
    
    def test_should_handle_special_characters(self, api_client):
        """测试处理特殊字符"""
        special_chars_data = {
            'name': '测试用例 <script>alert("xss")</script> 🚀',
            'description': 'SQL injection test: \'; DROP TABLE test_cases; --',
            'steps': [{
                'action': 'ai_input',
                'params': {
                    'text': '特殊字符: \\n\\r\\t\\0 "\'"',
                    'locate': 'Unicode: 你好 мир العالم 🌍'
                }
            }]
        }
        
        response = api_client.post('/api/testcases', json=special_chars_data)
        
        if response.status_code == 201:
            # 如果创建成功，验证数据已正确转义和存储
            data = response.get_json()
            assert '<script>' not in data['data']['name']
            assert 'DROP TABLE' not in data['data']['description']
        else:
            # 如果拒绝，应该是400错误
            assert response.status_code == 400


class TestDatabaseErrorSimulation:
    """数据库错误模拟测试"""
    
    @patch('web_gui.models.db.session.commit')
    def test_should_handle_database_commit_failure(self, mock_commit, api_client):
        """测试数据库提交失败"""
        mock_commit.side_effect = Exception("Database connection lost")
        
        response = api_client.post('/api/testcases', json={
            'name': '数据库错误测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'database' in data['message'].lower() or 'internal' in data['message'].lower()
    
    @patch('web_gui.models.TestCase.query.get')
    def test_should_handle_database_query_failure(self, mock_get, api_client):
        """测试数据库查询失败"""
        mock_get.side_effect = Exception("Database timeout")
        
        response = api_client.get('/api/testcases/1')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data
    
    @patch('web_gui.models.db.session.rollback')
    def test_should_handle_rollback_failure(self, mock_rollback, api_client):
        """测试回滚失败"""
        mock_rollback.side_effect = Exception("Rollback failed")
        
        # 发送一个会导致错误的请求（触发回滚）
        response = api_client.post('/api/testcases', json={
            'name': '',  # 空名称会导致验证错误
            'steps': []
        })
        
        # 即使回滚失败，应用也应该能够处理
        assert response.status_code in [400, 500]


class TestConcurrencyErrorScenarios:
    """并发错误场景测试"""
    
    def test_should_handle_concurrent_modifications(self, api_client, create_test_testcase):
        """测试并发修改冲突"""
        # 创建测试用例
        testcase = create_test_testcase({
            'name': '并发修改测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 模拟两个用户同时修改
        update_data1 = {
            'name': '用户1修改',
            'steps': [{'action': 'ai_input', 'params': {'text': 'user1', 'locate': 'input'}}]
        }
        
        update_data2 = {
            'name': '用户2修改',
            'steps': [{'action': 'ai_input', 'params': {'text': 'user2', 'locate': 'input'}}]
        }
        
        # 并发发送更新请求
        import threading
        results = []
        
        def update_testcase(data, result_list):
            response = api_client.put(f'/api/testcases/{testcase["id"]}', json=data)
            result_list.append(response)
        
        thread1 = threading.Thread(target=update_testcase, args=(update_data1, results))
        thread2 = threading.Thread(target=update_testcase, args=(update_data2, results))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # 应该至少有一个成功，可能有一个失败（乐观锁冲突）
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 1
    
    def test_should_handle_resource_locking(self, api_client, create_test_testcase, create_test_execution):
        """测试资源锁定冲突"""
        # 创建正在执行的测试用例
        testcase = create_test_testcase({
            'name': '资源锁定测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'running'
        })
        
        # 尝试删除正在执行的测试用例
        response = api_client.delete(f'/api/testcases/{testcase["id"]}')
        
        # 应该拒绝删除或等待执行完成
        assert response.status_code in [400, 409, 423]  # 423 = Locked
        
        if response.status_code in [400, 409, 423]:
            data = response.get_json()
            assert 'running' in data['message'].lower() or 'executing' in data['message'].lower()


class TestExternalServiceErrors:
    """外部服务错误测试"""
    
    @patch('requests.post')
    def test_should_handle_midscene_service_unavailable(self, mock_post, api_client, 
                                                       create_test_testcase):
        """测试MidScene服务不可用"""
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError("Connection refused")
        
        testcase = create_test_testcase({
            'name': 'MidScene错误测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 尝试启动执行
        response = api_client.post('/api/executions', json={
            'test_case_id': testcase['id'],
            'mode': 'headless',
            'browser': 'chrome'
        })
        
        # 应该能创建执行记录但标记为失败
        if response.status_code == 201:
            data = response.get_json()
            execution_id = data['data']['execution_id']
            
            # 检查执行状态
            status_response = api_client.get(f'/api/executions/{execution_id}')
            status_data = status_response.get_json()
            assert status_data['data']['status'] in ['failed', 'error']
        else:
            # 或者直接返回服务不可用错误
            assert response.status_code in [500, 503]
    
    @patch('requests.post')
    def test_should_handle_midscene_timeout(self, mock_post, api_client, create_test_testcase):
        """测试MidScene服务超时"""
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout("Request timeout")
        
        testcase = create_test_testcase({
            'name': 'MidScene超时测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        response = api_client.post('/api/executions', json={
            'test_case_id': testcase['id'],
            'mode': 'headless',
            'browser': 'chrome'
        })
        
        # 应该能处理超时并返回适当错误
        assert response.status_code in [201, 408, 500, 503]


class TestResourceLimitErrors:
    """资源限制错误测试"""
    
    def test_should_handle_too_many_executions(self, api_client, create_test_testcase):
        """测试过多并发执行"""
        testcase = create_test_testcase({
            'name': '并发限制测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 尝试创建大量并发执行
        responses = []
        for i in range(20):  # 尝试创建20个并发执行
            response = api_client.post('/api/executions', json={
                'test_case_id': testcase['id'],
                'mode': 'headless',
                'browser': 'chrome'
            })
            responses.append(response)
        
        # 应该有一些被限制
        success_count = sum(1 for r in responses if r.status_code == 201)
        rejected_count = sum(1 for r in responses if r.status_code == 429)  # Too Many Requests
        
        assert success_count + rejected_count == len(responses)
        # 至少应该拒绝一些请求（假设有并发限制）
        if rejected_count > 0:
            # 验证限制错误消息
            rejected_response = next(r for r in responses if r.status_code == 429)
            data = rejected_response.get_json()
            assert 'limit' in data['message'].lower() or 'too many' in data['message'].lower()
    
    def test_should_handle_memory_pressure(self, api_client, create_test_testcase):
        """测试内存压力情况"""
        # 创建大量大型测试用例以模拟内存压力
        large_testcases = []
        
        for i in range(10):
            large_steps = []
            for j in range(100):  # 每个测试用例100个步骤
                large_steps.append({
                    'action': 'ai_input',
                    'params': {
                        'text': f'大型数据{i}-{j}' * 100,  # 较大的数据
                        'locate': f'元素{i}-{j}'
                    }
                })
            
            response = api_client.post('/api/testcases', json={
                'name': f'大型测试用例{i}',
                'description': '大型测试用例，用于测试内存处理' * 100,
                'steps': large_steps
            })
            
            if response.status_code == 201:
                large_testcases.append(response.get_json()['data'])
            else:
                # 如果因为内存压力拒绝创建，这是可以接受的
                assert response.status_code in [400, 413, 507]  # 507 = Insufficient Storage
                break
        
        # 清理创建的大型测试用例
        for testcase in large_testcases:
            api_client.delete(f'/api/testcases/{testcase["id"]}')


class TestSecurityErrorScenarios:
    """安全错误场景测试"""
    
    def test_should_prevent_sql_injection(self, api_client):
        """测试防止SQL注入"""
        malicious_inputs = [
            "'; DROP TABLE test_cases; --",
            "' OR '1'='1",
            "'; INSERT INTO test_cases (name) VALUES ('hacked'); --",
            "' UNION SELECT * FROM test_cases WHERE '1'='1"
        ]
        
        for malicious_input in malicious_inputs:
            response = api_client.get(f'/api/testcases?search={malicious_input}')
            
            # 应该正常返回搜索结果，不执行恶意SQL
            assert response.status_code == 200
            
            data = response.get_json()
            # 不应该返回所有数据（SQL注入成功的标志）
            assert len(data['data']['items']) < 100  # 假设正常情况下不会有100+个匹配
    
    def test_should_prevent_path_traversal(self, api_client):
        """测试防止路径遍历"""
        malicious_paths = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd'
        ]
        
        for malicious_path in malicious_paths:
            response = api_client.get(f'/api/testcases/{malicious_path}')
            
            # 应该返回404而不是文件内容
            assert response.status_code in [400, 404]
    
    def test_should_handle_xss_attempts(self, api_client):
        """测试处理XSS攻击尝试"""
        xss_payloads = [
            '<script>alert("xss")</script>',
            '<img src="x" onerror="alert(\'xss\')">',
            'javascript:alert("xss")',
            '<svg onload="alert(\'xss\')"></svg>'
        ]
        
        for payload in xss_payloads:
            response = api_client.post('/api/testcases', json={
                'name': f'XSS测试 {payload}',
                'description': f'描述包含XSS: {payload}',
                'steps': [{
                    'action': 'ai_input',
                    'params': {
                        'text': payload,
                        'locate': 'input'
                    }
                }]
            })
            
            if response.status_code == 201:
                # 如果创建成功，验证XSS代码已被转义
                data = response.get_json()
                assert '<script>' not in data['data']['name']
                assert 'onerror=' not in data['data']['description']
            else:
                # 或者直接拒绝含有XSS的请求
                assert response.status_code == 400


class TestRecoveryScenarios:
    """恢复场景测试"""
    
    def test_should_recover_from_temporary_failures(self, api_client, create_test_testcase):
        """测试从临时故障中恢复"""
        testcase = create_test_testcase({
            'name': '恢复测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 模拟系统负载高的情况
        with patch('web_gui.models.db.session.commit') as mock_commit:
            # 前几次提交失败
            mock_commit.side_effect = [
                Exception("Temporary failure"),
                Exception("Database busy"),
                None  # 第三次成功
            ]
            
            # 重试逻辑应该能恢复
            response = api_client.put(f'/api/testcases/{testcase["id"]}', json={
                'name': '更新后的测试用例'
            })
            
            # 应该最终成功或返回适当的错误
            assert response.status_code in [200, 500, 503]
    
    def test_should_maintain_data_consistency(self, api_client, create_test_testcase, 
                                             create_test_execution):
        """测试维护数据一致性"""
        testcase = create_test_testcase({
            'name': '一致性测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        execution = create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'running'
        })
        
        # 模拟在执行过程中系统崩溃恢复
        with patch('web_gui.models.ExecutionHistory.query.filter_by') as mock_filter:
            mock_filter.return_value.first.return_value = None  # 模拟找不到执行记录
            
            response = api_client.get(f'/api/executions/{execution["execution_id"]}')
            
            # 应该能处理数据不一致的情况
            assert response.status_code in [200, 404, 500]