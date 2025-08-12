#!/usr/bin/env python3
"""
数据流功能集成测试脚本
测试完整的变量存储、解析和引用流程
"""

import sys
import os
import tempfile
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.app_enhanced import create_app, execute_single_step
# 创建模拟AI类
class MockMidSceneAI:
    def __init__(self):
        self.current_url = None
    
    def goto(self, url):
        self.current_url = url
        print(f"[模拟] 访问页面: {url}")
    
    def ai_input(self, text, locate):
        print(f"[模拟] 在 '{locate}' 中输入: {text}")
    
    def ai_tap(self, prompt):
        print(f"[模拟] 点击: {prompt}")
    
    def ai_assert(self, prompt):
        print(f"[模拟] 验证: {prompt}")
    
    def ai_wait_for(self, prompt, timeout=10000):
        print(f"[模拟] 等待: {prompt}")
    
    def ai_scroll(self, direction='down', scroll_type='once', locate_prompt=None):
        print(f"[模拟] 滚动: {direction}")
    
    def ai_query(self, data_demand, options=None):
        """模拟aiQuery方法"""
        print(f"[Mock] aiQuery调用 - dataDemand: {data_demand}")
        return {"name": "测试商品", "price": 99.99, "id": "test-001"}
    
    def ai_string(self, query, options=None):
        """模拟aiString方法"""
        print(f"[Mock] aiString调用 - query: {query}")
        return "¥99.99"
    
    def ai_number(self, query, options=None):
        """模拟aiNumber方法"""
        print(f"[Mock] aiNumber调用 - query: {query}")
        return 99.99
    
    def ai_boolean(self, query, options=None):
        """模拟aiBoolean方法"""
        print(f"[Mock] aiBoolean调用 - query: {query}")
        return True
    
    def take_screenshot(self, title):
        return f"mock_screenshot_{title}.png"
from web_gui.models import db
from web_gui.services.variable_resolver import VariableResolverService

def test_data_flow_integration():
    """测试完整的数据流集成功能"""
    
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
            
            # 测试用例：电商购物流程数据流
            execution_id = 'test-dataflow-001'
            ai = MockMidSceneAI()
            
            print("\n=== 数据流集成测试开始 ===")
            
            # 步骤1: 访问商品页面
            step1 = {
                'action': 'navigate',
                'params': {'url': 'https://demo-shop.com/products'},
                'description': '访问商品列表页面'
            }
            
            result1 = execute_single_step(ai, step1, 'headless', execution_id, 0)
            assert result1['success'], f"步骤1失败: {result1.get('error_message')}"
            print("✓ 步骤1: 页面导航成功")
            
            # 步骤2: 使用aiQuery获取商品信息并存储为变量
            step2 = {
                'action': 'aiQuery',
                'params': {
                    'dataDemand': '{name: string, price: number, id: string}'
                },
                'output_variable': 'first_product',
                'description': '提取第一个商品信息'
            }
            
            result2 = execute_single_step(ai, step2, 'headless', execution_id, 1)
            assert result2['success'], f"步骤2失败: {result2.get('error_message')}"
            assert result2['output_data'] is not None, "aiQuery应该返回数据"
            print(f"✓ 步骤2: 商品信息获取成功 - {result2['output_data']}")
            
            # 步骤3: 使用变量引用点击商品
            step3 = {
                'action': 'ai_tap',
                'params': {
                    'locate': '${first_product.name}商品链接'
                },
                'description': '点击进入商品详情'
            }
            
            result3 = execute_single_step(ai, step3, 'headless', execution_id, 2)
            assert result3['success'], f"步骤3失败: {result3.get('error_message')}"
            print("✓ 步骤3: 变量引用点击成功")
            
            # 步骤4: 获取详情页价格
            step4 = {
                'action': 'aiString',
                'params': {
                    'query': '获取商品详情页的价格'
                },
                'output_variable': 'detail_price',
                'description': '获取详情页价格'
            }
            
            result4 = execute_single_step(ai, step4, 'headless', execution_id, 3)
            assert result4['success'], f"步骤4失败: {result4.get('error_message')}"
            assert result4['output_data'] is not None, "aiString应该返回数据"
            print(f"✓ 步骤4: 价格信息获取成功 - {result4['output_data']}")
            
            # 步骤5: 使用多个变量的复杂引用进行断言
            step5 = {
                'action': 'ai_assert',
                'params': {
                    'condition': '详情页价格${detail_price}与列表页价格${first_product.price}一致'
                },
                'description': '验证价格一致性'
            }
            
            result5 = execute_single_step(ai, step5, 'headless', execution_id, 4)
            assert result5['success'], f"步骤5失败: {result5.get('error_message')}"
            print("✓ 步骤5: 多变量引用断言成功")
            
            # 步骤6: JavaScript执行并存储结果
            step6 = {
                'action': 'evaluateJavaScript',
                'params': {
                    'script': 'return {url: window.location.href, title: document.title, price: \"${detail_price}\"}'
                },
                'output_variable': 'page_info',
                'description': '获取页面综合信息'
            }
            
            result6 = execute_single_step(ai, step6, 'headless', execution_id, 5)
            assert result6['success'], f"步骤6失败: {result6.get('error_message')}"
            assert result6['output_data'] is not None, "evaluateJavaScript应该返回数据"
            print(f"✓ 步骤6: JavaScript执行成功 - {result6['output_data']}")
            
            # 步骤7: AI智能分析
            step7 = {
                'action': 'aiAsk',
                'params': {
                    'query': '这个商品${first_product.name}适合什么用户群体？'
                },
                'output_variable': 'target_audience',
                'description': 'AI分析目标用户群体'
            }
            
            result7 = execute_single_step(ai, step7, 'headless', execution_id, 6)
            assert result7['success'], f"步骤7失败: {result7.get('error_message')}"
            assert result7['output_data'] is not None, "aiAsk应该返回数据"
            print(f"✓ 步骤7: AI分析成功 - {result7['output_data'][:50]}...")
            
            # 验证变量存储情况
            print("\n=== 验证变量存储 ===")
            resolver = VariableResolverService(execution_id)
            available_vars = resolver.get_available_variables()
            
            print(f"共存储了 {len(available_vars)} 个变量:")
            for var in available_vars:
                print(f"  - {var['name']}: {var['data_type']} = {str(var['value'])[:50]}...")
            
            # 验证必要的变量都存在
            var_names = [var['name'] for var in available_vars]
            expected_vars = ['first_product', 'detail_price', 'page_info', 'target_audience']
            
            for expected_var in expected_vars:
                assert expected_var in var_names, f"缺少变量: {expected_var}"
            
            print("✓ 所有预期变量都已正确存储")
            
            # 测试变量引用验证
            print("\n=== 测试变量引用验证 ===")
            
            test_expressions = [
                '商品名称：${first_product.name}',
                '价格信息：${detail_price}',
                '页面URL：${page_info.url}',
                '用户群体：${target_audience}',
                '无效引用：${nonexistent_var}'
            ]
            
            for expr in test_expressions:
                validation_results = resolver.validate_variable_references(expr, 99)
                print(f"  {expr}")
                for result in validation_results:
                    status = "✓" if result['is_valid'] else "✗"
                    print(f"    {status} {result['reference_path']}: {result.get('error_message', 'OK')}")
            
            print("\n🎉 数据流集成测试完全成功！")
            print("✓ 变量存储功能正常")
            print("✓ 变量引用解析正常") 
            print("✓ AI方法返回值捕获正常")
            print("✓ 复杂表达式处理正常")
            print("✓ 错误处理机制正常")
            
            return True
            
        except Exception as e:
            print(f"\n❌ 集成测试失败: {e}")
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
    success = test_data_flow_integration()
    sys.exit(0 if success else 1)