"""AI 智能体 Flask 应用入口"""
import sys
import os

# 添加 shared 模块到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from flask import Flask
from shared.config import SharedConfig

def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../../frontend/public/static',
        static_url_path='/static'
    )
    
    # 应用配置
    app.config.from_object(SharedConfig)
    
    # 数据库配置
    from shared.database import get_database_config
    app.config.update(get_database_config())
    
    # 初始化数据库
    from backend.models import db
    db.init_app(app)
    
    with app.app_context():
        # 确保数据库表存在
        try:
            db.create_all()
            print("✅ 数据库表验证完成")
        except Exception as e:
            print(f"⚠️ 数据库表创建失败: {e}")
    
    # 添加时区格式化过滤器
    @app.template_filter('utc_to_local')
    def utc_to_local_filter(dt):
        """将UTC时间转换为带时区标识的ISO格式"""
        if dt is None:
            return ""
        try:
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except AttributeError:
            return ""
    
    # 注册 AI 智能体相关的蓝图
    try:
        from backend.api import requirements_bp, ai_configs_bp
        app.register_blueprint(requirements_bp)
        app.register_blueprint(ai_configs_bp)
        print("✅ API 蓝图注册成功")
    except Exception as e:
        import traceback
        print(f"⚠️ 蓝图注册失败: {e}")
        traceback.print_exc()
    
    # 注册页面路由
    from flask import render_template
    
    @app.route('/')
    @app.route('/ai-agents/')
    def index():
        return render_template('requirements_analyzer.html')
    
    @app.route('/config')
    @app.route('/config-management')
    @app.route('/ai-agents/config')
    @app.route('/ai-agents/config-management')
    def config():
        return render_template('config_management.html')
    
    @app.route('/health')
    @app.route('/ai-agents/health')
    def health():
        return {"status": "ok", "service": "ai-agents"}
    
    return app


if __name__ == '__main__':
    app = create_app()
    print("=== AI 智能体应用启动中 ===")
    print("📍 Web界面: http://localhost:5002")
    print("📍 API接口: http://localhost:5002/api/")
    print("=========================")
    app.run(debug=True, host='0.0.0.0', port=5002)

