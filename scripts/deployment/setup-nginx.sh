#!/bin/bash
# Nginx配置脚本

set -e

echo "=========================================="
echo "  Nginx反向代理配置"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

APP_DIR="/opt/intent-test-framework"
NGINX_CONF="/etc/nginx/sites-available/intent-test-framework"
NGINX_ENABLED="/etc/nginx/sites-enabled/intent-test-framework"

# 1. 复制Nginx配置文件
echo "[1/4] 复制Nginx配置文件..."
cp scripts/deployment/nginx-intent-test-framework.conf $NGINX_CONF

# 2. 创建符号链接
echo ""
echo "[2/4] 启用Nginx配置..."
if [ -L $NGINX_ENABLED ]; then
    rm $NGINX_ENABLED
fi
ln -s $NGINX_CONF $NGINX_ENABLED

# 3. 测试Nginx配置
echo ""
echo "[3/4] 测试Nginx配置..."
nginx -t

# 4. 重启Nginx
echo ""
echo "[4/4] 重启Nginx服务..."
systemctl reload nginx

echo ""
echo "=========================================="
echo "✅ Nginx配置完成！"
echo "=========================================="
echo ""
echo "Nginx配置已启用"
echo "访问地址: http://www.datou212.tech"
echo ""


