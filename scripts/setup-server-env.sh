#!/bin/bash

# ========================================
# 服务器环境配置脚本
# ========================================
# 在腾讯云服务器上执行此脚本来配置环境
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 数据库配置
DB_USER="intent_user"
DB_PASSWORD="iN7tLIpx&KcVBB@7rboO7JlP"
SECRET_KEY="bf41cfbfe3d925cd25c4dcbfe0f90897b456a4031d93be4e71b7b39ad3bc0d35"

log_info "=========================================="
log_info "🔧 配置腾讯云服务器环境"
log_info "=========================================="

# 1. 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用 root 权限运行此脚本"
    echo "使用方式: sudo bash $0"
    exit 1
fi

# 2. 创建项目目录（如果不存在）
PROJECT_DIR="/opt/intent-test-framework"
if [ ! -d "$PROJECT_DIR" ]; then
    log_info "创建项目目录..."
    mkdir -p "$PROJECT_DIR"
    log_info "✅ 项目目录已创建: $PROJECT_DIR"
else
    log_info "✅ 项目目录已存在: $PROJECT_DIR"
fi

# 3. 创建 .env 文件
log_info "创建 .env 配置文件..."
cat > "$PROJECT_DIR/.env" << EOF
# Intent Test Framework - 生产环境配置
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
EOF

chmod 600 "$PROJECT_DIR/.env"
chown ubuntu:ubuntu "$PROJECT_DIR/.env"
log_info "✅ .env 文件已创建"

# 4. 配置防火墙
log_info "配置防火墙规则..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 5001/tcp
    log_info "✅ 防火墙规则已配置"
else
    log_warn "未找到 ufw，请手动配置防火墙"
fi

# 5. 创建必要的目录
log_info "创建必要的目录..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/web_gui/static/screenshots"
chown -R ubuntu:ubuntu "$PROJECT_DIR"
log_info "✅ 目录结构已准备"

# 6. 验证 Docker 环境
log_info "验证 Docker 环境..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_info "✅ Docker: $DOCKER_VERSION"
else
    log_error "Docker 未安装"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    log_info "✅ Docker Compose: $COMPOSE_VERSION"
else
    log_error "Docker Compose 未安装"
    exit 1
fi

# 7. 显示配置摘要
log_info "=========================================="
log_info "✅ 服务器环境配置完成！"
log_info "=========================================="
echo ""
echo "配置摘要:"
echo "  项目目录: $PROJECT_DIR"
echo "  数据库用户: $DB_USER"
echo "  数据库密码: $DB_PASSWORD"
echo "  Flask 密钥: ${SECRET_KEY:0:20}..."
echo ""
log_info "下一步："
log_info "1. 在 GitHub 仓库中配置 Secrets（参考 github_secrets_config.md）"
log_info "2. 提交代码变更以触发 GitHub Actions 自动部署"
log_info "3. 监控部署日志并验证服务状态"
echo ""
log_info "服务将运行在: http://120.53.220.231:5001"
log_info "=========================================="
