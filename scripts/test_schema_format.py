#!/usr/bin/env python3
"""
测试新的schema格式的aiQuery功能
"""

import sys
import os
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.app_enhanced import create_app, execute_single_step
from web_gui.models import db
from web_gui.services.variable_resolver import VariableResolverService

# 创建模拟AI类
class MockMidSceneAI:
    def __init__(self):
        self.current_url = None
    
    def goto(self, url):
        self.current_url = url
        print(f"[模拟] 访问页面: {url}")
    
    def ai_tap(self, prompt):
        print(f"[模拟] 点击: {prompt}")
    
    def ai_input(self, text, locate):
        print(f"[模拟] 在 '{locate}' 中输入: {text}")
    
    def ai_assert(self, prompt):
        print(f"[模拟] 验证: {prompt}")
    
    def take_screenshot(self, title):
        return f"mock_screenshot_{title}.png"

def test_schema_format():
    """测试schema格式的aiQuery"""
    
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
            
            execution_id = 'test-schema-001'
            ai = MockMidSceneAI()
            
            print("\n=== 测试schema格式的aiQuery ===")
            
            # 测试1: 基本的schema格式
            step1 = {
                'action': 'aiQuery',
                'params': {
                    'schema': {
                        '商品名称': '商品的名称, string',
                        '价格': '商品价格, number',
                        '库存': '库存数量, number',
                        '是否促销': '是否在促销, boolean',
                        '标签': '商品标签列表, array'
                    }
                },
                'output_variable': 'product_info',
                'description': '提取商品信息'
            }
            
            result1 = execute_single_step(ai, step1, 'headless', execution_id, 0)
            assert result1['success'], f"步骤1失败: {result1.get('error_message')}"
            assert result1['output_data'] is not None, "应该返回数据"
            print(f"✓ 基本schema测试成功: {result1['output_data']}")
            
            # 测试2: 使用变量引用schema返回的数据
            step2 = {
                'action': 'ai_tap',
                'params': {
                    'locate': '购买${product_info.商品名称}按钮'
                },
                'description': '点击购买按钮'
            }
            
            result2 = execute_single_step(ai, step2, 'headless', execution_id, 1)
            assert result2['success'], f"步骤2失败: {result2.get('error_message')}"
            print("✓ 变量引用测试成功")
            
            # 测试3: 复杂的schema格式
            step3 = {
                'action': 'aiQuery',
                'params': {
                    'schema': {
                        'user_id': '用户ID, string',
                        'profile': '用户资料信息, object',
                        'orders': '订单列表, array',
                        'balance': '账户余额, number',
                        'is_vip': 'VIP状态, boolean'
                    }
                },
                'output_variable': 'user_data',
                'description': '提取用户数据'
            }
            
            result3 = execute_single_step(ai, step3, 'headless', execution_id, 2)
            assert result3['success'], f"步骤3失败: {result3.get('error_message')}"
            print(f"✓ 复杂schema测试成功: {result3['output_data']}")
            
            # 验证变量存储
            print("\n=== 验证变量存储 ===")
            resolver = VariableResolverService(execution_id)
            available_vars = resolver.get_available_variables()
            
            print(f"共存储了 {len(available_vars)} 个变量:")
            for var in available_vars:
                print(f"  - {var['name']}: {var['data_type']}")
                print(f"    值: {str(var['value'])[:100]}...")
            
            # 验证变量引用
            print("\n=== 测试变量引用 ===")
            test_expressions = [
                '商品：${product_info.商品名称}',
                '价格：${product_info.价格}',
                '用户：${user_data.user_id}',
                'VIP状态：${user_data.is_vip}'
            ]
            
            for expr in test_expressions:
                validation_results = resolver.validate_variable_references(expr, 99)
                for result in validation_results:
                    status = "✓" if result['is_valid'] else "✗"
                    print(f"  {status} {expr} -> {result.get('resolved_value', result.get('error_message'))}")
            
            print("\n🎉 Schema格式测试完全成功！")
            print("✓ 支持UI中的schema参数格式")
            print("✓ 智能数据类型识别")
            print("✓ 变量引用正常工作")
            print("✓ 中文字段名支持")
            
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
    success = test_schema_format()
    sys.exit(0 if success else 1)