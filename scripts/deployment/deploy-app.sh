#!/bin/bash
# 应用部署脚本

set -e

echo "=========================================="
echo "  应用部署脚本"
echo "=========================================="
echo ""

# 配置变量
APP_DIR="/opt/intent-test-framework"
APP_USER="appuser"
GIT_REPO="https://github.com/pollyan/intent-test-framework.git"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 1. 创建应用目录
echo "[1/5] 创建应用目录..."
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# 2. 克隆或更新代码
echo ""
echo "[2/5] 部署应用代码..."
if [ -d "$APP_DIR/.git" ]; then
    echo "代码已存在，更新代码..."
    sudo -u $APP_USER git -C $APP_DIR pull
else
    echo "克隆代码仓库..."
    sudo -u $APP_USER git clone $GIT_REPO $APP_DIR
fi

# 3. 创建Python虚拟环境
echo ""
echo "[3/5] 创建Python虚拟环境..."
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u $APP_USER python3.11 -m venv $APP_DIR/venv
fi

# 4. 安装Python依赖
echo ""
echo "[4/5] 安装Python依赖..."
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

# 5. 设置目录权限
echo ""
echo "[5/5] 设置目录权限..."
chown -R $APP_USER:$APP_USER $APP_DIR

echo ""
echo "=========================================="
echo "✅ 应用代码部署完成！"
echo "=========================================="
echo ""
echo "应用目录: $APP_DIR"
echo "下一步：配置环境变量和数据库初始化"
echo "  1. 创建 $APP_DIR/.env 文件"
echo "  2. 运行数据库初始化脚本"


