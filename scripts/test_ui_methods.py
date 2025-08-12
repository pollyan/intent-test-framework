#!/usr/bin/env python3
"""
测试UI中方法的新格式和默认参数
"""

import sys
import os
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.app_enhanced import create_app, execute_single_step
from web_gui.models import db

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
    
    def ai_wait_for(self, prompt, timeout=10000):
        print(f"[模拟] 等待: {prompt} (超时: {timeout}ms)")
    
    def take_screenshot(self, title):
        return f"mock_screenshot_{title}.png"

def test_ui_methods():
    """测试UI中新格式的方法"""
    
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
            
            execution_id = 'test-ui-methods-001'
            ai = MockMidSceneAI()
            
            print("\n=== 测试UI方法格式 ===")
            
            # 测试1: aiQuery的schema格式
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
                'output_variable': 'product_data',
                'description': '提取商品信息'
            }
            
            result1 = execute_single_step(ai, step1, 'headless', execution_id, 0)
            assert result1['success'], f"aiQuery测试失败: {result1.get('error_message')}"
            print(f"✓ aiQuery (schema格式): {result1['output_data']}")
            
            # 测试2: aiTap方法
            step2 = {
                'action': 'aiTap',
                'params': {
                    'locate': '购买${product_data.商品名称}按钮',
                    'options': {'deepThink': False, 'cacheable': True}
                },
                'description': '点击购买按钮'
            }
            
            result2 = execute_single_step(ai, step2, 'headless', execution_id, 1)
            assert result2['success'], f"aiTap测试失败: {result2.get('error_message')}"
            print("✓ aiTap: 变量引用点击成功")
            
            # 测试3: aiInput方法
            step3 = {
                'action': 'aiInput',
                'params': {
                    'text': '${product_data.商品名称}',
                    'locate': '搜索输入框',
                    'options': {'deepThink': False, 'cacheable': True}
                },
                'description': '输入商品名称搜索'
            }
            
            result3 = execute_single_step(ai, step3, 'headless', execution_id, 2)
            assert result3['success'], f"aiInput测试失败: {result3.get('error_message')}"
            print("✓ aiInput: 变量引用输入成功")
            
            # 测试4: aiString方法
            step4 = {
                'action': 'aiString',
                'params': {
                    'query': '获取页面标题或主要文本内容'
                },
                'output_variable': 'page_title',
                'description': '获取页面标题'
            }
            
            result4 = execute_single_step(ai, step4, 'headless', execution_id, 3)
            assert result4['success'], f"aiString测试失败: {result4.get('error_message')}"
            print(f"✓ aiString: {result4['output_data']}")
            
            # 测试5: aiAsk方法
            step5 = {
                'action': 'aiAsk',
                'params': {
                    'query': '这个商品${product_data.商品名称}适合什么用户群体？请分析其特点和适用场景'
                },
                'output_variable': 'analysis',
                'description': 'AI分析用户群体'
            }
            
            result5 = execute_single_step(ai, step5, 'headless', execution_id, 4)
            assert result5['success'], f"aiAsk测试失败: {result5.get('error_message')}"
            print(f"✓ aiAsk: {result5['output_data'][:50]}...")
            
            # 测试6: aiAssert方法
            step6 = {
                'action': 'aiAssert',
                'params': {
                    'condition': '页面显示了商品${product_data.商品名称}的详细信息'
                },
                'description': '验证商品详情显示'
            }
            
            result6 = execute_single_step(ai, step6, 'headless', execution_id, 5)
            assert result6['success'], f"aiAssert测试失败: {result6.get('error_message')}"
            print("✓ aiAssert: 断言验证成功")
            
            # 测试7: aiWaitFor方法
            step7 = {
                'action': 'aiWaitFor',
                'params': {
                    'prompt': '页面加载完成，显示${product_data.商品名称}的信息',
                    'options': {'timeoutMs': 15000, 'checkIntervalMs': 3000}
                },
                'description': '等待页面加载完成'
            }
            
            result7 = execute_single_step(ai, step7, 'headless', execution_id, 6)
            assert result7['success'], f"aiWaitFor测试失败: {result7.get('error_message')}"
            print("✓ aiWaitFor: 等待条件成功")
            
            # 测试8: evaluateJavaScript方法
            step8 = {
                'action': 'evaluateJavaScript',
                'params': {
                    'script': 'return {url: window.location.href, title: document.title, productName: "' + '${product_data.商品名称}' + '", timestamp: Date.now()};'
                },
                'output_variable': 'js_result',
                'description': '执行JavaScript获取页面信息'
            }
            
            result8 = execute_single_step(ai, step8, 'headless', execution_id, 7)
            assert result8['success'], f"evaluateJavaScript测试失败: {result8.get('error_message')}"
            print(f"✓ evaluateJavaScript: {result8['output_data']}")
            
            print("\n🎉 所有UI方法格式测试成功！")
            print("✓ aiQuery支持schema格式")
            print("✓ aiTap/aiInput/aiAssert支持新方法名")
            print("✓ 所有方法都支持变量引用")
            print("✓ 输出变量功能正常")
            print("✓ 默认参数格式更加直观")
            
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
    success = test_ui_methods()
    sys.exit(0 if success else 1)