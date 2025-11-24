#!/bin/bash
# 一键部署脚本
# 按顺序执行所有部署步骤

set -e

echo "=========================================="
echo "  AI4SE工具集 - 一键部署脚本"
echo "=========================================="
echo ""
echo "此脚本将按顺序执行以下步骤："
echo "  1. 服务器环境准备"
echo "  2. 数据库配置"
echo "  3. 应用代码部署"
echo "  4. 环境变量配置（需要手动编辑）"
echo "  5. 数据库初始化"
echo "  6. Systemd服务配置"
echo "  7. Nginx反向代理配置"
echo "  8. 防火墙配置"
echo ""
read -p "是否继续？(y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. 服务器环境准备
echo ""
echo "=========================================="
echo "步骤 1/8: 服务器环境准备"
echo "=========================================="
bash $SCRIPT_DIR/setup-server.sh

# 2. 数据库配置
echo ""
echo "=========================================="
echo "步骤 2/8: 数据库配置"
echo "=========================================="
bash $SCRIPT_DIR/setup-database.sh

# 3. 应用代码部署
echo ""
echo "=========================================="
echo "步骤 3/8: 应用代码部署"
echo "=========================================="
bash $SCRIPT_DIR/deploy-app.sh

# 4. 环境变量配置提示
echo ""
echo "=========================================="
echo "步骤 4/8: 环境变量配置"
echo "=========================================="
echo "请手动编辑环境变量文件："
echo "  sudo -u appuser nano /opt/intent-test-framework/.env"
echo ""
echo "必须配置的变量："
echo "  - DATABASE_URL (使用步骤2中生成的连接字符串)"
echo "  - SECRET_KEY (生成强随机密钥)"
echo "  - OPENAI_API_KEY"
echo "  - OPENAI_BASE_URL"
echo "  - MIDSCENE_MODEL_NAME"
echo ""
read -p "配置完成后按Enter继续..."

# 5. 数据库初始化
echo ""
echo "=========================================="
echo "步骤 5/8: 数据库初始化"
echo "=========================================="
bash $SCRIPT_DIR/init-database.sh

# 6. Systemd服务配置
echo ""
echo "=========================================="
echo "步骤 6/8: Systemd服务配置"
echo "=========================================="
bash $SCRIPT_DIR/setup-systemd.sh

# 7. Nginx反向代理配置
echo ""
echo "=========================================="
echo "步骤 7/8: Nginx反向代理配置"
echo "=========================================="
bash $SCRIPT_DIR/setup-nginx.sh

# 8. 防火墙配置
echo ""
echo "=========================================="
echo "步骤 8/8: 防火墙配置"
echo "=========================================="
bash $SCRIPT_DIR/setup-firewall.sh

# 完成
echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "应用已部署到: http://www.datou212.tech"
echo ""
echo "服务管理命令："
echo "  查看应用状态: sudo systemctl status intent-test-framework"
echo "  查看应用日志: sudo journalctl -u intent-test-framework -f"
echo "  重启应用: sudo systemctl restart intent-test-framework"
echo ""
echo "验证部署："
echo "  curl http://www.datou212.tech/health"
echo ""


