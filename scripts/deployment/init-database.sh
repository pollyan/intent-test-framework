#!/bin/bash
# 数据库初始化脚本

set -e

echo "=========================================="
echo "  数据库初始化"
echo "=========================================="
echo ""

APP_DIR="/opt/intent-test-framework"
APP_USER="appuser"

# 检查.env文件是否存在
if [ ! -f "$APP_DIR/.env" ]; then
    echo "错误: .env 文件不存在！"
    echo "请先创建 $APP_DIR/.env 文件并配置 DATABASE_URL"
    exit 1
fi

# 加载环境变量
export $(grep -v '^#' $APP_DIR/.env | xargs)

# 检查DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "错误: DATABASE_URL 未在 .env 文件中设置！"
    exit 1
fi

echo "使用数据库: $DATABASE_URL"
echo ""

# 运行数据库初始化
echo "初始化数据库表结构..."
cd $APP_DIR
sudo -u $APP_USER $APP_DIR/venv/bin/python <<EOF
import sys
import os
sys.path.insert(0, os.getcwd())

# 设置环境变量
for line in open('.env'):
    if '=' in line and not line.strip().startswith('#'):
        key, value = line.strip().split('=', 1)
        os.environ[key] = value

# 初始化数据库
from web_gui.models import db
from web_gui.app_enhanced import create_app

app = create_app()
with app.app_context():
    print("创建数据库表...")
    db.create_all()
    print("✅ 数据库表创建完成！")
    
    # 验证表是否创建
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"已创建 {len(tables)} 个表: {', '.join(tables)}")
EOF

echo ""
echo "=========================================="
echo "✅ 数据库初始化完成！"
echo "=========================================="


