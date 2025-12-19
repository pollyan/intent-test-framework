# 开发指南

## 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | Backend 运行环境 |
| Node.js | 18+ | Local Proxy |
| PostgreSQL | 12+ | 生产数据库 |
| Git | 2.0+ | 版本控制 |

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd intent-test-framework
```

### 2. Backend 环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置必要配置
```

### 3. Local Proxy 环境

```bash
# 安装 Node.js 依赖
npm install

# 安装 Playwright 浏览器
npx playwright install chromium
```

### 4. 启动服务

```bash
# 终端 1: Backend
python start.py

# 终端 2: Local Proxy
node midscene_server.js
```

### 5. 访问应用

| 服务 | 地址 |
|------|------|
| Web GUI | http://localhost:5001 |
| Backend API | http://localhost:5001/api |
| Local Proxy | http://localhost:3001 |

## 环境变量

### Backend

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///local.db` |
| `SECRET_KEY` | Flask 密钥 | - |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OPENAI_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `MIDSCENE_SERVER_URL` | Local Proxy 地址 | `http://localhost:3001` |

### Local Proxy

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `PORT` | 服务端口 | `3001` |
| `OPENAI_API_KEY` | AI 模型密钥 | - |
| `OPENAI_BASE_URL` | AI API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `MIDSCENE_MODEL_NAME` | 模型名称 | `qwen-vl-max-latest` |
| `MAIN_APP_URL` | Backend API | `http://localhost:5001/api` |
| `HEADLESS` | 无头模式 | `true` |

## 项目结构

```
intent-test-framework/
├── web_gui/              # Backend 源码
│   ├── api/              # API 路由
│   ├── services/         # 业务服务
│   ├── models.py         # 数据模型
│   ├── templates/        # Jinja2 模板
│   └── static/           # 静态资源
├── midscene_server.js    # Local Proxy 入口
├── midscene_framework/   # Python 辅助框架
├── tests/                # 测试代码
├── scripts/              # 工具脚本
├── migrations/           # 数据库迁移
├── assistant-bundles/    # AI 助手提示词
├── intelligent-requirements-analyzer/  # 需求分析框架
├── _bmad/                # BMAD 方法论资源
└── _bmad-output/         # 文档输出目录
```

## 开发流程

### 添加新 API

1. 在 `web_gui/api/` 创建模块
2. 使用 Blueprint 注册路由
3. 在 `__init__.py` 注册 Blueprint

```python
# web_gui/api/new_module.py
from flask import Blueprint, jsonify

new_module_bp = Blueprint('new_module', __name__, url_prefix='/api/new-module')

@new_module_bp.route('/', methods=['GET'])
def list_items():
    return jsonify({'items': []})

# web_gui/api/__init__.py
def register_api_routes(app):
    from .new_module import new_module_bp
    app.register_blueprint(new_module_bp)
```

### 添加数据模型

1. 在 `models.py` 定义模型
2. 创建迁移脚本
3. 执行迁移

```python
# web_gui/models.py
class NewModel(db.Model):
    __tablename__ = "new_models"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
```

```bash
# 创建迁移
alembic revision --autogenerate -m "Add NewModel"

# 执行迁移
alembic upgrade head
```

### 添加 LangGraph 智能体

1. 在 `services/langgraph_agents/` 添加配置
2. 定义 State、Nodes、Graph

```python
# services/langgraph_agents/graph.py
def create_new_agent_graph(checkpointer=None):
    builder = StateGraph(AssistantState)
    builder.add_node("process", process_node)
    builder.add_edge(START, "process")
    builder.add_edge("process", END)
    return builder.compile(checkpointer=checkpointer)
```

### 添加 Local Proxy 步骤类型

1. 在 `midscene_server.js` 的 `executeStep` 函数中添加 case
2. 更新 `normalizeStepType` 映射

```javascript
// midscene_server.js
case 'new_step_type':
    const param = params.param;
    await agent.someMethod(param);
    logMessage(executionId, 'info', `执行: ${param}`);
    break;
```

## 测试

### Backend 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/api/test_testcases.py

# 带覆盖率
pytest --cov=web_gui
```

### Local Proxy 测试

```bash
# 运行 Jest 测试
npm run test:proxy

# 监听模式
npm run test:proxy:watch
```

## 调试

### Backend 调试

VS Code 配置：

```json
{
  "name": "Python: Flask",
  "type": "python",
  "request": "launch",
  "module": "flask",
  "env": {"FLASK_APP": "api.index", "FLASK_DEBUG": "1"},
  "args": ["run", "--host=0.0.0.0", "--port=5001"]
}
```

### Local Proxy 调试

```bash
# 启用调试日志
DEBUG=midscene:* node midscene_server.js

# 可视化模式（慢动作）
HEADLESS=false SLOW_MO=500 node midscene_server.js
```

## 代码规范

### Python

```bash
# 格式化
black web_gui/

# 检查
flake8 web_gui/
```

### JavaScript

```bash
# 检查
npm run lint
```

## 数据库迁移

```bash
# 查看当前版本
alembic current

# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看历史
alembic history
```

## Docker 部署

```bash
# 构建镜像
docker build -t ai4se-toolbox .

# 运行
docker run -p 5001:5001 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-xxx \
  ai4se-toolbox
```

## 常见问题

### Q: MidScene 报错 "AI service unavailable"

1. 检查 `OPENAI_API_KEY` 是否设置
2. 检查网络是否能访问 API
3. 检查 API 配额

### Q: 浏览器启动失败

```bash
# 安装浏览器
npx playwright install chromium

# 安装系统依赖
npx playwright install-deps
```

### Q: 数据库连接失败

1. 检查 `DATABASE_URL` 格式
2. 确认数据库服务已启动
3. 检查防火墙设置

### Q: 步骤执行超时

调整超时设置：

```json
{
  "timeout_settings": {
    "page_timeout": 60000,
    "action_timeout": 60000,
    "navigation_timeout": 60000
  }
}
```

