#!/usr/bin/env python3
"""
Chrome桥接服务
基于MidSceneJS Chrome扩展实现本地浏览器自动化
无需启动本地服务器，直接通过扩展与浏览器通信
"""

import asyncio
import json
import uuid
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
import os

class ChromeBridgeService:
    """Chrome桥接服务 - 基于MidSceneJS Chrome扩展"""
    
    def __init__(self):
        self.bridge_available = False
        self.extension_id = None
        self.ai_config = self._load_ai_config()
        
    def _load_ai_config(self) -> Dict[str, str]:
        """加载AI配置"""
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "model": os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest")
        }
    
    def check_chrome_extension_status(self) -> Dict[str, Any]:
        """检查Chrome扩展状态"""
        try:
            # 检查Chrome是否运行
            chrome_running = self._is_chrome_running()
            
            # 检查MidSceneJS扩展是否安装（通过检查扩展目录）
            extension_installed = self._check_extension_installed()
            
            # 检查AI配置
            ai_configured = bool(self.ai_config["api_key"])
            
            status = {
                "chrome_running": chrome_running,
                "extension_installed": extension_installed,
                "ai_configured": ai_configured,
                "bridge_available": chrome_running and extension_installed and ai_configured,
                "message": self._get_status_message(chrome_running, extension_installed, ai_configured)
            }
            
            self.bridge_available = status["bridge_available"]
            return status
            
        except Exception as e:
            return {
                "chrome_running": False,
                "extension_installed": False,
                "ai_configured": False,
                "bridge_available": False,
                "error": str(e),
                "message": f"状态检查失败: {str(e)}"
            }
    
    def _is_chrome_running(self) -> bool:
        """检查Chrome是否运行"""
        try:
            # macOS
            result = subprocess.run(
                ["pgrep", "-f", "Google Chrome"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            try:
                # Windows
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                    capture_output=True,
                    text=True
                )
                return "chrome.exe" in result.stdout
            except:
                return False
    
    def _check_extension_installed(self) -> bool:
        """检查MidSceneJS扩展是否安装"""
        try:
            # 这里可以通过检查Chrome扩展目录或其他方式
            # 简化实现：假设如果有AI配置就认为扩展已安装
            return bool(self.ai_config["api_key"])
        except:
            return False
    
    def _get_status_message(self, chrome_running: bool, extension_installed: bool, ai_configured: bool) -> str:
        """获取状态消息"""
        if not chrome_running:
            return "请启动Chrome浏览器"
        elif not extension_installed:
            return "请安装MidSceneJS Chrome扩展"
        elif not ai_configured:
            return "请配置AI模型API密钥"
        else:
            return "Chrome桥接模式就绪"
    
    def create_bridge_script(self, testcase_data: Dict[str, Any], mode: str = "newTab") -> str:
        """创建桥接执行脚本"""
        execution_id = str(uuid.uuid4())
        
        # 解析测试步骤
        steps = json.loads(testcase_data.get("steps", "[]"))
        
        # 生成TypeScript脚本
        script_content = self._generate_typescript_script(
            testcase_data, steps, execution_id, mode
        )
        
        # 保存脚本文件
        script_path = f"temp_scripts/bridge_execution_{execution_id}.ts"
        os.makedirs("temp_scripts", exist_ok=True)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        return script_path
    
    def _generate_typescript_script(self, testcase_data: Dict[str, Any], steps: List[Dict], execution_id: str, mode: str) -> str:
        """生成TypeScript执行脚本"""
        
        # 步骤转换
        step_commands = []
        for i, step in enumerate(steps):
            action = step.get("action")
            params = step.get("params", {})
            description = step.get("description", action)
            
            if action == "navigate":
                url = params.get("url")
                step_commands.append(f'    // 步骤 {i+1}: {description}')
                if mode == "newTab":
                    step_commands.append(f'    await agent.connectNewTabWithUrl("{url}");')
                else:
                    step_commands.append(f'    await page.goto("{url}");')
                    
            elif action == "ai_input":
                text = params.get("text")
                locate = params.get("locate", "输入框")
                step_commands.append(f'    // 步骤 {i+1}: {description}')
                step_commands.append(f'    await agent.aiInput("{text}", "{locate}");')
                
            elif action == "ai_tap":
                prompt = params.get("prompt")
                step_commands.append(f'    // 步骤 {i+1}: {description}')
                step_commands.append(f'    await agent.aiTap("{prompt}");')
                
            elif action == "ai_assert":
                prompt = params.get("prompt")
                step_commands.append(f'    // 步骤 {i+1}: {description}')
                step_commands.append(f'    await agent.aiAssert("{prompt}");')
                
            elif action == "ai_wait_for":
                prompt = params.get("prompt")
                timeout = params.get("timeout", 10000)
                step_commands.append(f'    // 步骤 {i+1}: {description}')
                step_commands.append(f'    await agent.aiWaitFor("{prompt}", {timeout});')
            
            # 添加截图
            step_commands.append(f'    await agent.logScreenshot("step_{i+1}_{action}");')
            step_commands.append(f'    await sleep(1000); // 短暂延迟')
        
        # 生成完整脚本
        script = f'''
import {{ AgentOverChromeBridge }} from "@midscene/web/bridge-mode";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// 执行ID: {execution_id}
// 测试用例: {testcase_data.get("name", "未知测试用例")}
// 执行模式: {mode}

Promise.resolve(
  (async () => {{
    const agent = new AgentOverChromeBridge({{
      generateReport: true,
      autoPrintReportMsg: true
    }});

    try {{
      console.log("🚀 开始执行测试用例: {testcase_data.get('name', '未知测试用例')}");
      
{chr(10).join(step_commands)}
      
      console.log("✅ 测试用例执行完成");
      
    }} catch (error) {{
      console.error("❌ 测试执行失败:", error);
      throw error;
    }} finally {{
      // 清理连接
      await agent.destroy(true); // 关闭新创建的标签页
    }}
  }})()
);
'''
        return script
    
    async def execute_bridge_script(self, script_path: str, execution_id: str) -> Dict[str, Any]:
        """执行桥接脚本"""
        try:
            # 使用tsx执行TypeScript脚本
            process = await asyncio.create_subprocess_exec(
                "npx", "tsx", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "execution_id": execution_id,
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
                "return_code": process.returncode
            }
            
            # 清理临时脚本
            try:
                os.remove(script_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                "execution_id": execution_id,
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
    
    def get_installation_guide(self) -> Dict[str, Any]:
        """获取安装指南"""
        return {
            "title": "MidSceneJS Chrome扩展安装指南",
            "steps": [
                {
                    "step": 1,
                    "title": "安装Node.js和npm",
                    "description": "访问 https://nodejs.org/ 下载并安装Node.js",
                    "command": "node --version && npm --version"
                },
                {
                    "step": 2,
                    "title": "安装MidSceneJS CLI",
                    "description": "全局安装MidSceneJS命令行工具",
                    "command": "npm install -g @midscene/cli"
                },
                {
                    "step": 3,
                    "title": "构建Chrome扩展",
                    "description": "克隆MidSceneJS仓库并构建扩展",
                    "commands": [
                        "git clone https://github.com/web-infra-dev/midscene.git",
                        "cd midscene",
                        "pnpm install",
                        "cd apps/chrome-extension",
                        "pnpm run build"
                    ]
                },
                {
                    "step": 4,
                    "title": "安装Chrome扩展",
                    "description": "在Chrome中加载扩展",
                    "instructions": [
                        "打开Chrome浏览器",
                        "访问 chrome://extensions/",
                        "开启'开发者模式'",
                        "点击'加载已解压的扩展程序'",
                        "选择 midscene/apps/chrome-extension/dist 目录"
                    ]
                },
                {
                    "step": 5,
                    "title": "配置AI模型",
                    "description": "在扩展中配置API密钥",
                    "config": {
                        "OPENAI_API_KEY": "your_dashscope_api_key",
                        "OPENAI_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                        "MIDSCENE_MODEL_NAME": "qwen-vl-max-latest"
                    }
                }
            ],
            "troubleshooting": [
                {
                    "problem": "扩展无法连接",
                    "solution": "确保点击扩展中的'允许连接'按钮"
                },
                {
                    "problem": "AI调用失败",
                    "solution": "检查API密钥是否正确配置"
                },
                {
                    "problem": "脚本执行超时",
                    "solution": "确保Chrome浏览器保持打开状态"
                }
            ]
        }

# 使用示例
async def main():
    """测试Chrome桥接服务"""
    service = ChromeBridgeService()
    
    # 检查状态
    status = service.check_chrome_extension_status()
    print(f"桥接状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
    
    if status["bridge_available"]:
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
                }
            ])
        }
        
        # 创建并执行脚本
        script_path = service.create_bridge_script(testcase, "newTab")
        print(f"脚本已创建: {script_path}")
        
        # 执行脚本
        result = await service.execute_bridge_script(script_path, "test-execution")
        print(f"执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        # 显示安装指南
        guide = service.get_installation_guide()
        print(f"安装指南: {json.dumps(guide, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(main())
