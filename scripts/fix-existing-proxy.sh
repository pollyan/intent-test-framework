#!/bin/bash

# 修复现有本地代理包的依赖问题
# 直接修复 /Users/huian@thoughtworks.com/Downloads/intent-test-proxy

echo "🔧 正在修复现有本地代理包的依赖问题..."

PROXY_DIR="/Users/huian@thoughtworks.com/Downloads/intent-test-proxy"

# 检查代理目录是否存在
if [ ! -d "$PROXY_DIR" ]; then
    echo "❌ 本地代理目录不存在: $PROXY_DIR"
    exit 1
fi

echo "📁 代理目录: $PROXY_DIR"

# 1. 备份原有的 package.json
echo "📋 备份原有配置..."
if [ -f "$PROXY_DIR/package.json" ]; then
    cp "$PROXY_DIR/package.json" "$PROXY_DIR/package.json.backup"
fi

# 2. 更新 package.json 为正确的依赖
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

# 3. 复制最新的服务器文件
echo "📄 复制最新的midscene_server.js..."
cp "/Users/huian@thoughtworks.com/intent-test-framework/midscene_server.js" "$PROXY_DIR/midscene_server.js"

# 4. 清理并重新安装依赖
echo "🧹 清理旧依赖..."
cd "$PROXY_DIR"
rm -rf node_modules package-lock.json

echo "📦 重新安装依赖..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ 依赖安装成功！"
    
    # 5. 验证关键依赖
    echo "🔍 验证关键依赖..."
    
    if [ ! -d "node_modules/@playwright/test" ]; then
        echo "❌ @playwright/test 依赖验证失败"
        exit 1
    fi
    
    if [ ! -d "node_modules/axios" ]; then
        echo "❌ axios 依赖验证失败"
        exit 1
    fi
    
    echo "✅ 所有依赖验证通过！"
    
    # 6. 测试服务器启动
    echo "🧪 测试服务器启动..."
    timeout 10s node midscene_server.js > /dev/null 2>&1
    if [ $? -eq 124 ]; then
        echo "✅ 服务器启动测试通过！"
    else
        echo "❌ 服务器启动测试失败"
        exit 1
    fi
    
    echo ""
    echo "🎉 本地代理包修复完成！"
    echo ""
    echo "📋 现在可以使用以下命令启动:"
    echo "   cd '$PROXY_DIR'"
    echo "   ./start.sh"
    echo ""
else
    echo "❌ 依赖安装失败"
    exit 1
fi