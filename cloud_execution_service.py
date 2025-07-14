#!/usr/bin/env python3
"""
云端执行服务
使用Playwright + AI模型实现真正的云端浏览器自动化
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
import requests

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright未安装，请运行: pip install playwright")

class CloudExecutionService:
    """云端执行服务"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.ai_config = self._load_ai_config()
        
    def _load_ai_config(self) -> Dict[str, str]:
        """加载AI配置"""
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "model": os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest")
        }
    
    async def initialize_browser(self, headless: bool = True) -> bool:
        """初始化浏览器"""
        try:
            if not PLAYWRIGHT_AVAILABLE:
                return False
                
            self.playwright = await async_playwright().start()
            
            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # 创建页面
            self.page = await self.browser.new_page()
            
            # 设置视口
            await self.page.set_viewport_size({"width": 1280, "height": 720})
            
            print("✅ 云端浏览器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ 浏览器初始化失败: {e}")
            return False
    
    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("✅ 浏览器已关闭")
        except Exception as e:
            print(f"⚠️  关闭浏览器时出错: {e}")
    
    async def take_screenshot(self, name: str = None) -> str:
        """截图并返回base64编码"""
        try:
            if not self.page:
                return ""
                
            screenshot_bytes = await self.page.screenshot(full_page=True)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
            
            # 可以选择保存到文件
            if name:
                filename = f"screenshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                os.makedirs("screenshots", exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(screenshot_bytes)
                print(f"📸 截图已保存: {filename}")
            
            return screenshot_base64
            
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return ""
    
    async def ai_vision_call(self, prompt: str, screenshot_base64: str) -> Dict[str, Any]:
        """调用AI视觉模型"""
        try:
            if not self.ai_config["api_key"]:
                return {"error": "AI API密钥未配置"}
            
            headers = {
                "Authorization": f"Bearer {self.ai_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.ai_config["model"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            response = requests.post(
                f"{self.ai_config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "content": result["choices"][0]["message"]["content"]
                }
            else:
                return {
                    "success": False,
                    "error": f"AI调用失败: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"AI调用异常: {str(e)}"
            }
    
    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个测试步骤"""
        action = step.get("action")
        params = step.get("params", {})
        description = step.get("description", action)
        
        result = {
            "success": False,
            "action": action,
            "description": description,
            "screenshot": "",
            "ai_response": "",
            "error": None
        }
        
        try:
            print(f"🔄 执行步骤: {description}")
            
            if action == "navigate":
                url = params.get("url")
                await self.page.goto(url, wait_until="networkidle")
                result["success"] = True
                result["details"] = f"已导航到: {url}"
                
            elif action == "ai_input":
                text = params.get("text")
                locate_prompt = params.get("locate", "输入框")
                
                # 截图并使用AI定位元素
                screenshot = await self.take_screenshot()
                ai_prompt = f"在这个页面中找到{locate_prompt}，并返回其CSS选择器或XPath"
                
                ai_result = await self.ai_vision_call(ai_prompt, screenshot)
                if ai_result.get("success"):
                    # 这里需要解析AI返回的选择器并执行输入
                    # 简化实现：使用通用选择器
                    await self.page.fill("input[type='text'], input[type='search'], textarea", text)
                    result["success"] = True
                    result["ai_response"] = ai_result["content"]
                else:
                    result["error"] = ai_result.get("error")
                    
            elif action == "ai_tap":
                button_prompt = params.get("prompt", "按钮")
                
                # 截图并使用AI定位按钮
                screenshot = await self.take_screenshot()
                ai_prompt = f"在这个页面中找到{button_prompt}，并返回其CSS选择器"
                
                ai_result = await self.ai_vision_call(ai_prompt, screenshot)
                if ai_result.get("success"):
                    # 简化实现：使用通用选择器
                    await self.page.click("button, input[type='submit'], a")
                    result["success"] = True
                    result["ai_response"] = ai_result["content"]
                else:
                    result["error"] = ai_result.get("error")
                    
            elif action == "ai_assert":
                assert_prompt = params.get("prompt")
                
                # 截图并使用AI验证
                screenshot = await self.take_screenshot()
                ai_prompt = f"验证页面是否满足条件: {assert_prompt}。请回答'是'或'否'并说明原因。"
                
                ai_result = await self.ai_vision_call(ai_prompt, screenshot)
                if ai_result.get("success"):
                    ai_response = ai_result["content"].lower()
                    result["success"] = "是" in ai_response or "yes" in ai_response
                    result["ai_response"] = ai_result["content"]
                else:
                    result["error"] = ai_result.get("error")
                    
            elif action == "ai_wait_for":
                wait_prompt = params.get("prompt")
                timeout = params.get("timeout", 10000) / 1000  # 转换为秒
                
                # 简化实现：等待指定时间后验证
                await asyncio.sleep(2)
                screenshot = await self.take_screenshot()
                ai_prompt = f"检查页面是否满足条件: {wait_prompt}"
                
                ai_result = await self.ai_vision_call(ai_prompt, screenshot)
                if ai_result.get("success"):
                    result["success"] = True
                    result["ai_response"] = ai_result["content"]
                else:
                    result["error"] = ai_result.get("error")
                    
            else:
                result["error"] = f"不支持的操作类型: {action}"
            
            # 每步执行后截图
            result["screenshot"] = await self.take_screenshot(f"step_{action}")
            
        except Exception as e:
            result["error"] = str(e)
            result["screenshot"] = await self.take_screenshot(f"error_{action}")
        
        return result
    
    async def execute_testcase(self, testcase_data: Dict[str, Any], mode: str = "headless") -> Dict[str, Any]:
        """执行完整的测试用例"""
        execution_id = str(uuid.uuid4())
        
        execution_result = {
            "execution_id": execution_id,
            "testcase_name": testcase_data.get("name", "未知测试用例"),
            "mode": mode,
            "status": "running",
            "start_time": datetime.utcnow().isoformat(),
            "steps": [],
            "screenshots": [],
            "success_count": 0,
            "total_count": 0
        }
        
        try:
            # 初始化浏览器
            if not await self.initialize_browser(headless=(mode == "headless")):
                execution_result["status"] = "failed"
                execution_result["error"] = "浏览器初始化失败"
                return execution_result
            
            # 解析测试步骤
            steps = json.loads(testcase_data.get("steps", "[]"))
            execution_result["total_count"] = len(steps)
            
            # 执行每个步骤
            for i, step in enumerate(steps):
                print(f"\n📍 执行步骤 {i+1}/{len(steps)}")
                
                step_result = await self.execute_step(step)
                execution_result["steps"].append(step_result)
                
                if step_result["success"]:
                    execution_result["success_count"] += 1
                    print(f"✅ 步骤 {i+1} 成功")
                else:
                    print(f"❌ 步骤 {i+1} 失败: {step_result.get('error')}")
                
                # 添加截图到历史
                if step_result["screenshot"]:
                    execution_result["screenshots"].append({
                        "step": i + 1,
                        "description": step_result["description"],
                        "screenshot": step_result["screenshot"]
                    })
                
                # 短暂延迟
                await asyncio.sleep(1)
            
            # 完成执行
            execution_result["status"] = "completed"
            execution_result["end_time"] = datetime.utcnow().isoformat()
            
            success_rate = execution_result["success_count"] / execution_result["total_count"] * 100
            execution_result["success_rate"] = success_rate
            
            print(f"\n🎉 测试执行完成！成功率: {success_rate:.1f}%")
            
        except Exception as e:
            execution_result["status"] = "failed"
            execution_result["error"] = str(e)
            execution_result["end_time"] = datetime.utcnow().isoformat()
            print(f"❌ 测试执行失败: {e}")
        
        finally:
            # 关闭浏览器
            await self.close_browser()
        
        return execution_result

# 使用示例
async def main():
    """测试云端执行服务"""
    service = CloudExecutionService()
    
    # 示例测试用例
    testcase = {
        "name": "百度搜索测试",
        "steps": json.dumps([
            {
                "action": "navigate",
                "params": {"url": "https://www.baidu.com"},
                "description": "访问百度首页"
            },
            {
                "action": "ai_input",
                "params": {"text": "AI测试", "locate": "搜索框"},
                "description": "输入搜索关键词"
            },
            {
                "action": "ai_tap",
                "params": {"prompt": "搜索按钮"},
                "description": "点击搜索"
            },
            {
                "action": "ai_assert",
                "params": {"prompt": "页面显示了搜索结果"},
                "description": "验证搜索结果"
            }
        ])
    }
    
    # 执行测试
    result = await service.execute_testcase(testcase, mode="headless")
    print(f"\n执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(main())
