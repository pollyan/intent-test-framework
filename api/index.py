"""
Vercel入口文件 - Intent Test Framework
简化版本，专为Serverless环境优化
"""

import sys
import os
from flask import Flask, jsonify

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 创建Flask应用
app = Flask(__name__)

# 基本配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# 简单的健康检查路由
@app.route('/')
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'Intent Test Framework is running',
        'environment': 'Vercel Serverless',
        'database_url': os.getenv('DATABASE_URL', 'Not configured')[:50] + '...' if os.getenv('DATABASE_URL') else 'Not configured'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

# 尝试导入完整应用
try:
    # 设置环境变量
    os.environ['VERCEL'] = '1'

    # 导入数据库配置
    from web_gui.database_config import get_flask_config, print_database_info

    # 应用数据库配置
    db_config = get_flask_config()
    app.config.update(db_config)

    # 导入模型和路由
    from web_gui.models import db
    from web_gui.api_routes import api_bp

    # 初始化数据库
    db.init_app(app)

    # 注册API路由
    app.register_blueprint(api_bp)

    # 添加CORS支持
    from flask_cors import CORS
    CORS(app, origins="*")

    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status': 'ok',
            'message': 'API is working',
            'database': 'connected'
        })

    print("✅ 完整应用加载成功")

except Exception as e:
    print(f"⚠️ 完整应用加载失败: {e}")

    @app.route('/error')
    def show_error():
        return jsonify({
            'status': 'error',
            'message': f'应用加载失败: {str(e)}',
            'suggestion': '请检查环境变量和依赖配置'
        }), 500

# Vercel需要的应用对象
application = app

if __name__ == '__main__':
    app.run(debug=True)
