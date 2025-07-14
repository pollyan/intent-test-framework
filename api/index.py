"""
Vercel入口文件
将请求转发到主应用
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入主应用
from web_gui.app_enhanced import app

# Vercel WSGI应用
application = app

# 如果直接运行，启动开发服务器
if __name__ == '__main__':
    app.run(debug=True)
