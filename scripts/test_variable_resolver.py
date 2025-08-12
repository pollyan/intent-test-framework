#!/usr/bin/env python3
"""
VariableResolverService功能测试脚本
验证变量解析服务的各项功能
"""

import sys
import os
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.app_enhanced import create_app
from web_gui.models import db
from web_gui.services.variable_resolver import VariableResolverService

def test_variable_resolver():
    """测试变量解析服务"""
    
    # 创建临时SQLite数据库用于测试
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{temp_db.name}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        try:
            # 创建所有表
            db.create_all()
            print("✓ 数据库表创建成功")
            
            # 创建变量解析服务实例
            execution_id = 'test-execution-001'
            resolver = VariableResolverService(execution_id)
            print("✓ VariableResolverService实例创建成功")
            
            # 测试1: 存储变量
            print("\n=== 测试1: 存储变量 ===")
            
            # 存储简单字符串变量
            success = resolver.store_step_output(
                variable_name='user_name',
                value='张三',
                step_index=1,
                api_method='aiString'
            )
            assert success, "存储字符串变量失败"
            print("✓ 存储字符串变量成功")
            
            # 存储复杂对象变量
            product_info = {
                'name': 'iPhone 15',
                'price': 999.99,
                'specs': {
                    'color': '黑色',
                    'storage': '128GB'
                },
                'tags': ['智能手机', '苹果', '5G']
            }
            success = resolver.store_step_output(
                variable_name='product_info',
                value=product_info,
                step_index=2,
                api_method='aiQuery',
                api_params={'query': '获取商品信息', 'dataDemand': '{}'}
            )
            assert success, "存储对象变量失败"
            print("✓ 存储对象变量成功")
            
            # 存储数组变量
            items_list = [
                {'name': '商品1', 'price': 100},
                {'name': '商品2', 'price': 200},
                {'name': '商品3', 'price': 300}
            ]
            success = resolver.store_step_output(
                variable_name='items_list',
                value=items_list,
                step_index=3,
                api_method='aiQuery'
            )
            assert success, "存储数组变量失败"
            print("✓ 存储数组变量成功")
            
            # 测试2: 简单变量引用解析
            print("\n=== 测试2: 简单变量引用解析 ===")
            
            test_params = {
                'text': '用户名是：${user_name}',
                'url': 'https://example.com/user/${user_name}'
            }
            
            resolved_params = resolver.resolve_step_parameters(test_params, 4)
            
            assert resolved_params['text'] == '用户名是：张三', f"文本解析错误: {resolved_params['text']}"
            assert resolved_params['url'] == 'https://example.com/user/张三', f"URL解析错误: {resolved_params['url']}"
            print("✓ 简单变量引用解析成功")
            
            # 测试3: 复杂对象属性访问
            print("\n=== 测试3: 复杂对象属性访问 ===")
            
            complex_params = {
                'product_name': '商品名称：${product_info.name}',
                'product_price': '价格：${product_info.price}',
                'product_color': '颜色：${product_info.specs.color}',
                'storage_info': '存储：${product_info.specs.storage}'
            }
            
            resolved_complex = resolver.resolve_step_parameters(complex_params, 5)
            
            assert resolved_complex['product_name'] == '商品名称：iPhone 15'
            assert resolved_complex['product_price'] == '价格：999.99'
            assert resolved_complex['product_color'] == '颜色：黑色'
            assert resolved_complex['storage_info'] == '存储：128GB'
            print("✓ 复杂对象属性访问成功")
            
            # 测试4: 数组元素访问
            print("\n=== 测试4: 数组元素访问 ===")
            
            array_params = {
                'first_item': '第一个商品：${items_list[0].name}',
                'first_price': '第一个价格：${items_list[0].price}',
                'second_item': '第二个商品：${items_list[1].name}',
                'tag_info': '第一个标签：${product_info.tags[0]}'
            }
            
            resolved_array = resolver.resolve_step_parameters(array_params, 6)
            
            assert resolved_array['first_item'] == '第一个商品：商品1'
            assert resolved_array['first_price'] == '第一个价格：100'
            assert resolved_array['second_item'] == '第二个商品：商品2'
            assert resolved_array['tag_info'] == '第一个标签：智能手机'
            print("✓ 数组元素访问成功")
            
            # 测试5: 混合参数类型
            print("\n=== 测试5: 混合参数类型 ===")
            
            mixed_params = {
                'text_param': '用户${user_name}购买了${product_info.name}',
                'object_param': {
                    'user': '${user_name}',
                    'product': '${product_info.name}',
                    'price': '${product_info.price}'
                },
                'array_param': [
                    '${user_name}',
                    '${product_info.name}',
                    '${items_list[0].name}'
                ]
            }
            
            resolved_mixed = resolver.resolve_step_parameters(mixed_params, 7)
            
            assert resolved_mixed['text_param'] == '用户张三购买了iPhone 15'
            assert resolved_mixed['object_param']['user'] == '张三'
            assert resolved_mixed['object_param']['product'] == 'iPhone 15'
            assert resolved_mixed['array_param'][0] == '张三'
            assert resolved_mixed['array_param'][1] == 'iPhone 15'
            assert resolved_mixed['array_param'][2] == '商品1'
            print("✓ 混合参数类型解析成功")
            
            # 测试6: 错误处理
            print("\n=== 测试6: 错误处理 ===")
            
            error_params = {
                'invalid_var': '${nonexistent_variable}',
                'invalid_prop': '${product_info.nonexistent_property}',
                'invalid_index': '${items_list[99].name}',
                'valid_param': '${user_name}'
            }
            
            resolved_error = resolver.resolve_step_parameters(error_params, 8)
            
            # 无效引用应该保持原样
            assert '${nonexistent_variable}' in resolved_error['invalid_var']
            assert '${product_info.nonexistent_property}' in resolved_error['invalid_prop']
            assert '${items_list[99].name}' in resolved_error['invalid_index']
            # 有效引用应该被解析
            assert resolved_error['valid_param'] == '张三'
            print("✓ 错误处理测试成功")
            
            # 测试7: 获取可用变量
            print("\n=== 测试7: 获取可用变量 ===")
            
            available_vars = resolver.get_available_variables()
            
            assert len(available_vars) == 3, f"变量数量不正确: {len(available_vars)}"
            
            var_names = [var['name'] for var in available_vars]
            assert 'user_name' in var_names
            assert 'product_info' in var_names
            assert 'items_list' in var_names
            
            # 检查产品信息变量的属性
            product_var = next(var for var in available_vars if var['name'] == 'product_info')
            print(f"Product properties: {product_var['properties']}")  # 调试输出
            assert 'name' in product_var['properties']
            assert 'price' in product_var['properties']
            assert 'specs.color' in product_var['properties']
            # 数组索引格式调整
            has_tags_array = any('tags.[0]' in prop or 'tags[0]' in prop for prop in product_var['properties'])
            assert has_tags_array, f"未找到tags数组属性，实际属性: {product_var['properties']}"
            
            print("✓ 获取可用变量成功")
            
            # 测试8: 变量引用验证
            print("\n=== 测试8: 变量引用验证 ===")
            
            test_text = '用户${user_name}购买${product_info.name}，价格${product_info.price}，无效引用${invalid_var}'
            validation_results = resolver.validate_variable_references(test_text, 9)
            
            assert len(validation_results) == 4, f"验证结果数量不正确: {len(validation_results)}"
            
            # 检查有效引用
            valid_count = sum(1 for result in validation_results if result['is_valid'])
            invalid_count = sum(1 for result in validation_results if not result['is_valid'])
            
            assert valid_count == 3, f"有效引用数量不正确: {valid_count}"
            assert invalid_count == 1, f"无效引用数量不正确: {invalid_count}"
            
            print("✓ 变量引用验证成功")
            
            print("\n🎉 所有测试通过！VariableResolverService功能正常")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_db.name)
            except:
                pass

if __name__ == '__main__':
    success = test_variable_resolver()
    sys.exit(0 if success else 1)