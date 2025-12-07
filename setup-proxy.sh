#!/bin/bash

echo "=========================================="
echo "  修复 Node.js 环境并启动代理服务器"
echo "=========================================="
echo ""

# 加载 nvm
echo "[1/4] 加载 nvm..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# 检查 nvm 是否加载成功
if ! command -v nvm &> /dev/null; then
    echo "❌ nvm 未加载成功"
    echo "请重启终端后再试"
    exit 1
fi

echo "✅ nvm 已加载"

# 切换到 Node.js v20
echo ""
echo "[2/4] 切换到 Node.js v20..."
nvm use 20

# 验证版本
NODE_VERSION=$(node --version)
echo "✅ 当前 Node.js 版本: $NODE_VERSION"

if [[ ! "$NODE_VERSION" =~ ^v20 ]]; then
    echo "❌ Node.js 版本不正确"
    echo "尝试安装 Node.js v20..."
    nvm install 20
    nvm use 20
fi

# 清理 npm 缓存
echo ""
echo "[3/4] 清理 npm 缓存..."
npm cache clean --force
echo "✅ npm 缓存已清理"

# 进入代理服务器目录
echo ""
echo "[4/4] 启动代理服务器..."
cd /Users/anhui/Downloads/intent-test-proxy

# 启动服务器
bash start.sh
