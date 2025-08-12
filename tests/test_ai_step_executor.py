#!/usr/bin/env python3
"""
AI步骤执行器测试
测试STORY-005: AI方法返回值捕获功能
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.services.ai_step_executor import AIStepExecutor, StepExecutionResult
from web_gui.services.variable_resolver_service import VariableManager, get_variable_manager
from midscene_framework import (
    MidSceneDataExtractor,
    DataExtractionMethod,
    ExtractionRequest,
    ExtractionResult
)


class TestStepExecutionResult:
    """步骤执行结果数据类测试"""
    
    def test_basic_result(self):
        """测试基本结果"""
        result = StepExecutionResult(
            success=True,
            step_index=1,
            action="aiString",
            description="获取页面标题"
        )
        
        assert result.success is True
        assert result.step_index == 1
        assert result.action == "aiString"
        assert result.description == "获取页面标题"
        assert result.return_value is None
        assert result.variable_assigned is None
        assert result.execution_time == 0.0
        assert result.error_message is None
    
    def test_full_result(self):
        """测试完整结果"""
        result = StepExecutionResult(
            success=True,
            step_index=2,
            action="aiQuery",
            description="提取商品信息",
            return_value={"name": "iPhone", "price": 999.99},
            variable_assigned="product_info",
            execution_time=1.5,
            screenshot_path="/screenshots/test.png",
            metadata={"source": "test"}
        )
        
        assert result.success is True
        assert result.return_value == {"name": "iPhone", "price": 999.99}
        assert result.variable_assigned == "product_info"
        assert result.execution_time == 1.5
        assert result.screenshot_path == "/screenshots/test.png"
        assert result.metadata["source"] == "test"


class TestAIStepExecutor:
    """AI步骤执行器核心测试"""
    
    def test_init_mock_mode(self):
        """测试Mock模式初始化"""
        executor = AIStepExecutor(mock_mode=True)
        assert executor.mock_mode is True
        assert executor.midscene_client is None
        assert executor.data_extractor is not None
        assert len(executor.ai_extraction_methods) == 6
    
    def test_init_with_client(self):
        """测试带客户端初始化"""
        mock_client = Mock()
        executor = AIStepExecutor(midscene_client=mock_client)
        assert executor.mock_mode is False
        assert executor.midscene_client is mock_client
        assert executor.data_extractor is not None
    
    def test_ai_extraction_methods_mapping(self):
        """测试AI提取方法映射"""
        executor = AIStepExecutor(mock_mode=True)
        
        expected_methods = {
            'aiQuery': DataExtractionMethod.AI_QUERY,
            'aiString': DataExtractionMethod.AI_STRING,
            'aiNumber': DataExtractionMethod.AI_NUMBER,
            'aiBoolean': DataExtractionMethod.AI_BOOLEAN,
            'aiAsk': DataExtractionMethod.AI_ASK,
            'aiLocate': DataExtractionMethod.AI_LOCATE
        }
        
        assert executor.ai_extraction_methods == expected_methods
    
    def test_get_supported_actions(self):
        """测试获取支持的操作类型"""
        executor = AIStepExecutor(mock_mode=True)
        actions = executor.get_supported_actions()
        
        # 验证AI方法
        assert 'aiQuery' in actions
        assert 'aiString' in actions
        assert 'aiNumber' in actions
        assert 'aiBoolean' in actions
        assert 'aiAsk' in actions
        assert 'aiLocate' in actions
        
        # 验证传统方法
        assert 'navigate' in actions
        assert 'ai_input' in actions
        assert 'ai_tap' in actions
        assert 'ai_assert' in actions
        assert 'set_variable' in actions
        assert 'get_variable' in actions
    
    def test_get_stats(self):
        """测试获取执行器统计信息"""
        executor = AIStepExecutor(mock_mode=True)
        stats = executor.get_stats()
        
        assert 'mock_mode' in stats
        assert 'client_available' in stats
        assert 'supported_ai_methods' in stats
        assert 'ai_methods' in stats
        assert 'data_extractor_stats' in stats
        
        assert stats['mock_mode'] is True
        assert stats['client_available'] is False
        assert stats['supported_ai_methods'] == 6
        assert len(stats['ai_methods']) == 6


@pytest.mark.asyncio
class TestAIStepExecutorExecution:
    """AI步骤执行器执行测试"""
    
    async def test_execute_ai_query_step(self):
        """测试aiQuery步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        step_config = {
            "action": "aiQuery",
            "params": {
                "query": "获取商品信息",
                "dataDemand": "name: string, price: number"
            },
            "output_variable": "product_info",
            "description": "提取商品详细信息"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="test_exec_001",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.step_index == 0
        assert result.action == "aiQuery"
        assert result.description == "提取商品详细信息"
        assert result.return_value is not None
        assert isinstance(result.return_value, dict)
        assert result.variable_assigned == "product_info"
        assert result.execution_time > 0
        
        # 验证变量是否正确存储
        stored_value = variable_manager.get_variable("product_info")
        assert stored_value is not None
        assert stored_value == result.return_value
    
    async def test_execute_ai_string_step(self):
        """测试aiString步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        step_config = {
            "action": "aiString",
            "params": {
                "query": "页面标题文本"
            },
            "output_variable": "page_title",
            "description": "获取页面标题"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=1,
            execution_id="test_exec_002",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.action == "aiString"
        assert result.return_value is not None
        assert isinstance(result.return_value, str)
        assert result.variable_assigned == "page_title"
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("page_title")
        assert stored_value == result.return_value
    
    async def test_execute_ai_number_step(self):
        """测试aiNumber步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        step_config = {
            "action": "aiNumber",
            "params": {
                "query": "商品价格数值"
            },
            "output_variable": "current_price",
            "description": "获取当前商品价格"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=2,
            execution_id="test_exec_003",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.action == "aiNumber"
        assert result.return_value is not None
        assert isinstance(result.return_value, (int, float))
        assert result.variable_assigned == "current_price"
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("current_price")
        assert stored_value == result.return_value
    
    async def test_execute_ai_boolean_step(self):
        """测试aiBoolean步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        step_config = {
            "action": "aiBoolean",
            "params": {
                "query": "商品是否有库存"
            },
            "output_variable": "has_stock",
            "description": "检查商品库存状态"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=3,
            execution_id="test_exec_004",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.action == "aiBoolean"
        assert result.return_value is not None
        assert isinstance(result.return_value, bool)
        assert result.variable_assigned == "has_stock"
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("has_stock")
        assert stored_value == result.return_value
    
    async def test_execute_legacy_navigate_step(self):
        """测试传统navigate步骤执行"""
        mock_client = Mock()
        mock_client.goto = Mock(return_value="navigation_result")
        
        executor = AIStepExecutor(midscene_client=mock_client)
        variable_manager = VariableManager("test_execution")
        
        step_config = {
            "action": "navigate",
            "params": {
                "url": "https://example.com"
            },
            "description": "导航到测试页面"
        }
        
        with patch('asyncio.to_thread', return_value="navigation_result"):
            result = await executor.execute_step(
                step_config=step_config,
                step_index=0,
                execution_id="test_exec_005",
                variable_manager=variable_manager
            )
        
        assert result.success is True
        assert result.action == "navigate"
        assert result.return_value == "navigation_result"
        assert result.variable_assigned is None  # 没有配置output_variable
    
    async def test_execute_set_variable_step(self):
        """测试set_variable步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        step_config = {
            "action": "set_variable",
            "params": {
                "name": "test_var",
                "value": "test_value"
            },
            "description": "设置测试变量"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="test_exec_006",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.action == "set_variable"
        assert result.return_value == "test_value"
        assert result.variable_assigned == "test_var"
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("test_var")
        assert stored_value == "test_value"
    
    async def test_execute_get_variable_step(self):
        """测试get_variable步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        # 先设置一个变量
        variable_manager.store_variable("existing_var", "existing_value")
        
        step_config = {
            "action": "get_variable",
            "params": {
                "name": "existing_var"
            },
            "description": "获取已存在的变量"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="test_exec_007",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.action == "get_variable"
        assert result.return_value == "existing_value"
    
    async def test_execute_step_error_handling(self):
        """测试步骤执行错误处理"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        # 测试不支持的操作
        step_config = {
            "action": "unsupported_action",
            "params": {},
            "description": "测试不支持的操作"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="test_exec_008",
            variable_manager=variable_manager
        )
        
        assert result.success is False
        assert result.action == "unsupported_action"
        assert "不支持的操作类型" in result.error_message
        assert result.execution_time > 0
    
    async def test_execute_ai_extraction_failure(self):
        """测试AI提取失败处理"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        # Mock data_extractor返回失败结果
        failed_result = ExtractionResult(
            success=False,
            data=None,
            data_type="error",
            method="aiString",
            error="AI提取失败"
        )
        
        with patch.object(executor.data_extractor, 'extract_data', return_value=failed_result):
            step_config = {
                "action": "aiString",
                "params": {
                    "query": "测试查询"
                },
                "output_variable": "test_var",
                "description": "测试AI提取失败"
            }
            
            result = await executor.execute_step(
                step_config=step_config,
                step_index=0,
                execution_id="test_exec_009",
                variable_manager=variable_manager
            )
            
            assert result.success is False
            assert result.error_message == "AI提取失败"
            assert result.variable_assigned is None
            
            # 验证变量未被存储
            stored_value = variable_manager.get_variable("test_var")
            assert stored_value is None


@pytest.mark.asyncio
class TestAIStepExecutorTestCase:
    """完整测试用例执行测试"""
    
    async def test_execute_complete_test_case(self):
        """测试执行完整测试用例"""
        executor = AIStepExecutor(mock_mode=True)
        
        test_case = {
            "name": "商品信息提取测试",
            "steps": [
                {
                    "action": "navigate",
                    "params": {"url": "https://test-shop.com/product/123"},
                    "description": "导航到商品页面"
                },
                {
                    "action": "aiQuery",
                    "params": {
                        "query": "提取商品名称和价格",
                        "dataDemand": "name: string, price: number"
                    },
                    "output_variable": "product_info",
                    "description": "提取商品信息"
                },
                {
                    "action": "aiString",
                    "params": {"query": "商品描述文本"},
                    "output_variable": "product_description",
                    "description": "获取商品描述"
                },
                {
                    "action": "aiNumber",
                    "params": {"query": "商品评分"},
                    "output_variable": "product_rating",
                    "description": "获取商品评分"
                },
                {
                    "action": "aiBoolean",
                    "params": {"query": "商品是否有库存"},
                    "output_variable": "in_stock",
                    "description": "检查库存状态"
                }
            ]
        }
        
        # Mock导航步骤
        with patch('asyncio.to_thread', return_value="navigation_success"):
            result = await executor.execute_test_case(
                test_case=test_case,
                execution_id="test_case_001"
            )
        
        assert result['success'] is True
        assert result['total_steps'] == 5
        assert result['successful_steps'] == 5
        assert result['failed_steps'] == 0
        assert result['test_case_name'] == "商品信息提取测试"
        
        # 验证步骤结果
        steps = result['steps']
        assert len(steps) == 5
        
        # 验证每个步骤
        assert steps[0]['action'] == 'navigate'
        assert steps[1]['action'] == 'aiQuery'
        assert steps[1]['variable_assigned'] == 'product_info'
        assert steps[2]['action'] == 'aiString'
        assert steps[2]['variable_assigned'] == 'product_description'
        assert steps[3]['action'] == 'aiNumber'
        assert steps[3]['variable_assigned'] == 'product_rating'
        assert steps[4]['action'] == 'aiBoolean'
        assert steps[4]['variable_assigned'] == 'in_stock'
        
        # 验证变量导出
        variables = result['variables']
        assert 'product_info' in variables
        assert 'product_description' in variables
        assert 'product_rating' in variables
        assert 'in_stock' in variables
    
    async def test_execute_test_case_with_failure(self):
        """测试包含失败步骤的测试用例"""
        executor = AIStepExecutor(mock_mode=True)
        
        test_case = {
            "name": "失败测试用例",
            "steps": [
                {
                    "action": "aiString",
                    "params": {"query": "正常查询"},
                    "description": "正常步骤"
                },
                {
                    "action": "invalid_action",
                    "params": {},
                    "description": "无效步骤"
                },
                {
                    "action": "aiString",
                    "params": {"query": "不会执行的步骤"},
                    "description": "跳过的步骤"
                }
            ],
            "stop_on_failure": True
        }
        
        result = await executor.execute_test_case(
            test_case=test_case,
            execution_id="test_case_002"
        )
        
        assert result['success'] is False
        assert result['total_steps'] == 2  # 第三步被跳过
        assert result['successful_steps'] == 1
        assert result['failed_steps'] == 1
        
        # 验证步骤结果
        steps = result['steps']
        assert len(steps) == 2
        assert steps[0]['success'] is True
        assert steps[1]['success'] is False


class TestAcceptanceCriteria:
    """验收标准验证测试"""
    
    @pytest.mark.asyncio
    async def test_ac1_ai_query_capture(self):
        """AC-1: aiQuery方法返回值捕获"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("ac1_test")
        
        step_config = {
            "action": "aiQuery",
            "params": {
                "query": "提取商品价格和库存信息",
                "dataDemand": "name: string, price: number, stock: number, category: string"
            },
            "output_variable": "product_info",
            "description": "提取商品详细信息"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="ac1_exec",
            variable_manager=variable_manager
        )
        
        # 验证执行成功
        assert result.success is True
        assert result.variable_assigned == "product_info"
        assert isinstance(result.return_value, dict)
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("product_info")
        assert stored_value is not None
        assert isinstance(stored_value, dict)
    
    @pytest.mark.asyncio
    async def test_ac2_ai_string_capture(self):
        """AC-2: aiString方法返回值捕获"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("ac2_test")
        
        step_config = {
            "action": "aiString",
            "params": {
                "query": "页面标题文本"
            },
            "output_variable": "page_title",
            "description": "获取页面标题"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="ac2_exec",
            variable_manager=variable_manager
        )
        
        # 验证执行成功
        assert result.success is True
        assert result.variable_assigned == "page_title"
        assert isinstance(result.return_value, str)
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("page_title")
        assert stored_value is not None
        assert isinstance(stored_value, str)
    
    @pytest.mark.asyncio
    async def test_ac3_ai_number_capture(self):
        """AC-3: aiNumber方法返回值捕获"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("ac3_test")
        
        step_config = {
            "action": "aiNumber",
            "params": {
                "query": "商品价格数值"
            },
            "output_variable": "current_price",
            "description": "获取当前商品价格"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="ac3_exec",
            variable_manager=variable_manager
        )
        
        # 验证执行成功
        assert result.success is True
        assert result.variable_assigned == "current_price"
        assert isinstance(result.return_value, (int, float))
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("current_price")
        assert stored_value is not None
        assert isinstance(stored_value, (int, float))
    
    @pytest.mark.asyncio
    async def test_ac4_ai_boolean_capture(self):
        """AC-4: aiBoolean方法返回值捕获"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("ac4_test")
        
        step_config = {
            "action": "aiBoolean",
            "params": {
                "query": "商品是否有库存"
            },
            "output_variable": "has_stock",
            "description": "检查商品库存状态"
        }
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="ac4_exec",
            variable_manager=variable_manager
        )
        
        # 验证执行成功
        assert result.success is True
        assert result.variable_assigned == "has_stock"
        assert isinstance(result.return_value, bool)
        
        # 验证变量存储
        stored_value = variable_manager.get_variable("has_stock")
        assert stored_value is not None
        assert isinstance(stored_value, bool)
    
    @pytest.mark.asyncio
    async def test_ac5_error_handling(self):
        """AC-5: API执行失败时的错误处理"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("ac5_test")
        
        # Mock数据提取器返回失败
        failed_result = ExtractionResult(
            success=False,
            data=None,
            data_type="error",
            method="aiString",
            error="API调用失败: 网络超时"
        )
        
        with patch.object(executor.data_extractor, 'extract_data', return_value=failed_result):
            step_config = {
                "action": "aiString",
                "params": {
                    "query": "测试查询"
                },
                "output_variable": "test_var",
                "description": "测试错误处理"
            }
            
            result = await executor.execute_step(
                step_config=step_config,
                step_index=0,
                execution_id="ac5_exec",
                variable_manager=variable_manager
            )
            
            # 验证错误处理
            assert result.success is False
            assert "API调用失败" in result.error_message
            assert result.variable_assigned is None
            
            # 验证变量未被存储
            stored_value = variable_manager.get_variable("test_var")
            assert stored_value is None
    
    @pytest.mark.asyncio
    async def test_ac6_data_type_validation(self):
        """AC-6: 数据类型自动检测和验证"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("ac6_test")
        
        # 测试各种数据类型的自动检测
        test_cases = [
            ("aiQuery", {"query": "test", "dataDemand": "name: string"}, dict),
            ("aiString", {"query": "test"}, str),
            ("aiNumber", {"query": "test"}, (int, float)),
            ("aiBoolean", {"query": "test"}, bool)
        ]
        
        for action, params, expected_type in test_cases:
            step_config = {
                "action": action,
                "params": params,
                "output_variable": f"test_{action.lower()}",
                "description": f"测试{action}数据类型验证"
            }
            
            result = await executor.execute_step(
                step_config=step_config,
                step_index=0,
                execution_id="ac6_exec",
                variable_manager=variable_manager
            )
            
            assert result.success is True, f"{action} 执行失败"
            assert isinstance(result.return_value, expected_type), f"{action} 返回类型不正确"
            assert result.variable_assigned == f"test_{action.lower()}"


@pytest.mark.asyncio
class TestPerformance:
    """性能测试"""
    
    async def test_concurrent_execution(self):
        """测试并发执行性能"""
        executor = AIStepExecutor(mock_mode=True)
        
        # 创建10个并发步骤
        tasks = []
        for i in range(10):
            variable_manager = VariableManager(f"perf_test_{i}")
            step_config = {
                "action": "aiString",
                "params": {"query": f"并发测试查询 {i}"},
                "output_variable": f"result_{i}",
                "description": f"并发测试步骤 {i}"
            }
            
            task = executor.execute_step(
                step_config=step_config,
                step_index=i,
                execution_id=f"perf_exec_{i}",
                variable_manager=variable_manager
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证所有步骤都成功
        for result in results:
            assert result.success is True
        
        # 性能要求：10个并发步骤应在5秒内完成
        total_time = end_time - start_time
        assert total_time < 5.0, f"并发性能测试失败，耗时 {total_time:.2f}秒"
        
        print(f"并发性能测试: 10个步骤耗时 {total_time:.3f}秒，平均 {total_time/10*1000:.1f}ms/步骤")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])