#!/bin/bash
# 防火墙配置脚本

set -e

echo "=========================================="
echo "  防火墙配置"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 检查ufw是否安装
if ! command -v ufw &> /dev/null; then
    echo "安装ufw防火墙..."
    apt install -y ufw
fi

# 配置防火墙规则
echo "[1/3] 配置防火墙规则..."

# 允许SSH（重要！）
ufw allow 22/tcp

# 允许HTTP
ufw allow 80/tcp

# 允许HTTPS（为将来SSL证书做准备）
ufw allow 443/tcp

# 5001端口仅本地访问，不需要开放

# 启用防火墙
echo ""
echo "[2/3] 启用防火墙..."
ufw --force enable

# 显示防火墙状态
echo ""
echo "[3/3] 防火墙状态:"
ufw status

echo ""
echo "=========================================="
echo "✅ 防火墙配置完成！"
echo "=========================================="
echo ""
echo "已开放的端口:"
echo "  - 22 (SSH)"
echo "  - 80 (HTTP)"
echo "  - 443 (HTTPS)"
echo ""


