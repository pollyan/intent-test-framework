#!/bin/bash
# Systemd服务配置脚本

set -e

echo "=========================================="
echo "  Systemd服务配置"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

APP_DIR="/opt/intent-test-framework"
SERVICE_FILE="/etc/systemd/system/intent-test-framework.service"

# 1. 复制systemd服务文件
echo "[1/4] 复制systemd服务文件..."
cp scripts/deployment/intent-test-framework.service $SERVICE_FILE

# 2. 确保启动脚本有执行权限
echo ""
echo "[2/4] 设置文件权限..."
chmod +x $APP_DIR/scripts/deployment/start-production.py
chown -R appuser:appuser $APP_DIR

# 3. 重新加载systemd
echo ""
echo "[3/4] 重新加载systemd..."
systemctl daemon-reload

# 4. 启用并启动服务
echo ""
echo "[4/4] 启用并启动服务..."
systemctl enable intent-test-framework.service
systemctl start intent-test-framework.service

# 等待服务启动
sleep 2

# 检查服务状态
echo ""
echo "服务状态:"
systemctl status intent-test-framework.service --no-pager -l

echo ""
echo "=========================================="
echo "✅ Systemd服务配置完成！"
echo "=========================================="
echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status intent-test-framework"
echo "  查看日志: sudo journalctl -u intent-test-framework -f"
echo "  重启服务: sudo systemctl restart intent-test-framework"
echo "  停止服务: sudo systemctl stop intent-test-framework"
echo ""


