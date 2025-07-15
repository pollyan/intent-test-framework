#!/bin/bash

# 更新本地代理服务器包
# 用于修复依赖和同步最新代码

echo "🔄 正在更新本地代理服务器包..."

# 定义路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROXY_DIR="/Users/huian@thoughtworks.com/Downloads/intent-test-proxy"

# 检查代理目录是否存在
if [ ! -d "$PROXY_DIR" ]; then
    echo "❌ 本地代理目录不存在: $PROXY_DIR"
    exit 1
fi

echo "📁 项目目录: $PROJECT_DIR"
echo "📁 代理目录: $PROXY_DIR"

# 1. 更新package.json
echo "🔧 更新package.json..."
cat > "$PROXY_DIR/package.json" << 'EOF'
{
  "name": "intent-test-proxy",
  "version": "1.0.0",
  "description": "Intent Test Framework 本地代理服务器",
  "main": "midscene_server.js",
  "scripts": {
    "start": "node midscene_server.js",
    "install-deps": "npm install"
  },
  "dependencies": {
    "@midscene/web": "^0.20.1",
    "@playwright/test": "^1.45.0",
    "axios": "^1.10.0",
    "cors": "^2.8.5",
    "express": "^4.18.2",
    "playwright": "^1.45.0",
    "socket.io": "^4.7.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0"
  },
  "keywords": ["midscene", "automation", "testing", "ai"],
  "author": "Intent Test Framework",
  "license": "MIT"
}
EOF

# 2. 复制最新的服务器文件
echo "📄 复制最新的midscene_server.js..."
cp "$PROJECT_DIR/midscene_server.js" "$PROXY_DIR/midscene_server.js"

# 3. 确保环境文件存在
echo "⚙️  检查环境配置文件..."
if [ ! -f "$PROXY_DIR/.env.example" ]; then
    cat > "$PROXY_DIR/.env.example" << 'EOF'
# AI API 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# 数据库配置（可选，本地代理默认连接到主系统）
API_BASE_URL=http://localhost:5001/api
EOF
fi

# 4. 重新安装依赖
echo "📦 重新安装依赖..."
cd "$PROXY_DIR"
rm -rf node_modules package-lock.json
npm install

if [ $? -eq 0 ]; then
    echo "✅ 本地代理服务器包更新成功！"
    echo ""
    echo "📋 使用方法:"
    echo "1. 进入代理目录: cd '$PROXY_DIR'"
    echo "2. 配置环境变量: cp .env.example .env && nano .env"
    echo "3. 启动服务器: ./start.sh"
else
    echo "❌ 依赖安装失败"
    exit 1
fi