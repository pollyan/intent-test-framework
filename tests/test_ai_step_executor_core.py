#!/usr/bin/env python3
"""
AI步骤执行器核心功能测试（不依赖数据库）
专注于验证STORY-005的核心功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.services.ai_step_executor import AIStepExecutor, StepExecutionResult
from tests.test_variable_manager import TestVariableManager as VariableManager
from midscene_framework import (
    MidSceneDataExtractor,
    DataExtractionMethod,
    ExtractionRequest,
    ExtractionResult
)


class TestAIStepExecutorCore:
    """AI步骤执行器核心功能测试"""
    
    def test_init_mock_mode(self):
        """测试Mock模式初始化"""
        executor = AIStepExecutor(mock_mode=True)
        assert executor.mock_mode is True
        assert executor.midscene_client is None
        assert executor.data_extractor is not None
        assert len(executor.ai_extraction_methods) == 6
    
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
        
        # 验证传统方法
        assert 'navigate' in actions
        assert 'set_variable' in actions
        assert 'get_variable' in actions
    
    @pytest.mark.asyncio
    async def test_execute_ai_query_step_without_db(self):
        """测试aiQuery步骤执行（不记录数据库）"""
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True  # 跳过数据库记录
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
    
    @pytest.mark.asyncio
    async def test_execute_ai_string_step_without_db(self):
        """测试aiString步骤执行（不记录数据库）"""
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
        
        executor._skip_db_recording = True  # 跳过数据库记录
        
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
    
    @pytest.mark.asyncio
    async def test_execute_ai_number_step_without_db(self):
        """测试aiNumber步骤执行（不记录数据库）"""
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
        
        executor._skip_db_recording = True  # 跳过数据库记录
        
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
    
    @pytest.mark.asyncio
    async def test_execute_ai_boolean_step_without_db(self):
        """测试aiBoolean步骤执行（不记录数据库）"""
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
        
        executor._skip_db_recording = True  # 跳过数据库记录
        
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
    
    @pytest.mark.asyncio
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
        
        executor._skip_db_recording = True  # 跳过数据库记录
        
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
    
    @pytest.mark.asyncio
    async def test_execute_get_variable_step(self):
        """测试get_variable步骤执行"""
        executor = AIStepExecutor(mock_mode=True)
        variable_manager = VariableManager("test_execution")
        
        # 先设置一个变量
        variable_manager.store_variable("existing_var", "existing_value", source_step_index=0)
        
        step_config = {
            "action": "get_variable",
            "params": {
                "name": "existing_var"
            },
            "description": "获取已存在的变量"
        }
        
        executor._skip_db_recording = True  # 跳过数据库记录
        
        result = await executor.execute_step(
            step_config=step_config,
            step_index=0,
            execution_id="test_exec_007",
            variable_manager=variable_manager
        )
        
        assert result.success is True
        assert result.action == "get_variable"
        assert result.return_value == "existing_value"
    
    @pytest.mark.asyncio
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
            with patch.object(executor, '_record_step_execution', return_value=None):
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


class TestAcceptanceCriteriaCore:
    """验收标准验证测试（核心功能）"""
    
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
        
        with patch.object(executor, '_record_step_execution', return_value=None):
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
        
        with patch.object(executor, '_record_step_execution', return_value=None):
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
        
        with patch.object(executor, '_record_step_execution', return_value=None):
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
        
        with patch.object(executor, '_record_step_execution', return_value=None):
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
            with patch.object(executor, '_record_step_execution', return_value=None):
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
            
            with patch.object(executor, '_record_step_execution', return_value=None):
                result = await executor.execute_step(
                    step_config=step_config,
                    step_index=0,
                execution_id="ac6_exec",
                    variable_manager=variable_manager
                )
                
                assert result.success is True, f"{action} 执行失败"
                assert isinstance(result.return_value, expected_type), f"{action} 返回类型不正确"
                assert result.variable_assigned == f"test_{action.lower()}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])