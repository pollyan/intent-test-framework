#!/usr/bin/env python3
"""
启动MidSceneJS服务器的脚本
用于支持真实的AI驱动测试执行
"""

import os
import sys
import subprocess
import time
import requests
import json
from pathlib import Path

def check_node_and_npm():
    """检查Node.js和npm是否安装"""
    try:
        node_result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        npm_result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        
        if node_result.returncode == 0 and npm_result.returncode == 0:
            print(f"✅ Node.js版本: {node_result.stdout.strip()}")
            print(f"✅ npm版本: {npm_result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js或npm未安装")
            return False
    except FileNotFoundError:
        print("❌ Node.js或npm未找到")
        return False

def install_midscene():
    """安装MidSceneJS"""
    print("📦 安装MidSceneJS...")
    try:
        result = subprocess.run(['npm', 'install', '-g', '@midscene/cli'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ MidSceneJS安装成功")
            return True
        else:
            print(f"❌ MidSceneJS安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 安装过程出错: {e}")
        return False

def check_ai_config():
    """检查AI配置"""
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    model_name = os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest')
    
    if not api_key:
        print("⚠️  未配置OPENAI_API_KEY")
        print("请设置环境变量:")
        print("export OPENAI_API_KEY='your_api_key'")
        print("export OPENAI_BASE_URL='https://dashscope.aliyuncs.com/compatible-mode/v1'")
        print("export MIDSCENE_MODEL_NAME='qwen-vl-max-latest'")
        return False
    
    print(f"✅ AI配置检查通过")
    print(f"   模型: {model_name}")
    print(f"   API地址: {base_url}")
    return True

def create_midscene_config():
    """创建MidSceneJS配置文件"""
    config = {
        "model": {
            "name": os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest'),
            "apiKey": os.getenv('OPENAI_API_KEY'),
            "baseURL": os.getenv('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        },
        "server": {
            "port": 3001,
            "host": "127.0.0.1"
        },
        "browser": {
            "headless": True,
            "defaultTimeout": 30000
        }
    }
    
    config_path = Path('midscene.config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置文件已创建: {config_path}")
    return config_path

def start_midscene_server():
    """启动MidSceneJS服务器"""
    print("🚀 启动MidSceneJS服务器...")
    
    try:
        # 启动服务器
        process = subprocess.Popen(
            ['npx', 'midscene', 'server', '--port', '3001'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(5)
        
        # 检查服务器是否启动成功
        try:
            response = requests.get('http://127.0.0.1:3001/health', timeout=5)
            if response.status_code == 200:
                print("✅ MidSceneJS服务器启动成功")
                print("🌐 服务器地址: http://127.0.0.1:3001")
                return process
            else:
                print(f"❌ 服务器健康检查失败: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到服务器: {e}")
            return None
            
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        return None

def main():
    """主函数"""
    print("=== MidSceneJS服务器启动器 ===\n")
    
    # 检查依赖
    if not check_node_and_npm():
        print("\n请先安装Node.js和npm:")
        print("https://nodejs.org/")
        return 1
    
    # 检查AI配置
    if not check_ai_config():
        print("\n请先配置AI相关环境变量")
        return 1
    
    # 创建配置文件
    config_path = create_midscene_config()
    
    # 安装MidSceneJS（如果需要）
    print("\n检查MidSceneJS安装...")
    try:
        result = subprocess.run(['npx', 'midscene', '--version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            if not install_midscene():
                return 1
    except:
        if not install_midscene():
            return 1
    
    # 启动服务器
    server_process = start_midscene_server()
    if not server_process:
        return 1
    
    print("\n🎉 MidSceneJS服务器已启动！")
    print("现在可以使用真实的AI驱动测试执行功能")
    print("\n按Ctrl+C停止服务器...")
    
    try:
        # 保持服务器运行
        server_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务器...")
        server_process.terminate()
        server_process.wait()
        print("✅ 服务器已停止")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
