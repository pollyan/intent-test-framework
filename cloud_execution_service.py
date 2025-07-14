#!/usr/bin/env python3
"""
轻量级云端执行服务
基于MidSceneJS实现意图驱动的测试执行，针对免费云服务器优化
集成资源管理和智能回退机制
"""

import asyncio
import json
import os
import uuid
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
import requests
from pathlib import Path
import tempfile
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightweightCloudExecutor:
    """轻量级云端执行器 - 基于MidSceneJS的意图驱动测试"""
    
    def __init__(self):
        self.midscene_server = None
        self.server_port = 3001
        self.ai_config = self._load_ai_config()
        self.execution_timeout = 300  # 5分钟超时
        self.max_memory_mb = 400  # 最大内存限制 400MB
        self.optimization_config = None
        
    def _load_ai_config(self) -> Dict[str, str]:
        """加载AI配置"""
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "model": os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest"),
            "timeout": "30000"  # 30秒超时
        }
    
    def set_optimization_config(self, config: Dict[str, Any]):
        """设置优化配置"""
        self.optimization_config = config
    
    async def _start_lightweight_midscene_server(self) -> bool:
        """启动轻量级MidSceneJS服务器"""
        try:
            logger.info("🚀 启动轻量级MidSceneJS服务器...")
            
            # 创建临时的轻量级服务器脚本
            server_script = await self._create_lightweight_server_script()
            
            # 启动Node.js服务器
            self.midscene_server = subprocess.Popen(
                ['node', server_script],
                env={
                    **os.environ,
                    'OPENAI_API_KEY': self.ai_config['api_key'],
                    'OPENAI_BASE_URL': self.ai_config['base_url'],
                    'MIDSCENE_MODEL_NAME': self.ai_config['model'],
                    'NODE_OPTIONS': '--max-old-space-size=256'  # 限制Node.js内存
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            await asyncio.sleep(3)
            
            # 验证服务器状态
            if await self._verify_server_health():
                logger.info("✅ MidSceneJS服务器启动成功")
                return True
            else:
                logger.error("❌ MidSceneJS服务器启动失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 启动MidSceneJS服务器异常: {e}")
            return False
    
    async def _create_lightweight_server_script(self) -> str:
        """创建轻量级服务器脚本"""
        # 获取优化配置
        browser_args = []
        viewport = {"width": 1024, "height": 768}
        
        if self.optimization_config:
            browser_args = self.optimization_config.get("browser_args", [])
            viewport = self.optimization_config.get("viewport", viewport)
        
        # 默认优化参数
        if not browser_args:
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--single-process'
            ]
        
        script_content = f"""
// 轻量级MidSceneJS服务器 - 针对云端资源优化
const express = require('express');
const {{ PlaywrightAgent }} = require('@midscene/web');
const {{ chromium }} = require('playwright');

const app = express();
const port = {self.server_port};

app.use(express.json({{ limit: '10mb' }}));

let browser = null;
let page = null;
let agent = null;

// 启动轻量级浏览器
async function initLightweightBrowser() {{
    if (!browser) {{
        browser = await chromium.launch({{
            headless: true,
            args: {json.dumps(browser_args)}
        }});
    }}
    
    if (!page) {{
        const context = await browser.newContext({{
            viewport: {json.dumps(viewport)},
            deviceScaleFactor: 1
        }});
        page = await context.newPage();
        
        // 初始化MidSceneJS AI Agent
        const config = {{
            modelName: process.env.MIDSCENE_MODEL_NAME,
            apiKey: process.env.OPENAI_API_KEY,
            baseUrl: process.env.OPENAI_BASE_URL
        }};
        
        agent = new PlaywrightAgent(page, {{ aiModel: config }});
    }}
    
    return {{ page, agent }};
}}

// 健康检查
app.get('/health', (req, res) => {{
    res.json({{ status: 'healthy', timestamp: new Date().toISOString() }});
}});

// 意图驱动执行接口
app.post('/ai-action', async (req, res) => {{
    try {{
        const {{ action, params }} = req.body;
        await initLightweightBrowser();
        
        let result = {{ success: false, data: null, error: null }};
        
        switch (action) {{
            case 'navigate':
                await page.goto(params.url, {{ waitUntil: 'networkidle' }});
                result = {{ success: true, data: 'Navigation completed' }};
                break;
                
            case 'ai_action':
                const actionResult = await agent.action(params.prompt);
                result = {{ success: true, data: actionResult }};
                break;
                
            case 'ai_query':
                const queryResult = await agent.query(params.prompt);
                result = {{ success: true, data: queryResult }};
                break;
                
            case 'ai_assert':
                const assertResult = await agent.assert(params.prompt);
                result = {{ success: true, data: assertResult }};
                break;
                
            case 'screenshot':
                const screenshot = await page.screenshot({{ 
                    type: 'png',
                    quality: {self.optimization_config.get('screenshot_quality', 80) if self.optimization_config else 80}
                }});
                result = {{ success: true, data: screenshot.toString('base64') }};
                break;
                
            default:
                result = {{ success: false, error: `Unsupported action: ${{action}}` }};
        }}
        
        res.json(result);
    }} catch (error) {{
        console.error('AI Action Error:', error);
        res.status(500).json({{ success: false, error: error.message }});
    }}
}});

// 批量执行接口 - 减少HTTP请求次数
app.post('/ai-batch', async (req, res) => {{
    try {{
        const {{ actions }} = req.body;
        await initLightweightBrowser();
        
        const results = [];
        
        for (const actionData of actions) {{
            const {{ action, params }} = actionData;
            
            try {{
                let result = {{ success: false, data: null, error: null }};
                
                switch (action) {{
                    case 'navigate':
                        await page.goto(params.url, {{ waitUntil: 'networkidle' }});
                        result = {{ success: true, data: 'Navigation completed' }};
                        break;
                        
                    case 'ai_action':
                        const actionResult = await agent.action(params.prompt);
                        result = {{ success: true, data: actionResult }};
                        break;
                        
                    case 'ai_query':
                        const queryResult = await agent.query(params.prompt);
                        result = {{ success: true, data: queryResult }};
                        break;
                        
                    case 'ai_assert':
                        const assertResult = await agent.assert(params.prompt);
                        result = {{ success: true, data: assertResult }};
                        break;
                        
                    default:
                        result = {{ success: false, error: `Unsupported action: ${{action}}` }};
                }}
                
                results.push(result);
                
            }} catch (error) {{
                results.push({{ success: false, error: error.message }});
            }}
        }}
        
        res.json({{ success: true, results }});
    }} catch (error) {{
        console.error('AI Batch Error:', error);
        res.status(500).json({{ success: false, error: error.message }});
    }}
}});

// 清理资源
app.post('/cleanup', async (req, res) => {{
    try {{
        if (page) await page.close();
        if (browser) await browser.close();
        page = null;
        browser = null;
        agent = null;
        res.json({{ success: true }});
    }} catch (error) {{
        res.status(500).json({{ success: false, error: error.message }});
    }}
}});

// 启动服务器
app.listen(port, () => {{
    console.log(`🚀 轻量级MidSceneJS服务器启动 - 端口: ${{port}}`);
}});

// 进程退出时清理
process.on('SIGINT', async () => {{
    if (browser) await browser.close();
    process.exit(0);
}});
"""
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False)
        temp_file.write(script_content)
        temp_file.close()
        
        return temp_file.name
    
    async def _verify_server_health(self) -> bool:
        """验证服务器健康状态"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:{self.server_port}/health') as response:
                    return response.status == 200
        except:
            return False
    
    async def _make_ai_request(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送AI请求到MidSceneJS服务器"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'http://localhost:{self.server_port}/ai-action',
                    json={'action': action, 'params': params},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return await response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _make_batch_request(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """发送批量AI请求到MidSceneJS服务器"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'http://localhost:{self.server_port}/ai-batch',
                    json={'actions': actions},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    return await response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def execute_intent_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行意图驱动的测试步骤"""
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
            logger.info(f"🔄 执行意图步骤: {description}")
            
            # 应用步骤延迟优化
            if self.optimization_config:
                delay = self.optimization_config.get("step_delay", 0.5)
                await asyncio.sleep(delay)
            
            # 基于MidSceneJS的意图驱动执行
            if action == "navigate":
                ai_result = await self._make_ai_request("navigate", {"url": params.get("url")})
                
            elif action == "ai_input":
                # 意图驱动输入：使用自然语言描述找到输入框并输入
                locate_prompt = params.get("locate", "输入框")
                text = params.get("text", "")
                ai_result = await self._make_ai_request("ai_action", {
                    "prompt": f"在{locate_prompt}中输入'{text}'"
                })
                
            elif action == "ai_tap":
                # 意图驱动点击：使用自然语言描述找到并点击元素
                element_desc = params.get("element", "按钮")
                ai_result = await self._make_ai_request("ai_action", {
                    "prompt": f"点击{element_desc}"
                })
                
            elif action == "ai_assert":
                # 意图驱动断言：使用自然语言验证页面状态
                assertion = params.get("assertion", "")
                ai_result = await self._make_ai_request("ai_assert", {
                    "prompt": assertion
                })
                
            elif action == "ai_query":
                # 意图驱动查询：使用自然语言查询页面信息
                query = params.get("query", "")
                ai_result = await self._make_ai_request("ai_query", {
                    "prompt": query
                })
                
            elif action == "ai_wait_for":
                # 意图驱动等待：等待特定条件满足
                condition = params.get("condition", "")
                ai_result = await self._make_ai_request("ai_query", {
                    "prompt": f"检查是否{condition}"
                })
                
            else:
                ai_result = {"success": False, "error": f"不支持的意图操作: {action}"}
            
            # 处理结果
            if ai_result.get("success"):
                result["success"] = True
                result["ai_response"] = str(ai_result.get("data", ""))
            else:
                result["error"] = ai_result.get("error", "未知错误")
            
            # 获取截图 - 根据优化配置决定是否截图
            should_screenshot = True
            if self.optimization_config:
                # 在高内存压力下减少截图
                should_screenshot = self.optimization_config.get("screenshot_quality", 80) > 0
            
            if should_screenshot:
                screenshot_result = await self._make_ai_request("screenshot", {})
                if screenshot_result.get("success"):
                    result["screenshot"] = screenshot_result.get("data", "")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ 步骤执行失败: {e}")
        
        return result
    
    async def execute_batch_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量执行测试步骤 - 减少HTTP请求次数"""
        try:
            # 构建批量请求
            batch_actions = []
            for step in steps:
                action = step.get("action")
                params = step.get("params", {})
                
                if action == "navigate":
                    batch_actions.append({
                        "action": "navigate",
                        "params": {"url": params.get("url")}
                    })
                elif action == "ai_input":
                    locate_prompt = params.get("locate", "输入框")
                    text = params.get("text", "")
                    batch_actions.append({
                        "action": "ai_action",
                        "params": {"prompt": f"在{locate_prompt}中输入'{text}'"}
                    })
                elif action == "ai_tap":
                    element_desc = params.get("element", "按钮")
                    batch_actions.append({
                        "action": "ai_action",
                        "params": {"prompt": f"点击{element_desc}"}
                    })
                elif action == "ai_assert":
                    assertion = params.get("assertion", "")
                    batch_actions.append({
                        "action": "ai_assert",
                        "params": {"prompt": assertion}
                    })
                elif action == "ai_query":
                    query = params.get("query", "")
                    batch_actions.append({
                        "action": "ai_query",
                        "params": {"prompt": query}
                    })
            
            # 发送批量请求
            batch_result = await self._make_batch_request(batch_actions)
            
            # 处理批量结果
            results = []
            if batch_result.get("success"):
                batch_results = batch_result.get("results", [])
                for i, (step, ai_result) in enumerate(zip(steps, batch_results)):
                    result = {
                        "success": ai_result.get("success", False),
                        "action": step.get("action"),
                        "description": step.get("description", step.get("action")),
                        "screenshot": "",
                        "ai_response": str(ai_result.get("data", "")),
                        "error": ai_result.get("error")
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"批量执行失败: {e}")
            # 回退到单步执行
            return [await self.execute_intent_step(step) for step in steps]
    
    async def execute_testcase(self, testcase_data: Dict[str, Any], mode: str = "headless") -> Dict[str, Any]:
        """执行完整的意图驱动测试用例"""
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
            # 启动轻量级MidSceneJS服务器
            if not await self._start_lightweight_midscene_server():
                execution_result["status"] = "failed"
                execution_result["error"] = "MidSceneJS服务器启动失败"
                return execution_result
            
            # 解析测试步骤
            steps = json.loads(testcase_data.get("steps", "[]"))
            execution_result["total_count"] = len(steps)
            
            # 决定是否使用批量执行
            use_batch = len(steps) > 3 and self.optimization_config and self.optimization_config.get("use_batch", True)
            
            if use_batch:
                # 批量执行
                logger.info(f"📦 批量执行 {len(steps)} 个步骤")
                step_results = await self.execute_batch_steps(steps)
                execution_result["steps"] = step_results
                
                # 计算成功数
                for step_result in step_results:
                    if step_result["success"]:
                        execution_result["success_count"] += 1
                
            else:
                # 逐步执行意图驱动的测试步骤
                for i, step in enumerate(steps):
                    logger.info(f"📍 执行步骤 {i+1}/{len(steps)}: {step.get('description', step.get('action'))}")
                    
                    step_result = await self.execute_intent_step(step)
                    execution_result["steps"].append(step_result)
                    
                    if step_result["success"]:
                        execution_result["success_count"] += 1
                        logger.info(f"✅ 步骤 {i+1} 成功")
                    else:
                        logger.warning(f"❌ 步骤 {i+1} 失败: {step_result.get('error')}")
                    
                    # 适当的步骤间延迟
                    delay = 0.5
                    if self.optimization_config:
                        delay = self.optimization_config.get("step_delay", 0.5)
                    await asyncio.sleep(delay)
            
            # 添加截图到历史
            for i, step_result in enumerate(execution_result["steps"]):
                if step_result["screenshot"]:
                    execution_result["screenshots"].append({
                        "step": i + 1,
                        "description": step_result["description"],
                        "screenshot": step_result["screenshot"]
                    })
            
            # 计算执行结果
            execution_result["status"] = "completed"
            execution_result["end_time"] = datetime.utcnow().isoformat()
            
            success_rate = (execution_result["success_count"] / execution_result["total_count"]) * 100
            execution_result["success_rate"] = success_rate
            
            logger.info(f"🎉 意图驱动测试执行完成！成功率: {success_rate:.1f}%")
            
        except Exception as e:
            execution_result["status"] = "failed"
            execution_result["error"] = str(e)
            execution_result["end_time"] = datetime.utcnow().isoformat()
            logger.error(f"❌ 测试执行失败: {e}")
        
        finally:
            # 清理资源
            await self._cleanup()
        
        return execution_result
    
    async def _cleanup(self):
        """清理资源"""
        try:
            # 通知服务器清理
            await self._make_ai_request("cleanup", {})
            
            # 终止服务器进程
            if self.midscene_server:
                self.midscene_server.terminate()
                try:
                    await asyncio.wait_for(self.midscene_server.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.midscene_server.kill()
                    await self.midscene_server.wait()
            
            logger.info("✅ 资源清理完成")
            
        except Exception as e:
            logger.error(f"⚠️ 资源清理时出错: {e}")

# 向后兼容的类名
CloudExecutionService = LightweightCloudExecutor

# 使用示例
async def main():
    """测试云端执行服务"""
    service = CloudExecutionService()
    
    # 示例优化配置
    optimization_config = {
        "browser_args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--single-process"
        ],
        "viewport": {"width": 1024, "height": 768},
        "screenshot_quality": 80,
        "step_delay": 0.5,
        "use_batch": True
    }
    service.set_optimization_config(optimization_config)
    
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
