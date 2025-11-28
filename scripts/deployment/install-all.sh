#!/bin/bash
# 完整的服务器部署脚本
# 在服务器上直接执行

set -e

echo "=========================================="
echo "  AI4SE工具集 - 服务器部署"
echo "=========================================="
echo ""

# 1. 安装 Python 3.11
echo "[1/8] 安装 Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip libpq-dev
python3.11 --version

# 2. 安装 Node.js
echo ""
echo "[2/8] 安装 Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
    sudo apt install -y nodejs
fi
node --version

# 3. 安装 PostgreSQL
echo ""
echo "[3/8] 安装 PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
psql --version

# 4. 安装 Nginx
echo ""
echo "[4/8] 安装 Nginx..."
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
nginx -v

# 5. 创建应用用户
echo ""
echo "[5/8] 创建应用用户..."
sudo useradd -m -s /bin/bash appuser 2>/dev/null || echo "appuser already exists"

# 6. 克隆代码
echo ""
echo "[6/8] 部署应用代码..."
if [ ! -d "/opt/intent-test-framework" ]; then
    sudo git clone https://github.com/pollyan/intent-test-framework.git /opt/intent-test-framework
else
    cd /opt/intent-test-framework
    sudo git pull
fi

# 7. 创建虚拟环境和安装依赖
echo ""
echo "[7/8] 安装 Python 依赖..."
cd /opt/intent-test-framework
sudo -u appuser python3.11 -m venv venv
sudo -u appuser ./venv/bin/pip install --upgrade pip
sudo -u appuser ./venv/bin/pip install -r requirements.txt

# 8. 设置权限
echo ""
echo "[8/8] 设置文件权限..."
sudo chown -R appuser:appuser /opt/intent-test-framework

echo ""
echo "=========================================="
echo "✅ 基础环境安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 配置数据库: cd /opt/intent-test-framework && sudo bash scripts/deployment/setup-database.sh"
echo "2. 配置环境变量: sudo nano /opt/intent-test-framework/.env"
echo "3. 初始化数据库: sudo bash scripts/deployment/init-database.sh"
echo "4. 配置服务: sudo bash scripts/deployment/setup-systemd.sh"
echo "5. 配置 Nginx: sudo bash scripts/deployment/setup-nginx.sh"
echo ""


