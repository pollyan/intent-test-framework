#!/bin/bash
# 服务器环境准备脚本
# 用于Ubuntu Server 24.04 LTS

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  服务器环境准备脚本"
echo "  Ubuntu Server 24.04 LTS"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 1. 更新系统包管理器
echo "[1/7] 更新系统包管理器..."
apt update
apt upgrade -y

# 2. 安装Python 3.11+和pip
echo ""
echo "[2/7] 安装Python 3.11+和pip..."
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
python3.11 --version
pip3 --version

# 3. 安装Node.js 16+和npm
echo ""
echo "[3/7] 安装Node.js 16+和npm..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
node --version
npm --version

# 4. 安装PostgreSQL数据库服务器
echo ""
echo "[4/7] 安装PostgreSQL数据库服务器..."
apt install -y postgresql postgresql-contrib
systemctl start postgresql
systemctl enable postgresql
psql --version

# 5. 安装Nginx
echo ""
echo "[5/7] 安装Nginx..."
apt install -y nginx
systemctl start nginx
systemctl enable nginx
nginx -v

# 6. 安装Git
echo ""
echo "[6/7] 安装Git..."
apt install -y git
git --version

# 7. 创建应用运行用户（可选）
echo ""
echo "[7/7] 创建应用运行用户..."
if ! id -u appuser &>/dev/null; then
    useradd -m -s /bin/bash appuser
    echo "用户 'appuser' 已创建"
else
    echo "用户 'appuser' 已存在"
fi

# 安装其他必要工具
echo ""
echo "安装其他必要工具..."
apt install -y build-essential libpq-dev curl wget

echo ""
echo "=========================================="
echo "✅ 服务器环境准备完成！"
echo "=========================================="
echo ""
echo "已安装的组件："
echo "  - Python $(python3.11 --version | cut -d' ' -f2)"
echo "  - Node.js $(node --version)"
echo "  - PostgreSQL $(psql --version | cut -d' ' -f3)"
echo "  - Nginx $(nginx -v 2>&1 | cut -d'/' -f2)"
echo "  - Git $(git --version | cut -d' ' -f3)"
echo ""
echo "下一步：运行数据库配置脚本"
echo "  sudo bash scripts/deployment/setup-database.sh"


