#!/bin/bash
# PostgreSQL数据库配置脚本

set -e

echo "=========================================="
echo "  PostgreSQL数据库配置"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 读取数据库配置
read -p "请输入数据库名称 [intent_test_framework]: " DB_NAME
DB_NAME=${DB_NAME:-intent_test_framework}

read -p "请输入数据库用户名 [intent_user]: " DB_USER
DB_USER=${DB_USER:-intent_user}

read -sp "请输入数据库密码: " DB_PASSWORD
echo ""

# 切换到postgres用户执行数据库操作
sudo -u postgres psql <<EOF
-- 创建数据库用户
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- 创建数据库
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- 连接到数据库并授予schema权限
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo ""
echo "=========================================="
echo "✅ 数据库配置完成！"
echo "=========================================="
echo ""
echo "数据库信息："
echo "  数据库名: $DB_NAME"
echo "  用户名: $DB_USER"
echo "  连接字符串: postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "请将连接字符串保存到 .env 文件的 DATABASE_URL 中"
echo ""


