"""
变量建议服务单元测试
测试VariableSuggestionService的核心功能
"""

import pytest
from unittest.mock import Mock, patch
from web_gui.services.variable_suggestion_service import VariableSuggestionService
from web_gui.services.variable_manager import VariableManager

class TestVariableSuggestionService:
    """变量建议服务测试类"""
    
    @pytest.fixture
    def mock_variable_manager(self):
        """创建模拟变量管理器"""
        manager = Mock(spec=VariableManager)
        manager.execution_id = 'test-exec-001'
        return manager
    
    @pytest.fixture
    def service(self, mock_variable_manager):
        """创建服务实例"""
        return VariableSuggestionService(mock_variable_manager)
    
    @pytest.fixture
    def sample_variables(self):
        """示例变量数据"""
        return [
            {
                'variable_name': 'user_name',
                'variable_value': '"张三"',
                'data_type': 'string',
                'source_step_index': 1,
                'source_api_method': 'aiInput',
                'created_at': '2025-01-30T10:00:00Z'
            },
            {
                'variable_name': 'product_info',
                'variable_value': '{"name": "iPhone 15", "price": 999, "specs": {"color": "blue", "storage": "128GB"}}',
                'data_type': 'object',
                'source_step_index': 2,
                'source_api_method': 'aiQuery',
                'created_at': '2025-01-30T10:05:00Z'
            },
            {
                'variable_name': 'item_count',
                'variable_value': '5',
                'data_type': 'number',
                'source_step_index': 3,
                'source_api_method': 'aiNumber',
                'created_at': '2025-01-30T10:10:00Z'
            }
        ]
    
    def test_get_variable_suggestions_basic(self, service, mock_variable_manager, sample_variables):
        """测试基础变量建议功能"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.get_variable_suggestions()
        
        assert result['execution_id'] == 'test-exec-001'
        assert result['total_count'] == 3
        assert len(result['variables']) == 3
        
        # 验证变量数据格式
        var = result['variables'][0]
        assert var['name'] == 'user_name'
        assert var['data_type'] == 'string'
        assert var['source_step_index'] == 1
        assert var['preview_value'] == '"张三"'
    
    def test_get_variable_suggestions_with_step_filter(self, service, mock_variable_manager, sample_variables):
        """测试步骤索引过滤"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        # 只返回步骤2之前的变量
        result = service.get_variable_suggestions(step_index=2)
        
        assert result['current_step_index'] == 2
        assert result['total_count'] == 1  # 只有步骤1的user_name
        assert result['variables'][0]['name'] == 'user_name'
    
    def test_get_variable_suggestions_with_properties(self, service, mock_variable_manager, sample_variables):
        """测试包含属性信息"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.get_variable_suggestions(include_properties=True)
        
        # 找到对象类型的变量
        product_var = next(v for v in result['variables'] if v['name'] == 'product_info')
        assert 'properties' in product_var
        assert len(product_var['properties']) == 3
        
        # 验证属性结构
        name_prop = next(p for p in product_var['properties'] if p['name'] == 'name')
        assert name_prop['type'] == 'string'
        assert name_prop['value'] == 'iPhone 15'
        assert name_prop['path'] == 'product_info.name'
    
    def test_get_variable_properties_object(self, service, mock_variable_manager):
        """测试获取对象变量属性"""
        # 模拟变量元数据
        mock_variable_manager.get_variable_metadata.return_value = {
            'name': 'product_info',
            'value': {
                'name': 'iPhone 15',
                'price': 999,
                'specs': {
                    'color': 'blue',
                    'storage': '128GB'
                }
            },
            'data_type': 'object'
        }
        
        result = service.get_variable_properties('product_info', max_depth=2)
        
        assert result['variable_name'] == 'product_info'
        assert result['data_type'] == 'object'
        assert len(result['properties']) == 3
        
        # 验证嵌套属性
        specs_prop = next(p for p in result['properties'] if p['name'] == 'specs')
        assert specs_prop['type'] == 'object'
        assert 'properties' in specs_prop
        assert len(specs_prop['properties']) == 2
    
    def test_get_variable_properties_non_object(self, service, mock_variable_manager):
        """测试获取非对象变量属性"""
        mock_variable_manager.get_variable_metadata.return_value = {
            'name': 'user_name',
            'value': '张三',
            'data_type': 'string'
        }
        
        result = service.get_variable_properties('user_name')
        
        assert result['variable_name'] == 'user_name'
        assert result['data_type'] == 'string'
        assert result['properties'] == []
    
    def test_get_variable_properties_not_found(self, service, mock_variable_manager):
        """测试获取不存在的变量属性"""
        mock_variable_manager.get_variable_metadata.return_value = None
        
        result = service.get_variable_properties('nonexistent')
        
        assert result is None
    
    def test_search_variables_exact_match(self, service, mock_variable_manager, sample_variables):
        """测试精确匹配搜索"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.search_variables('user_name')
        
        assert result['query'] == 'user_name'
        assert result['count'] >= 1  # 至少有一个匹配
        
        # 验证最佳匹配是 user_name
        best_match = result['matches'][0]
        assert best_match['name'] == 'user_name'
        assert best_match['match_score'] > 0.9  # 精确匹配应该有很高的分数
    
    def test_search_variables_prefix_match(self, service, mock_variable_manager, sample_variables):
        """测试前缀匹配搜索"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.search_variables('user')
        
        assert result['count'] == 1
        match = result['matches'][0]
        assert match['name'] == 'user_name'
        assert match['match_score'] > 0.7  # 前缀匹配应该有较高分数
        assert '<mark>user</mark>' in match['highlighted_name']
    
    def test_search_variables_substring_match(self, service, mock_variable_manager, sample_variables):
        """测试子字符串匹配搜索"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.search_variables('info')
        
        assert result['count'] >= 1  # 至少有一个匹配
        # 验证包含 product_info 在结果中
        info_matches = [m for m in result['matches'] if m['name'] == 'product_info']
        assert len(info_matches) == 1
        match = info_matches[0]
        assert '<mark>info</mark>' in match['highlighted_name']
    
    def test_search_variables_case_insensitive(self, service, mock_variable_manager, sample_variables):
        """测试大小写不敏感搜索"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.search_variables('USER')
        
        assert result['count'] == 1
        assert result['matches'][0]['name'] == 'user_name'
    
    def test_search_variables_empty_query(self, service, mock_variable_manager):
        """测试空查询搜索"""
        result = service.search_variables('')
        
        assert result['query'] == ''
        assert result['count'] == 0
        assert result['matches'] == []
    
    def test_validate_references_valid(self, service, mock_variable_manager):
        """测试有效引用验证"""
        # 模拟变量数据
        mock_variable_manager.get_variable.return_value = {
            'name': 'iPhone 15',
            'price': 999
        }
        mock_variable_manager.list_variables.return_value = [
            {'variable_name': 'product_info'}
        ]
        
        references = ['${product_info.name}', '${product_info.price}']
        results = service.validate_references(references)
        
        assert len(results) == 2
        
        # 验证第一个引用
        result1 = results[0]
        assert result1['reference'] == '${product_info.name}'
        assert result1['is_valid'] is True
        assert result1['resolved_value'] == 'iPhone 15'
        assert result1['data_type'] == 'str'
        
        # 验证第二个引用
        result2 = results[1]
        assert result2['reference'] == '${product_info.price}'
        assert result2['is_valid'] is True
        assert result2['resolved_value'] == 999
        assert result2['data_type'] == 'int'
    
    def test_validate_references_invalid_format(self, service, mock_variable_manager):
        """测试无效格式引用验证"""
        references = ['invalid_format', 'product_info.name']
        results = service.validate_references(references)
        
        assert len(results) == 2
        
        for result in results:
            assert result['is_valid'] is False
            assert '无效的变量引用格式' in result['error']
            assert 'suggestion' in result
    
    def test_validate_references_undefined_variable(self, service, mock_variable_manager):
        """测试未定义变量引用验证"""
        mock_variable_manager.get_variable.return_value = None
        mock_variable_manager.list_variables.return_value = [
            {'variable_name': 'user_name'},
            {'variable_name': 'product_info'}
        ]
        
        references = ['${undefined_var}']
        results = service.validate_references(references)
        
        assert len(results) == 1
        result = results[0]
        assert result['is_valid'] is False
        assert "变量 'undefined_var' 未定义" in result['error']
        assert 'user_name' in result['suggestion']
    
    def test_validate_references_invalid_property(self, service, mock_variable_manager):
        """测试无效属性引用验证"""
        mock_variable_manager.get_variable.return_value = {
            'name': 'iPhone 15',
            'price': 999
        }
        mock_variable_manager.list_variables.return_value = [
            {'variable_name': 'product_info'}
        ]
        
        references = ['${product_info.invalid_prop}']
        results = service.validate_references(references)
        
        assert len(results) == 1
        result = results[0]
        assert result['is_valid'] is False
        assert "属性 'invalid_prop' 在对象中不存在" in result['error']
        assert 'name' in result['suggestion'] and 'price' in result['suggestion']
    
    def test_get_variables_status(self, service, mock_variable_manager, sample_variables):
        """测试获取变量状态"""
        mock_variable_manager.list_variables.return_value = sample_variables
        
        result = service.get_variables_status()
        
        assert result['variables_count'] == 3
        assert len(result['variables']) == 3
        
        # 验证变量状态格式
        var_status = result['variables'][0]
        assert var_status['name'] == 'user_name'
        assert var_status['status'] == 'available'
        assert 'last_updated' in var_status
        assert 'usage_count' in var_status
    
    def test_format_preview_value_string(self, service):
        """测试字符串预览格式化"""
        preview = service._format_preview_value('Hello World', 'string')
        assert preview == '"Hello World"'
        
        # 测试长字符串截断
        long_string = 'A' * 200
        preview = service._format_preview_value(long_string, 'string')
        assert preview.endswith('..."')
        assert len(preview) <= 103  # 100 + 3个引号和省略号
    
    def test_format_preview_value_object(self, service):
        """测试对象预览格式化"""
        obj = {'name': 'iPhone', 'price': 999, 'specs': {}}
        preview = service._format_preview_value(obj, 'object')
        
        assert preview.startswith('{')
        assert preview.endswith('}')
        assert '"name": ...' in preview
        assert '"price": ...' in preview
    
    def test_format_preview_value_array(self, service):
        """测试数组预览格式化"""
        arr = [1, 2, 3, 4, 5]
        preview = service._format_preview_value(arr, 'array')
        assert preview == '[5 items]'
    
    def test_format_preview_value_number(self, service):
        """测试数字预览格式化"""
        assert service._format_preview_value(42, 'number') == '42'
        assert service._format_preview_value(3.14, 'number') == '3.14'
    
    def test_format_preview_value_boolean(self, service):
        """测试布尔值预览格式化"""
        assert service._format_preview_value(True, 'boolean') == 'true'
        assert service._format_preview_value(False, 'boolean') == 'false'
    
    def test_format_preview_value_null(self, service):
        """测试null值预览格式化"""
        assert service._format_preview_value(None, 'string') == 'null'
    
    def test_highlight_match(self, service):
        """测试文本高亮功能"""
        # 基本高亮
        result = service._highlight_match('product_info', 'info')
        assert result == 'product_<mark>info</mark>'
        
        # 大小写不敏感
        result = service._highlight_match('product_info', 'INFO')
        assert result == 'product_<mark>info</mark>'
        
        # 多次匹配
        result = service._highlight_match('info_product_info', 'info')
        assert result == '<mark>info</mark>_product_<mark>info</mark>'
        
        # 空查询
        result = service._highlight_match('product_info', '')
        assert result == 'product_info'
    
    def test_parse_variable_reference(self, service):
        """测试变量引用解析"""
        # 基本变量引用
        result = service._parse_variable_reference('${variable_name}')
        assert result == 'variable_name'
        
        # 嵌套属性引用
        result = service._parse_variable_reference('${object.property.subprop}')
        assert result == 'object.property.subprop'
        
        # 无效格式
        result = service._parse_variable_reference('invalid_format')
        assert result is None
        
        result = service._parse_variable_reference('${unclosed')
        assert result is None
    
    def test_resolve_property_path(self, service):
        """测试属性路径解析"""
        obj = {
            'name': 'iPhone',
            'price': 999,
            'specs': {
                'color': 'blue',
                'storage': '128GB'
            },
            'tags': ['electronics', 'mobile']
        }
        
        # 简单属性
        result = service._resolve_property_path(obj, 'product.name')
        assert result == 'iPhone'
        
        # 嵌套属性
        result = service._resolve_property_path(obj, 'product.specs.color')
        assert result == 'blue'
        
        # 数组索引
        result = service._resolve_property_path(obj, 'product.tags.0')
        assert result == 'electronics'
        
        # 负数索引
        result = service._resolve_property_path(obj, 'product.tags.-1')
        assert result == 'mobile'
        
        # 无效属性
        with pytest.raises(ValueError, match="属性 'invalid' 在对象中不存在"):
            service._resolve_property_path(obj, 'product.invalid')
        
        # 无效数组索引
        with pytest.raises(ValueError, match="数组索引超出范围"):
            service._resolve_property_path(obj, 'product.tags.10')
        
        # 无效数组索引格式
        with pytest.raises(ValueError, match="无效的数组索引"):
            service._resolve_property_path(obj, 'product.tags.abc')
    
    def test_detect_data_type(self, service):
        """测试数据类型检测"""
        assert service._detect_data_type(None) == 'null'
        assert service._detect_data_type(True) == 'boolean'
        assert service._detect_data_type(False) == 'boolean'
        assert service._detect_data_type(42) == 'number'
        assert service._detect_data_type(3.14) == 'number'
        assert service._detect_data_type('hello') == 'string'
        assert service._detect_data_type([1, 2, 3]) == 'array'
        assert service._detect_data_type({'key': 'value'}) == 'object'
        assert service._detect_data_type(object()) == 'string'  # 默认类型
    
    def test_get_property_suggestions(self, service):
        """测试属性建议"""
        obj = {'name': 'iPhone', 'price': 999}
        
        # 对象属性建议
        suggestion = service._get_property_suggestions(obj, 'product.invalid')
        assert 'name' in suggestion and 'price' in suggestion
        
        # 数组建议
        arr = [1, 2, 3]
        suggestion = service._get_property_suggestions(arr, 'items.10')
        assert '数组长度' in suggestion and '0-2' in suggestion
    
    @patch('web_gui.services.variable_suggestion_service.VariableManagerFactory.get_manager')
    def test_get_service_factory_method(self, mock_factory):
        """测试服务工厂方法"""
        mock_manager = Mock(spec=VariableManager)
        mock_manager.execution_id = 'test-exec-001'
        mock_factory.return_value = mock_manager
        
        service = VariableSuggestionService.get_service('test-exec-001')
        
        assert isinstance(service, VariableSuggestionService)
        assert service.execution_id == 'test-exec-001'
        mock_factory.assert_called_once_with('test-exec-001')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])