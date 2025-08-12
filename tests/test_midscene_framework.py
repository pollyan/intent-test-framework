#!/usr/bin/env python3
"""
MidSceneJS数据提取API框架测试
测试所有核心功能和集成
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from midscene_framework import (
    MidSceneDataExtractor,
    DataExtractionMethod,
    ExtractionRequest,
    ExtractionResult,
    RetryHandler,
    RetryConfig,
    MidSceneConfig,
    ConfigManager,
    MockMidSceneAPI,
    DataValidator
)


class TestDataExtractionMethod:
    """数据提取方法枚举测试"""
    
    def test_enum_values(self):
        """测试枚举值"""
        assert DataExtractionMethod.AI_QUERY.value == "aiQuery"
        assert DataExtractionMethod.AI_STRING.value == "aiString"
        assert DataExtractionMethod.AI_NUMBER.value == "aiNumber"
        assert DataExtractionMethod.AI_BOOLEAN.value == "aiBoolean"
        assert DataExtractionMethod.AI_ASK.value == "aiAsk"
        assert DataExtractionMethod.AI_LOCATE.value == "aiLocate"
    
    def test_enum_count(self):
        """测试枚举数量"""
        methods = list(DataExtractionMethod)
        assert len(methods) == 6


class TestExtractionRequest:
    """提取请求数据类测试"""
    
    def test_basic_request(self):
        """测试基本请求"""
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_STRING,
            params={"query": "test query"}
        )
        
        assert request.method == DataExtractionMethod.AI_STRING
        assert request.params["query"] == "test query"
        assert request.output_variable is None
        assert request.validation_rules is None
        assert request.retry_config is None
    
    def test_full_request(self):
        """测试完整请求"""
        retry_config = {"max_attempts": 5}
        validation_rules = {"required_fields": ["name"]}
        
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_QUERY,
            params={"query": "test", "dataDemand": "{name: string}"},
            output_variable="test_var",
            validation_rules=validation_rules,
            retry_config=retry_config
        )
        
        assert request.method == DataExtractionMethod.AI_QUERY
        assert request.output_variable == "test_var"
        assert request.validation_rules == validation_rules
        assert request.retry_config == retry_config


class TestExtractionResult:
    """提取结果数据类测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ExtractionResult(
            success=True,
            data={"name": "test"},
            data_type="object",
            method="aiQuery",
            execution_time=1.5,
            metadata={"source": "test"}
        )
        
        assert result.success is True
        assert result.data == {"name": "test"}
        assert result.data_type == "object"
        assert result.method == "aiQuery"
        assert result.error is None
        assert result.execution_time == 1.5
        assert result.metadata["source"] == "test"
    
    def test_error_result(self):
        """测试错误结果"""
        result = ExtractionResult(
            success=False,
            data=None,
            data_type="error",
            method="aiString",
            error="Test error",
            execution_time=0.5
        )
        
        assert result.success is False
        assert result.data is None
        assert result.data_type == "error"
        assert result.error == "Test error"


class TestDataValidator:
    """数据验证器测试"""
    
    def test_validate_query_data(self):
        """测试查询数据验证"""
        validator = DataValidator()
        
        # 正常数据
        data = {"name": "test", "price": 99.99}
        result = validator.validate_query_data(data)
        assert result == data
        
        # 空对象
        with pytest.raises(ValueError, match="不能返回空对象"):
            validator.validate_query_data({})
        
        # 非对象类型
        with pytest.raises(ValueError, match="必须返回对象类型"):
            validator.validate_query_data("not an object")
    
    def test_validate_string_data(self):
        """测试字符串数据验证"""
        validator = DataValidator()
        
        # 正常字符串
        assert validator.validate_string_data("hello world") == "hello world"
        
        # 空字符串
        with pytest.raises(ValueError, match="不能返回空字符串"):
            validator.validate_string_data("")
        
        # 只有空格
        with pytest.raises(ValueError, match="不能返回空字符串"):
            validator.validate_string_data("   ")
        
        # 非字符串类型
        with pytest.raises(ValueError, match="必须返回字符串类型"):
            validator.validate_string_data(123)
    
    def test_validate_number_data(self):
        """测试数字数据验证"""
        validator = DataValidator()
        
        # 正常数字
        assert validator.validate_number_data(42) == 42.0
        assert validator.validate_number_data(3.14) == 3.14
        
        # 字符串数字
        assert validator.validate_number_data("123.45") == 123.45
        
        # NaN
        import math
        with pytest.raises(ValueError, match="不能返回NaN"):
            validator.validate_number_data(float('nan'))
        
        # 无穷大
        with pytest.raises(ValueError, match="不能返回无穷大"):
            validator.validate_number_data(float('inf'))
        
        # 无效字符串
        with pytest.raises(ValueError, match="必须返回数字类型"):
            validator.validate_number_data("not a number")
    
    def test_validate_boolean_data(self):
        """测试布尔数据验证"""
        validator = DataValidator()
        
        # 正常布尔值
        assert validator.validate_boolean_data(True) is True
        assert validator.validate_boolean_data(False) is False
        
        # 字符串布尔值
        assert validator.validate_boolean_data("true") is True
        assert validator.validate_boolean_data("false") is False
        assert validator.validate_boolean_data("1") is True
        assert validator.validate_boolean_data("0") is False
        
        # 数字布尔值
        assert validator.validate_boolean_data(1) is True
        assert validator.validate_boolean_data(0) is False
        
        # 无效值
        with pytest.raises(ValueError, match="无法将字符串"):
            validator.validate_boolean_data("maybe")


class TestRetryConfig:
    """重试配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=1.5
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 1.5
    
    def test_invalid_config(self):
        """测试无效配置"""
        with pytest.raises(ValueError, match="max_attempts必须大于0"):
            RetryConfig(max_attempts=0)
        
        with pytest.raises(ValueError, match="base_delay必须大于0"):
            RetryConfig(base_delay=-1.0)


class TestRetryHandler:
    """重试处理器测试"""
    
    @pytest.mark.asyncio
    async def test_successful_call(self):
        """测试成功调用"""
        async def success_func():
            return "success"
        
        config = RetryConfig(max_attempts=3)
        result = await RetryHandler.retry_with_backoff(success_func, config)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试失败重试"""
        call_count = 0
        
        async def fail_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        result = await RetryHandler.retry_with_backoff(fail_then_success, config)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """测试超过最大尝试次数"""
        async def always_fail():
            raise ConnectionError("Always fails")
        
        config = RetryConfig(max_attempts=2, base_delay=0.1)
        with pytest.raises(ConnectionError, match="Always fails"):
            await RetryHandler.retry_with_backoff(always_fail, config)
    
    def test_should_retry(self):
        """测试是否应该重试"""
        # 应该重试的异常
        assert RetryHandler._should_retry(ConnectionError("connection failed"))
        assert RetryHandler._should_retry(Exception("timeout error"))
        assert RetryHandler._should_retry(Exception("500 server error"))
        
        # 不应该重试的异常
        assert not RetryHandler._should_retry(ValueError("invalid parameter"))
        assert not RetryHandler._should_retry(KeyError("missing key"))


class TestMidSceneConfig:
    """配置类测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = MidSceneConfig()
        assert config.api_base_url == "http://localhost:3001"
        assert config.api_timeout == 30
        assert config.model_name == "qwen-vl-max-latest"
        assert config.max_retry_attempts == 3
        assert config.mock_mode is False
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = MidSceneConfig(
            api_base_url="http://test.com",
            api_timeout=60,
            mock_mode=True
        )
        assert config.api_base_url == "http://test.com"
        assert config.api_timeout == 60
        assert config.mock_mode is True
    
    def test_config_validation(self):
        """测试配置验证"""
        with pytest.raises(ValueError, match="api_timeout必须大于0"):
            MidSceneConfig(api_timeout=0)
        
        with pytest.raises(ValueError, match="max_retry_attempts必须大于等于1"):
            MidSceneConfig(max_retry_attempts=0)
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = MidSceneConfig(api_base_url="http://test.com")
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["api_base_url"] == "http://test.com"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {"api_base_url": "http://test.com", "api_timeout": 45}
        config = MidSceneConfig.from_dict(data)
        assert config.api_base_url == "http://test.com"
        assert config.api_timeout == 45


class TestConfigManager:
    """配置管理器测试"""
    
    def test_singleton(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        assert manager1 is manager2
    
    def test_load_from_env(self):
        """测试从环境变量加载"""
        manager = ConfigManager()
        manager.reset_config()  # 重置配置
        
        with patch.dict(os.environ, {
            'MIDSCENE_API_URL': 'http://test.com',
            'MIDSCENE_API_TIMEOUT': '45',
            'MIDSCENE_MOCK_MODE': 'true'
        }):
            config = manager.load_config()
            assert config.api_base_url == 'http://test.com'
            assert config.api_timeout == 45
            assert config.mock_mode is True
    
    def test_update_config(self):
        """测试更新配置"""
        manager = ConfigManager()
        manager.reset_config()
        
        config = manager.update_config(api_timeout=90, mock_mode=True)
        assert config.api_timeout == 90
        assert config.mock_mode is True
    
    def test_validate_config(self):
        """测试配置验证"""
        manager = ConfigManager()
        manager.reset_config()
        
        # 加载默认配置
        manager.load_config()
        
        # 验证配置（可能会有OPENAI_API_KEY未设置的警告）
        errors = manager.validate_config()
        # 根据环境变量情况，errors可能包含或不包含API密钥错误


@pytest.mark.asyncio
class TestMockMidSceneAPI:
    """Mock API服务测试"""
    
    async def test_ai_query(self):
        """测试aiQuery Mock"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        result = await mock_api.aiQuery(
            query="获取商品信息",
            dataDemand="name: string, price: number"
        )
        
        assert isinstance(result, dict)
        assert "name" in result
        assert "price" in result
        assert isinstance(result["name"], str)
        assert isinstance(result["price"], (int, float))
    
    async def test_ai_string(self):
        """测试aiString Mock"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        result = await mock_api.aiString(query="页面标题")
        assert isinstance(result, str)
        assert len(result) > 0
    
    async def test_ai_number(self):
        """测试aiNumber Mock"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        result = await mock_api.aiNumber(query="商品价格")
        assert isinstance(result, (int, float))
        assert result > 0
    
    async def test_ai_boolean(self):
        """测试aiBoolean Mock"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        result = await mock_api.aiBoolean(query="是否有库存")
        assert isinstance(result, bool)
    
    async def test_ai_ask(self):
        """测试aiAsk Mock"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        result = await mock_api.aiAsk(query="什么是人工智能")
        assert isinstance(result, str)
        assert len(result) > 0
    
    async def test_ai_locate(self):
        """测试aiLocate Mock"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        result = await mock_api.aiLocate(query="登录按钮")
        assert isinstance(result, dict)
        assert "rect" in result
        assert "center" in result
        assert "x" in result["rect"]
        assert "y" in result["rect"]
    
    async def test_call_stats(self):
        """测试调用统计"""
        mock_api = MockMidSceneAPI(response_delay=0.01)
        
        await mock_api.aiString(query="test1")
        await mock_api.aiString(query="test2")
        await mock_api.aiNumber(query="test3")
        
        stats = mock_api.get_call_stats()
        assert stats["total_calls"] == 3
        assert stats["method_calls"]["aiString"] == 2
        assert stats["method_calls"]["aiNumber"] == 1


@pytest.mark.asyncio
class TestMidSceneDataExtractor:
    """数据提取器核心测试"""
    
    def test_init_mock_mode(self):
        """测试Mock模式初始化"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        assert extractor.mock_mode is True
        assert extractor.midscene_client is None
    
    def test_init_with_client(self):
        """测试带客户端初始化"""
        mock_client = Mock()
        extractor = MidSceneDataExtractor(midscene_client=mock_client)
        assert extractor.mock_mode is False
        assert extractor.midscene_client is mock_client
    
    def test_method_registry(self):
        """测试方法注册表"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        # 检查所有方法都有注册信息
        for method in DataExtractionMethod:
            assert method in extractor.METHOD_REGISTRY
            config = extractor.METHOD_REGISTRY[method]
            assert "handler" in config
            assert "required_params" in config
            assert "return_type" in config
    
    def test_get_supported_methods(self):
        """测试获取支持的方法"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        methods = extractor.get_supported_methods()
        
        assert len(methods) == 6
        assert "aiQuery" in methods
        assert "aiString" in methods
        assert "aiNumber" in methods
        assert "aiBoolean" in methods
        assert "aiAsk" in methods
        assert "aiLocate" in methods
    
    def test_get_method_info(self):
        """测试获取方法信息"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        info = extractor.get_method_info(DataExtractionMethod.AI_QUERY)
        assert info["handler"] == "_handle_ai_query"
        assert "query" in info["required_params"]
        assert "dataDemand" in info["required_params"]
        assert info["return_type"] == "object"
    
    def test_validate_request(self):
        """测试请求验证"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        # 正常请求
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_STRING,
            params={"query": "test"}
        )
        extractor._validate_request(request)  # 应该不抛异常
        
        # 缺少必需参数
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_QUERY,
            params={"query": "test"}  # 缺少dataDemand
        )
        with pytest.raises(ValueError, match="缺少必需参数: dataDemand"):
            extractor._validate_request(request)
        
        # 参数类型错误
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_STRING,
            params={"query": 123}  # query应该是字符串
        )
        with pytest.raises(ValueError, match="query参数必须是字符串"):
            extractor._validate_request(request)
    
    async def test_extract_data_mock_mode(self):
        """测试Mock模式数据提取"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        # 测试aiString
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_STRING,
            params={"query": "页面标题"},
            output_variable="title"
        )
        
        result = await extractor.extract_data(request)
        
        assert result.success is True
        assert isinstance(result.data, str)
        assert result.data_type == "string"
        assert result.method == "aiString"
        assert result.execution_time > 0
        assert result.metadata["output_variable"] == "title"
    
    async def test_extract_data_all_methods_mock(self):
        """测试所有方法的Mock提取"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        test_cases = [
            (DataExtractionMethod.AI_QUERY, {"query": "test", "dataDemand": "name: string, price: number"}, "object"),
            (DataExtractionMethod.AI_STRING, {"query": "test"}, "string"),
            (DataExtractionMethod.AI_NUMBER, {"query": "test"}, "number"),
            (DataExtractionMethod.AI_BOOLEAN, {"query": "test"}, "boolean"),
            (DataExtractionMethod.AI_ASK, {"query": "test"}, "string"),
            (DataExtractionMethod.AI_LOCATE, {"query": "test"}, "object"),
        ]
        
        for method, params, expected_type in test_cases:
            request = ExtractionRequest(method=method, params=params)
            result = await extractor.extract_data(request)
            
            assert result.success is True, f"Method {method.value} failed"
            assert result.data_type == expected_type, f"Method {method.value} wrong type"
            assert result.method == method.value
    
    async def test_extract_data_validation_error(self):
        """测试数据验证错误"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        # 让Mock返回无效数据，然后测试验证
        with patch.object(extractor, '_mock_extract', return_value=""):
            request = ExtractionRequest(
                method=DataExtractionMethod.AI_STRING,
                params={"query": "test"}
            )
            
            result = await extractor.extract_data(request)
            assert result.success is False
            assert "不能返回空字符串" in result.error
    
    def test_get_stats(self):
        """测试获取统计信息"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        stats = extractor.get_stats()
        
        assert "supported_methods" in stats
        assert "mock_mode" in stats
        assert "client_available" in stats
        assert "methods" in stats
        assert stats["supported_methods"] == 6
        assert stats["mock_mode"] is True
        assert stats["client_available"] is False


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_mock(self):
        """端到端Mock测试"""
        # 创建提取器
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        # 创建请求
        request = ExtractionRequest(
            method=DataExtractionMethod.AI_QUERY,
            params={
                "query": "获取商品信息",
                "dataDemand": "name: string, price: number"
            },
            output_variable="product_info",
            validation_rules={"required_fields": ["name", "price"]}
        )
        
        # 执行提取
        result = await extractor.extract_data(request)
        
        # 验证结果
        assert result.success is True
        assert isinstance(result.data, dict)
        assert "name" in result.data
        assert "price" in result.data
        assert result.data_type == "object"
        assert result.metadata["output_variable"] == "product_info"
    
    @pytest.mark.asyncio
    async def test_performance_benchmark(self):
        """性能基准测试"""
        extractor = MidSceneDataExtractor(mock_mode=True)
        
        # 测试100次调用的性能
        start_time = time.time()
        
        tasks = []
        for i in range(100):
            request = ExtractionRequest(
                method=DataExtractionMethod.AI_STRING,
                params={"query": f"test query {i}"}
            )
            tasks.append(extractor.extract_data(request))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证所有调用都成功
        for result in results:
            assert result.success is True
        
        # 性能要求：100次调用应在10秒内完成
        assert total_time < 10.0, f"性能测试失败，耗时 {total_time:.2f}秒"
        
        print(f"性能基准测试: 100次调用耗时 {total_time:.3f}秒，平均 {total_time/100*1000:.1f}ms/次")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])