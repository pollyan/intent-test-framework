#!/usr/bin/env python3
"""
生产环境启动脚本
监听127.0.0.1:5001，仅本地访问，通过Nginx反向代理对外提供服务
"""
import sys
import os

# 加载环境变量
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 导入应用
from api.index import app

if __name__ == "__main__":
    # 从环境变量读取配置
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    print("=== AI4SE工具集启动中 (生产环境) ===")
    print(f"📍 监听地址: {host}:{port}")
    print(f"📍 调试模式: {debug}")
    print("=========================")
    
    # 生产环境使用gunicorn或直接运行
    # 这里使用Flask内置服务器（生产环境建议使用gunicorn）
    app.run(debug=debug, host=host, port=port, threaded=True)


