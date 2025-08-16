"""
增强版Web GUI测试用例管理系统 - Flask主应用
基于现有的MidSceneJS AI框架构建，采用模块化架构
"""
import os
import sys
import time
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
import json
import uuid
import threading

# 导入日志配置
try:
    from utils.logging_config import setup_logging
    LOGGING_AVAILABLE = True
except ImportError:
    try:
        from web_gui.utils.logging_config import setup_logging
        LOGGING_AVAILABLE = True
    except ImportError:
        LOGGING_AVAILABLE = False
        logging.basicConfig(level=logging.INFO)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入模块 - 修复Serverless环境的导入路径
try:
    from models import db, TestCase, ExecutionHistory, StepExecution, Template
    from api import register_api_routes
    from database_config import get_flask_config, print_database_info, validate_database_connection
    print("✅ 模块化API路由导入成功 (本地模式)")
except ImportError:
    # Serverless环境中使用绝对导入
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template
    from web_gui.api import register_api_routes
    from web_gui.database_config import get_flask_config, print_database_info, validate_database_connection
    print("✅ 模块化API路由导入成功 (Serverless模式)")

# 导入错误处理器
try:
    from utils.error_handler import APIError, ValidationError, NotFoundError, DatabaseError
except ImportError:
    from web_gui.utils.error_handler import APIError, ValidationError, NotFoundError, DatabaseError

# 尝试导入MidSceneAI，如果失败则使用模拟版本
try:
    from midscene_python import MidSceneAI
    AI_AVAILABLE = True
    print("✅ MidSceneAI导入成功")
except ImportError as e:
    print(f"⚠️  MidSceneAI导入失败: {e}")
    print("使用模拟AI引擎进行演示")
    AI_AVAILABLE = False

    # 创建模拟AI类
    class MockMidSceneAI:
        def __init__(self):
            self.current_url = None

        def goto(self, url):
            self.current_url = url
            print(f"[模拟] 访问页面: {url}")
            time.sleep(1)  # 模拟加载时间

        def ai_input(self, text, locate):
            print(f"[模拟] 在 '{locate}' 中输入: {text}")
            time.sleep(0.5)

        def ai_tap(self, prompt):
            print(f"[模拟] 点击: {prompt}")
            time.sleep(0.5)

        def ai_assert(self, prompt):
            print(f"[模拟] 验证: {prompt}")
            time.sleep(0.5)

        def ai_wait_for(self, prompt, timeout=10000):
            print(f"[模拟] 等待: {prompt} (超时: {timeout}ms)")
            time.sleep(1)

        def ai_scroll(self, direction='down', scroll_type='once', locate_prompt=None):
            print(f"[模拟] 滚动: {direction} ({scroll_type})")
            time.sleep(0.5)

        def take_screenshot(self, title):
            """模拟截图功能"""
            # 确保截图保存到正确的静态文件目录
            screenshot_filename = f"{title}.png"
            screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'screenshots')
            screenshot_path = os.path.join(screenshot_dir, screenshot_filename)

            print(f"[模拟] 截图保存到: {screenshot_path}")

            # 确保目录存在
            os.makedirs(screenshot_dir, exist_ok=True)

            # 创建一个简单的模拟截图
            try:
                from PIL import Image, ImageDraw
                # 创建一个800x600的图片
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)

                # 绘制一些模拟内容
                draw.rectangle([50, 50, 750, 550], outline='black', width=2)
                draw.text((100, 100), "模拟截图", fill='black')
                draw.text((100, 150), f"URL: {getattr(self, 'current_url', 'Unknown')}", fill='blue')
                draw.text((100, 200), f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill='gray')
                draw.text((100, 250), "这是AI执行引擎的模拟截图", fill='green')

                # 保存图片
                img.save(screenshot_path, 'PNG')
                print(f"[模拟] 截图已保存: {screenshot_path}")
            except ImportError:
                # 如果没有PIL库，创建一个简单的文本文件
                with open(screenshot_path.replace('.png', '.txt'), 'w') as f:
                    f.write(f"模拟截图 - {time.strftime('%Y-%m-%d %H:%M:%S')}\nURL: {getattr(self, 'current_url', 'Unknown')}")
                print(f"[模拟] 截图文本文件已保存: {screenshot_path.replace('.png', '.txt')}")
            except Exception as e:
                print(f"[模拟] 截图保存失败: {e}")
                # 创建一个空文件作为占位符
                with open(screenshot_path, 'w') as f:
                    f.write("")

            return f"web_gui/static/screenshots/{screenshot_filename}"

        def cleanup(self):
            print("[模拟] 清理AI资源")

    MidSceneAI = MockMidSceneAI

# 确保MockMidSceneAI在全局作用域中可用
if not AI_AVAILABLE:
    MockMidSceneAI = MidSceneAI

def register_error_handlers(app):
    """注册全局错误处理器"""
    
    @app.errorhandler(APIError)
    def handle_api_error(e):
        """处理API自定义异常"""
        logger = logging.getLogger(__name__)
        logger.warning(f"API错误: {e.message} (代码: {e.code})")
        
        response_data = e.to_dict()
        return jsonify(response_data), e.code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """处理验证错误"""
        return jsonify({
            'code': e.code,
            'message': e.message,
            'details': e.details
        }), e.code
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e):
        """处理404错误"""
        return jsonify({
            'code': 404,
            'message': e.message
        }), 404
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(e):
        """处理数据库错误"""
        logger = logging.getLogger(__name__)
        logger.error(f"数据库错误: {e.message}")
        
        return jsonify({
            'code': 500,
            'message': '数据库操作失败，请稍后重试'
        }), 500
    
    @app.errorhandler(404)
    def handle_404(e):
        """处理404错误"""
        if request.path.startswith('/api/'):
            return jsonify({
                'code': 404,
                'message': '接口不存在'
            }), 404
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def handle_500(e):
        """处理500错误"""
        logger = logging.getLogger(__name__)
        logger.error(f"服务器内部错误: {str(e)}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'code': 500,
                'message': '服务器内部错误'
            }), 500
        return render_template('500.html'), 500


def create_app(test_config=None):
    """应用工厂函数"""
    app = Flask(__name__)

    # 配置日志系统
    if LOGGING_AVAILABLE:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Intent Test Framework 启动中...")
    else:
        logger = logging.getLogger(__name__)
        logger.warning("高级日志配置不可用，使用基础日志配置")

    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    if test_config:
        # 如果传入测试配置，使用测试配置（用于单元测试）
        app.config.update(test_config)
        # 确保SQLite不使用连接池参数
        if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
            app.config.pop('SQLALCHEMY_ENGINE_OPTIONS', None)
    else:
        # 数据库配置 - 仅支持PostgreSQL
        try:
            db_config = get_flask_config()
            app.config.update(db_config)
        except (ValueError, ImportError) as e:
            print(f"❌ 数据库配置失败: {e}")
            print("请确保已正确配置PostgreSQL数据库连接。")
            sys.exit(1)

        # 打印数据库信息
        print_database_info()
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, origins="*")
    
    # 注册API蓝图
    # 注册模块化API路由
    register_api_routes(app)
    
    # 注册全局错误处理器
    register_error_handlers(app)
    
    # 添加时区格式化过滤器
    @app.template_filter('utc_to_local')
    def utc_to_local_filter(dt):
        """将UTC时间转换为带时区标识的ISO格式，供前端JavaScript转换为本地时间"""
        if dt is None:
            return ''
        try:
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        except AttributeError:
            return ''
    
    return app

def register_error_handlers(app):
    """注册全局错误处理器"""
    try:
        from utils.error_handler import APIError, ValidationError, NotFoundError, DatabaseError
    except ImportError:
        from web_gui.utils.error_handler import APIError, ValidationError, NotFoundError, DatabaseError
    
    @app.errorhandler(APIError)
    def handle_api_error(e):
        """处理API异常"""
        return jsonify({
            'code': e.code,
            'message': e.message,
            'details': e.details
        }), e.code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """处理验证异常"""
        return jsonify({
            'code': 400,
            'message': e.message,
            'details': e.details
        }), 400
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e):
        """处理资源不存在异常"""
        return jsonify({
            'code': 404,
            'message': e.message,
            'details': e.details
        }), 404
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(e):
        """处理数据库异常"""
        return jsonify({
            'code': 500,
            'message': e.message,
            'details': e.details
        }), 500

# 全局变量
app = None
socketio = None

def init_app():
    """初始化应用实例"""
    global app, socketio
    if app is None:
        app = create_app()
        socketio = SocketIO(app, cors_allowed_origins="*")
        setup_routes(app, socketio)
    return app, socketio

# 全局变量存储执行状态
execution_manager = {}

def setup_routes(app, socketio):
    """设置所有路由和WebSocket事件处理器"""
    
    # ==================== 主页路由 ====================
    
    @app.route('/')
    @app.route('/dashboard')
    def index():
        """主页"""
        return render_template('index.html')

    @app.route('/testcases')
    def testcases_page():
        """测试用例管理页面"""
        return render_template('testcases.html')

    @app.route('/testcases/create')
    def testcase_create_page():
        """测试用例创建页面"""
        # 创建一个空的测试用例对象用于创建模式
        class EmptyTestCase:
            def __init__(self):
                self.id = None
                self.name = ''
                self.description = ''
                self.category = '功能测试'  # 默认分类
                self.priority = 2
                self.tags = ''
                self.is_active = True
                self.created_by = 'admin'
                self.created_at = None
                self.updated_at = None
        
        empty_testcase = EmptyTestCase()
        
        return render_template('testcase_edit.html', 
                             testcase=empty_testcase,
                             steps_data='[]',
                             total_executions=0,
                             success_rate=0,
                             is_create_mode=True)

    @app.route('/testcases/<int:testcase_id>/edit')
    def testcase_edit_page(testcase_id):
        """测试用例编辑页面"""
        # 获取测试用例详情
        testcase = TestCase.query.get_or_404(testcase_id)
        
        # 获取执行统计信息
        execution_stats = db.session.query(ExecutionHistory).filter_by(test_case_id=testcase_id).all()
        total_executions = len(execution_stats)
        successful_executions = len([e for e in execution_stats if e.status == 'success'])
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        # 确保步骤数据是正确的JSON格式
        try:
            steps_data = json.loads(testcase.steps) if testcase.steps else []
        except (json.JSONDecodeError, TypeError):
            steps_data = []
        
        return render_template('testcase_edit.html', 
                             testcase=testcase,
                             steps_data=json.dumps(steps_data),
                             total_executions=total_executions,
                             success_rate=success_rate,
                             is_create_mode=False)

    @app.route('/execution')
    def execution_page():
        """执行控制台页面"""
        return render_template('execution.html')

    @app.route('/reports')
    def reports_page():
        """测试报告页面"""
        return render_template('reports.html')

    @app.route('/local-proxy')
    def local_proxy_page():
        """本地代理下载页面"""
        return render_template('local_proxy.html', current_date=datetime.utcnow().strftime('%Y-%m-%d'))

    @app.route('/debug_screenshot_history.html')
    def debug_screenshot_history():
        """调试截图历史功能"""
        import os
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug_screenshot_history.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @app.route('/step_editor')
    def step_editor_page():
        """步骤编辑器页面"""
        return render_template('step_editor.html')

    @app.route('/static/screenshots/<filename>')
    def screenshot_file(filename):
        """提供截图文件访问"""
        screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'screenshots')
        return send_from_directory(screenshot_dir, filename)

    # ==================== WebSocket事件处理 ====================

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        print(f'客户端已连接: {request.sid}')
        emit('connected', {
            'message': '连接成功',
            'ai_available': AI_AVAILABLE,
            'server_time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接"""
        print(f'客户端已断开: {request.sid}')

    @socketio.on('ping')
    def handle_ping():
        """心跳检测"""
        emit('pong', {'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')})

    @socketio.on('stop_execution')
    def handle_stop_execution(data):
        """停止执行测试用例"""
        execution_id = data.get('execution_id')
        if execution_id:
            # TODO: 实现停止执行逻辑
            emit('execution_stopped', {
                'execution_id': execution_id,
                'message': '执行已停止'
            })
        else:
            emit('error', {'message': '缺少execution_id参数'})

    @socketio.on('start_execution')
    def handle_start_execution(data):
        """开始执行测试用例"""
        try:
            testcase_id = data.get('testcase_id')
            mode = data.get('mode', 'headless')
            
            # 获取测试用例
            testcase = TestCase.query.get(testcase_id)
            if not testcase:
                emit('execution_error', {'message': '测试用例不存在'})
                return
            
            # 创建执行记录
            execution_id = str(uuid.uuid4())
            execution = ExecutionHistory(
                execution_id=execution_id,
                test_case_id=testcase_id,
                status='running',
                mode=mode,
                start_time=datetime.utcnow(),
                executed_by='web_user'
            )
            
            db.session.add(execution)
            db.session.commit()
            
            # 启动异步执行
            thread = threading.Thread(
                target=execute_testcase_async,
                args=(execution_id, testcase, mode, request.sid)
            )
            thread.daemon = True
            thread.start()
            
            emit('execution_started', {
                'execution_id': execution_id,
                'testcase_name': testcase.name
            })
            
        except Exception as e:
            emit('execution_error', {'message': f'启动执行失败: {str(e)}'})

def execute_testcase_async(execution_id, testcase, mode, client_sid):
    """异步执行测试用例"""
    ai = None
    try:
        # 确保app实例已创建
        global app
        if app is None:
            app, _ = init_app()
            
        # 获取执行记录
        with app.app_context():
            execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
            if not execution:
                socketio.emit('execution_error', {
                    'execution_id': execution_id,
                    'message': '执行记录不存在'
                }, room=client_sid)
                return

            # 解析测试步骤
            steps = json.loads(testcase.steps) if testcase.steps else []
            if not steps:
                socketio.emit('execution_error', {
                    'execution_id': execution_id,
                    'message': '测试用例没有定义执行步骤'
                }, room=client_sid)
                return

            execution.steps_total = len(steps)
            db.session.commit()

            # 初始化AI测试引擎
            try:
                ai = MidSceneAI()

                # 设置浏览器模式
                ai.set_browser_mode(mode)

                socketio.emit('execution_log', {
                    'execution_id': execution_id,
                    'message': f'AI引擎初始化成功 ({"真实" if AI_AVAILABLE else "模拟"}模式)',
                    'level': 'info'
                }, room=client_sid)
            except Exception as e:
                print(f"AI引擎初始化失败，使用模拟模式: {e}")
                # 如果真实AI引擎失败，回退到模拟模式
                ai = MockMidSceneAI()
                socketio.emit('execution_log', {
                    'execution_id': execution_id,
                    'message': f'AI引擎初始化失败，使用模拟模式: {str(e)}',
                    'level': 'warning'
                }, room=client_sid)

            steps_passed = 0
            steps_failed = 0
        
            # 执行每个步骤
            for i, step in enumerate(steps):
                step_start_time = datetime.utcnow()

                # 检查步骤是否被跳过
                if step.get('skip', False):
                    # 发送步骤跳过事件
                    socketio.emit('step_skipped', {
                        'execution_id': execution_id,
                        'step_index': i,
                        'step_description': step.get('description', step.get('action', f'步骤 {i+1}')),
                        'total_steps': len(steps),
                        'message': '此步骤已被标记为跳过'
                    }, room=client_sid)
                    
                    # 记录跳过的步骤
                    step_execution = StepExecution(
                        execution_id=execution_id,
                        step_index=i,
                        step_description=step.get('description', step.get('action', f'步骤 {i+1}')),
                        status='skipped',
                        start_time=step_start_time,
                        end_time=step_start_time,
                        duration=0,
                        error_message='步骤被跳过'
                    )
                    db.session.add(step_execution)
                    db.session.commit()
                    
                    # 继续下一个步骤
                    continue

                try:
                    # 发送步骤开始事件
                    socketio.emit('step_started', {
                        'execution_id': execution_id,
                        'step_index': i,
                        'step_description': step.get('description', step.get('action', f'步骤 {i+1}')),
                        'total_steps': len(steps)
                    }, room=client_sid)

                    # 执行步骤
                    result = execute_single_step(ai, step, mode, execution_id, i)

                    step_end_time = datetime.utcnow()
                    duration = int((step_end_time - step_start_time).total_seconds())

                    # 记录步骤执行结果
                    step_execution = StepExecution(
                        execution_id=execution_id,
                        step_index=i,
                        step_description=step.get('description', step.get('action', f'步骤 {i+1}')),
                        status='success' if result['success'] else 'failed',
                        start_time=step_start_time,
                        end_time=step_end_time,
                        duration=duration,
                        screenshot_path=result.get('screenshot_path'),
                        ai_confidence=result.get('confidence'),
                        ai_decision=json.dumps(result.get('ai_decision', {})),
                        error_message=result.get('error_message')
                    )

                    db.session.add(step_execution)

                    if result['success']:
                        steps_passed += 1
                        # 发送步骤成功事件
                        socketio.emit('step_completed', {
                            'execution_id': execution_id,
                            'step_index': i,
                            'status': 'success',
                            'duration': duration,
                            'screenshot': result.get('screenshot'),
                            'screenshot_path': result.get('screenshot_path'),  # 保持向后兼容
                            'total_steps': len(steps)
                        }, room=client_sid)
                    else:
                        steps_failed += 1
                        # 发送步骤失败事件
                        socketio.emit('step_completed', {
                            'execution_id': execution_id,
                            'step_index': i,
                            'status': 'failed',
                            'error_message': result.get('error_message'),
                            'duration': duration,
                            'screenshot': result.get('screenshot'),
                            'screenshot_path': result.get('screenshot_path'),  # 保持向后兼容
                            'total_steps': len(steps)
                        }, room=client_sid)

                        # 如果是无头模式，失败后停止执行；浏览器模式下继续执行
                        if mode == 'headless':
                            break

                    # 短暂延迟，避免操作过快
                    time.sleep(1)

                except Exception as e:
                    steps_failed += 1
                    # 记录步骤异常
                    step_execution = StepExecution(
                        execution_id=execution_id,
                        step_index=i,
                        step_description=step.get('description', step.get('action', f'步骤 {i+1}')),
                        status='failed',
                        start_time=step_start_time,
                        end_time=datetime.utcnow(),
                        error_message=str(e)
                    )
                    db.session.add(step_execution)

                    socketio.emit('step_completed', {
                        'execution_id': execution_id,
                        'step_index': i,
                        'status': 'failed',
                        'error_message': str(e),
                        'screenshot': None,
                        'screenshot_path': None,
                        'total_steps': len(steps)
                    }, room=client_sid)

                    if mode == 'headless':
                        break
        
            # 更新执行记录
            execution.end_time = datetime.utcnow()
            execution.duration = int((execution.end_time - execution.start_time).total_seconds())
            execution.steps_passed = steps_passed
            execution.steps_failed = steps_failed
            execution.status = 'success' if steps_failed == 0 else 'failed'

            db.session.commit()
        
            # 发送执行完成事件
            socketio.emit('execution_completed', {
                'execution_id': execution_id,
                'status': execution.status,
                'duration': execution.duration,
                'steps_passed': steps_passed,
                'steps_failed': steps_failed,
                'total_steps': len(steps)
            }, room=client_sid)

            # 清理AI资源
            try:
                ai.cleanup()
            except:
                pass
            
    except Exception as e:
        # 更新执行状态为失败
        # 确保app实例已创建
        if app is None:
            app, _ = init_app()
        
        with app.app_context():
            execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
            if execution:
                execution.status = 'failed'
                execution.end_time = datetime.utcnow()
                execution.error_message = str(e)
                db.session.commit()

        # 发送执行错误事件
        socketio.emit('execution_error', {
            'execution_id': execution_id,
            'message': f'执行过程中发生错误: {str(e)}'
        }, room=client_sid)

def execute_single_step(ai, step, mode, execution_id, step_index=0):
    """执行单个测试步骤 - 支持变量解析和输出捕获"""
    try:
        action = step.get('action')
        params = step.get('params', {})
        description = step.get('description', action)
        output_variable = step.get('output_variable')  # 新增：输出变量名

        result = {
            'success': False,
            'ai_decision': {'action': action, 'params': params},
            'confidence': 0.8 if AI_AVAILABLE else 0.5,
            'execution_details': {},
            'step_index': step_index,
            'step_name': description,
            'output_data': None  # 新增：存储输出数据
        }

        print(f"[执行] {description}")

        # 创建变量解析器
        try:
            from web_gui.services.variable_resolver import VariableResolverService
            resolver = VariableResolverService(execution_id)
            
            # 解析步骤参数中的变量引用
            resolved_params = resolver.resolve_step_parameters(params, step_index)
            print(f"[变量解析] 原始参数: {params}")
            print(f"[变量解析] 解析后参数: {resolved_params}")
            
        except Exception as e:
            print(f"[警告] 变量解析失败，使用原始参数: {e}")
            resolved_params = params
            resolver = None

        # 根据不同的操作类型执行相应的AI操作
        if action == 'goto' or action == 'navigate':
            url = resolved_params.get('url')
            if not url:
                raise ValueError("goto操作缺少url参数")
            ai.goto(url)
            result['success'] = True
            result['execution_details']['url'] = url

        elif action == 'ai_input' or action == 'aiInput':
            text = resolved_params.get('text')
            locate = resolved_params.get('locate')
            if not text or not locate:
                raise ValueError("ai_input操作缺少text或locate参数")
            ai.ai_input(text, locate)
            result['success'] = True
            result['execution_details']['text'] = text
            result['execution_details']['locate'] = locate

        elif action == 'ai_tap' or action == 'aiTap':
            prompt = resolved_params.get('prompt') or resolved_params.get('locate')
            if not prompt:
                raise ValueError("ai_tap操作缺少prompt或locate参数")
            ai.ai_tap(prompt)
            result['success'] = True
            result['execution_details']['prompt'] = prompt

        elif action == 'ai_assert' or action == 'aiAssert':
            prompt = resolved_params.get('prompt') or resolved_params.get('condition')
            if not prompt:
                raise ValueError("ai_assert操作缺少prompt或condition参数")
            ai.ai_assert(prompt)
            result['success'] = True
            result['execution_details']['assertion'] = prompt

        elif action == 'ai_wait_for' or action == 'aiWaitFor':
            prompt = resolved_params.get('prompt')
            timeout = resolved_params.get('timeout', 10000)
            if not prompt:
                raise ValueError("ai_wait_for操作缺少prompt参数")
            ai.ai_wait_for(prompt, timeout)
            result['success'] = True
            result['execution_details']['wait_for'] = prompt
            result['execution_details']['timeout'] = timeout

        elif action == 'ai_scroll':
            direction = resolved_params.get('direction', 'down')
            scroll_type = resolved_params.get('scroll_type', 'once')
            locate_prompt = resolved_params.get('locate_prompt')
            ai.ai_scroll(direction, scroll_type, locate_prompt)
            result['success'] = True
            result['execution_details']['direction'] = direction
            result['execution_details']['scroll_type'] = scroll_type

        # 新增：支持AI查询操作并捕获返回值
        elif action == 'aiQuery':
            # 支持两种参数格式：
            # 1. 新格式：schema = {"字段名": "字段描述, 数据类型"}
            # 2. 旧格式：query + dataDemand（向后兼容）
            schema = resolved_params.get('schema')
            query = resolved_params.get('query')
            data_demand = resolved_params.get('dataDemand')
            
            if not schema and not query:
                raise ValueError("aiQuery操作缺少schema或query参数")
            
            # 模拟aiQuery返回值（实际应调用AI引擎）
            if hasattr(ai, 'ai_query'):
                if schema:
                    output_data = ai.ai_query(schema=schema)
                else:
                    output_data = ai.ai_query(query, data_demand)
            else:
                # 模拟返回数据
                if schema:
                    output_data = _mock_ai_query_result_from_schema(schema)
                else:
                    output_data = _mock_ai_query_result(query, data_demand)
            
            result['success'] = True
            result['output_data'] = output_data
            result['execution_details']['schema'] = schema
            result['execution_details']['query'] = query
            result['execution_details']['data_demand'] = data_demand
            
            # 如果指定了输出变量，存储结果
            if output_variable and resolver:
                resolver.store_step_output(
                    variable_name=output_variable,
                    value=output_data,
                    step_index=step_index,
                    api_method='aiQuery',
                    api_params=resolved_params
                )
                print(f"[变量存储] {output_variable} = {output_data}")

        elif action == 'aiString':
            query = resolved_params.get('query')
            if not query:
                raise ValueError("aiString操作缺少query参数")
            
            # 模拟aiString返回值
            if hasattr(ai, 'ai_string'):
                output_data = ai.ai_string(query)
            else:
                output_data = _mock_ai_string_result(query)
            
            result['success'] = True
            result['output_data'] = output_data
            result['execution_details']['query'] = query
            
            # 存储输出变量
            if output_variable and resolver:
                resolver.store_step_output(
                    variable_name=output_variable,
                    value=output_data,
                    step_index=step_index,
                    api_method='aiString',
                    api_params=resolved_params
                )
                print(f"[变量存储] {output_variable} = {output_data}")

        elif action == 'aiAsk':
            query = resolved_params.get('query')
            if not query:
                raise ValueError("aiAsk操作缺少query参数")
            
            # 模拟aiAsk返回值
            if hasattr(ai, 'ai_ask'):
                output_data = ai.ai_ask(query)
            else:
                output_data = _mock_ai_ask_result(query)
            
            result['success'] = True
            result['output_data'] = output_data
            result['execution_details']['query'] = query
            
            # 存储输出变量
            if output_variable and resolver:
                resolver.store_step_output(
                    variable_name=output_variable,
                    value=output_data,
                    step_index=step_index,
                    api_method='aiAsk',
                    api_params=resolved_params
                )
                print(f"[变量存储] {output_variable} = {output_data}")

        elif action == 'evaluateJavaScript':
            script = resolved_params.get('script')
            if not script:
                raise ValueError("evaluateJavaScript操作缺少script参数")
            
            # 模拟JavaScript执行结果
            if hasattr(ai, 'evaluate_javascript'):
                output_data = ai.evaluate_javascript(script)
            else:
                output_data = _mock_javascript_result(script)
            
            result['success'] = True
            result['output_data'] = output_data
            result['execution_details']['script'] = script
            
            # 存储输出变量
            if output_variable and resolver:
                resolver.store_step_output(
                    variable_name=output_variable,
                    value=output_data,
                    step_index=step_index,
                    api_method='evaluateJavaScript',
                    api_params=resolved_params
                )
                print(f"[变量存储] {output_variable} = {output_data}")

        elif action == 'setKsyunCookie':
            # 设置金山云登录Cookie
            access_key = resolved_params.get('access_key') or resolved_params.get('accessKey')
            secret_key = resolved_params.get('secret_key') or resolved_params.get('secretKey') 
            region = resolved_params.get('region', 'cn-beijing-6')
            target_url = resolved_params.get('target_url') or resolved_params.get('targetUrl')
            
            # 从环境变量获取默认值（如果参数中没有提供）
            if not access_key:
                access_key = os.getenv('KSYUN_ACCESS_KEY')
            if not secret_key:
                secret_key = os.getenv('KSYUN_SECRET_KEY')
            if not region:
                region = os.getenv('KSYUN_REGION', 'cn-beijing-6')
                
            if not access_key or not secret_key:
                raise ValueError("金山云Access Key和Secret Key不能为空，请在参数中提供或设置环境变量KSYUN_ACCESS_KEY和KSYUN_SECRET_KEY")
            
            print(f"🔑 设置金山云Cookie - 区域: {region}")
            
            if hasattr(ai, 'set_ksyun_cookies'):
                # 使用真实AI引擎设置Cookie
                ai.set_ksyun_cookies(
                    access_key=access_key,
                    secret_key=secret_key,
                    region=region,
                    target_url=target_url
                )
            else:
                # 模拟实现
                print(f"[模拟] 设置金山云Cookie")
                print(f"[模拟] Access Key: {access_key[:8]}***")
                print(f"[模拟] 区域: {region}")
                if target_url:
                    print(f"[模拟] 跳转到: {target_url}")
                time.sleep(1)  # 模拟操作时间
            
            result['success'] = True
            result['execution_details']['access_key'] = access_key[:8] + '***'  # 部分隐藏
            result['execution_details']['region'] = region
            result['execution_details']['target_url'] = target_url

        elif action == 'setCookie' or action == 'setCookies':
            # 通用Cookie设置操作
            cookies = resolved_params.get('cookies')
            domain = resolved_params.get('domain')
            
            if not cookies or not isinstance(cookies, dict):
                raise ValueError("setCookie操作需要cookies参数，且必须是字典格式")
            
            print(f"🍪 设置{len(cookies)}个Cookie")
            if domain:
                print(f"   域名: {domain}")
                
            if hasattr(ai, 'set_cookies'):
                # 使用真实AI引擎设置Cookie
                ai.set_cookies(cookies, domain)
            else:
                # 模拟实现
                print(f"[模拟] 设置Cookie:")
                for name, value in cookies.items():
                    print(f"  {name}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
                time.sleep(0.5)
                
            result['success'] = True
            result['execution_details']['cookies_count'] = len(cookies)
            result['execution_details']['domain'] = domain

        else:
            raise ValueError(f'不支持的操作类型: {action}')

        # 截图
        timestamp = int(time.time())
        step_index = result.get('step_index', 0)  # 从result中获取步骤索引
        screenshot_filename = f"exec_{execution_id}_step_{step_index}_{timestamp}"

        try:
            # 调用AI引擎截图，传递文件名（不含扩展名）
            screenshot_path = ai.take_screenshot(screenshot_filename)
            # 返回详细的截图信息
            result['screenshot'] = {
                'path': f"/static/screenshots/{screenshot_filename}.png",
                'filename': f"{screenshot_filename}.png",
                'timestamp': timestamp,
                'step_index': step_index,
                'step_name': result.get('step_name', f'步骤 {step_index + 1}')
            }
            print(f"截图成功保存: {screenshot_path}")
        except Exception as e:
            print(f"截图失败: {e}")
            result['screenshot'] = None

        # 模拟AI置信度（真实环境中应该从AI引擎获取）
        if AI_AVAILABLE:
            result['confidence'] = 0.85 + (hash(str(params)) % 15) / 100  # 0.85-0.99
        else:
            result['confidence'] = 0.50 + (hash(str(params)) % 30) / 100  # 0.50-0.79

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"[错误] 步骤执行失败: {error_msg}")
        return {
            'success': False,
            'error_message': error_msg,
            'ai_decision': {'action': action, 'params': params, 'error': error_msg},
            'confidence': 0.0,
            'execution_details': {}
        }

def _mock_ai_query_result(query: str, data_demand: str = None) -> dict:
    """模拟aiQuery返回结果（旧格式）"""
    import json
    import re
    
    # 尝试解析dataDemand结构
    if data_demand:
        try:
            # 简单解析dataDemand格式，如 "{name: string, price: number}"
            if 'name' in data_demand and 'price' in data_demand:
                return {
                    'name': f'模拟商品名_{hash(query) % 100}',
                    'price': abs(hash(query) % 1000) + 99.99
                }
            elif 'title' in data_demand:
                return {'title': f'模拟标题_{hash(query) % 100}'}
            elif 'count' in data_demand:
                return {'count': abs(hash(query) % 50) + 1}
        except:
            pass
    
    # 默认返回结构
    return {
        'result': f'模拟查询结果: {query}',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'confidence': 0.85
    }

def _mock_ai_query_result_from_schema(schema: dict) -> dict:
    """根据schema格式模拟aiQuery返回结果"""
    result = {}
    
    for field_name, field_desc in schema.items():
        # 根据字段描述生成模拟数据
        field_desc_lower = field_desc.lower()
        
        if 'string' in field_desc_lower or '字符串' in field_desc_lower:
            if 'name' in field_name.lower() or '名称' in field_name or '姓名' in field_name:
                result[field_name] = f'模拟名称_{hash(field_name) % 100}'
            elif 'title' in field_name.lower() or '标题' in field_name:
                result[field_name] = f'模拟标题_{hash(field_name) % 100}'
            elif 'url' in field_name.lower() or '链接' in field_name:
                result[field_name] = f'https://example.com/page_{hash(field_name) % 100}'
            elif 'id' in field_name.lower():
                result[field_name] = f'id_{abs(hash(field_name) % 10000)}'
            else:
                result[field_name] = f'模拟文本_{hash(field_name) % 100}'
                
        elif 'number' in field_desc_lower or '数字' in field_desc_lower or 'int' in field_desc_lower:
            if 'price' in field_name.lower() or '价格' in field_name:
                result[field_name] = abs(hash(field_name) % 1000) + 99.99
            elif 'count' in field_name.lower() or '数量' in field_name:
                result[field_name] = abs(hash(field_name) % 100) + 1
            elif 'age' in field_name.lower() or '年龄' in field_name:
                result[field_name] = abs(hash(field_name) % 50) + 18
            else:
                result[field_name] = abs(hash(field_name) % 1000)
                
        elif 'boolean' in field_desc_lower or '布尔' in field_desc_lower or 'bool' in field_desc_lower:
            result[field_name] = hash(field_name) % 2 == 0
            
        elif 'array' in field_desc_lower or '数组' in field_desc_lower or 'list' in field_desc_lower:
            result[field_name] = [f'项目{i}_{hash(field_name) % 100}' for i in range(3)]
            
        else:
            # 默认返回字符串
            result[field_name] = f'模拟数据_{hash(field_name) % 100}'
    
    return result

def _mock_ai_string_result(query: str) -> str:
    """模拟aiString返回结果"""
    # 根据查询内容返回不同的模拟结果
    if '价格' in query or 'price' in query.lower():
        return f'¥{abs(hash(query) % 1000) + 99}'
    elif '标题' in query or 'title' in query.lower():
        return f'模拟页面标题_{hash(query) % 100}'
    elif '时间' in query or 'time' in query.lower():
        return time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return f'模拟字符串结果: {query}'

def _mock_ai_ask_result(query: str) -> str:
    """模拟aiAsk返回结果"""
    # 模拟AI分析结果
    responses = [
        f'根据当前页面内容，{query}的答案是：这是一个模拟的AI分析结果。',
        f'基于页面信息分析，{query}的结论是：模拟的智能回答内容。',
        f'通过AI理解，{query}的回应是：这是模拟生成的智能答案。'
    ]
    return responses[hash(query) % len(responses)]

def _mock_javascript_result(script: str) -> any:
    """模拟JavaScript执行结果"""
    # 根据脚本内容返回不同的模拟结果
    if 'window.location' in script:
        return {
            'url': 'https://example.com/current-page',
            'title': '模拟页面标题',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    elif 'document.title' in script:
        return '模拟页面标题'
    elif 'return' in script and '{' in script:
        # 返回对象的脚本
        return {
            'result': '模拟JavaScript执行结果',
            'script': script[:50] + '...' if len(script) > 50 else script,
            'timestamp': time.time()
        }
    else:
        return f'模拟脚本执行结果: {script[:30]}...'

# ==================== 初始化数据库 ====================

def init_database():
    """初始化数据库"""
    # 确保app实例已创建
    global app
    if app is None:
        app, _ = init_app()
    
    with app.app_context():
        try:
            # 验证数据库连接
            if not validate_database_connection():
                print("❌ 数据库连接失败")
                return False

            # 创建表
            db.create_all()
            print("✅ 数据库表创建完成")
            
            # 应用数据库优化
            try:
                from utils.db_optimization import create_database_indexes
                create_database_indexes(db)
                print("✅ 数据库索引优化完成")
            except ImportError:
                try:
                    from web_gui.utils.db_optimization import create_database_indexes
                    create_database_indexes(db)
                    print("✅ 数据库索引优化完成")
                except Exception as opt_e:
                    print(f"⚠️ 数据库优化失败: {opt_e}")

            # 创建默认模板
            create_default_templates()
            return True
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            return False

def create_default_templates():
    """创建默认测试模板"""
    try:
        # 检查是否已有模板
        if Template.query.count() > 0:
            return
        
        # 登录测试模板
        login_template = Template(
            name="用户登录测试",
            description="标准的用户登录流程测试",
            category="认证",
            steps_template=json.dumps([
                {
                    "action": "goto",
                    "params": {"url": "{{login_url}}"},
                    "description": "访问登录页面"
                },
                {
                    "action": "ai_input",
                    "params": {"text": "{{username}}", "locate": "用户名输入框"},
                    "description": "输入用户名"
                },
                {
                    "action": "ai_input",
                    "params": {"text": "{{password}}", "locate": "密码输入框"},
                    "description": "输入密码"
                },
                {
                    "action": "ai_tap",
                    "params": {"prompt": "登录按钮"},
                    "description": "点击登录按钮"
                },
                {
                    "action": "ai_assert",
                    "params": {"prompt": "登录成功，显示用户首页"},
                    "description": "验证登录成功"
                }
            ]),
            parameters=json.dumps({
                "login_url": {"type": "string", "description": "登录页面URL"},
                "username": {"type": "string", "description": "用户名"},
                "password": {"type": "string", "description": "密码"}
            }),
            created_by="system",
            is_public=True
        )
        
        db.session.add(login_template)
        db.session.commit()
        print("默认模板创建完成")
        
    except Exception as e:
        print(f"创建默认模板失败: {e}")

if __name__ == '__main__':
    print("🚀 启动增强版AI测试GUI系统...")
    print("📍 后端地址: http://localhost:5001")
    print("📍 API文档: http://localhost:5001/api/v1/")

    # 初始化应用实例
    app, socketio = init_app()
    
    # 初始化数据库
    if init_database():
        print("✅ 数据库初始化成功")
    else:
        print("❌ 数据库初始化失败")

    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5001,
        allow_unsafe_werkzeug=True
    )
