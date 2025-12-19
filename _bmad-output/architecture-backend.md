# Backend 架构文档

## 概述

Backend 是 AI4SE Toolbox 的服务端核心，基于 **Flask** 构建，集成 **LangGraph** AI 工作流引擎，提供：

- REST API 服务
- Web GUI (Jinja2 模板)
- LangGraph 智能体
- 数据库操作

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 主语言 |
| Flask | 2.3.3 | Web 框架 |
| Flask-SQLAlchemy | 3.0.5 | ORM |
| Flask-CORS | 4.0.0 | 跨域支持 |
| LangGraph | 1.0+ | 智能体工作流 |
| LangChain | 1.1+ | LLM 集成 |

## 目录结构

```
web_gui/
├── api/                        # API 路由模块
│   ├── __init__.py             # 路由注册入口
│   ├── testcases.py            # 测试用例 CRUD
│   ├── executions.py           # 执行历史
│   ├── templates.py            # 测试模板
│   ├── statistics.py           # 统计数据
│   ├── dashboard.py            # 仪表板
│   ├── midscene.py             # MidScene 集成
│   ├── requirements.py         # 需求分析 API
│   ├── ai_configs.py           # AI 配置管理
│   ├── database.py             # 数据库操作
│   ├── health.py               # 健康检查
│   └── user.py                 # 用户相关
├── services/                   # 业务服务层
│   ├── ai_service.py           # AI 服务封装
│   ├── ai_step_executor.py     # 步骤执行器
│   ├── execution_service.py    # 执行管理
│   ├── database_service.py     # 数据库服务
│   ├── requirements_ai_service.py  # 需求分析 AI
│   ├── variable_resolver_service.py # 变量解析
│   ├── query_optimizer.py      # 查询优化
│   └── langgraph_agents/       # LangGraph 智能体
│       ├── graph.py            # 图定义 (Alex/Lisa)
│       ├── nodes.py            # 节点实现
│       ├── state.py            # 状态定义
│       └── service.py          # 服务封装
├── models.py                   # 数据模型定义
├── config.py                   # 应用配置
├── database_config.py          # 数据库配置
├── templates/                  # Jinja2 模板 (Web GUI)
│   ├── base_layout.html        # 基础布局
│   ├── index.html              # 首页
│   ├── testcases.html          # 用例列表
│   ├── execution.html          # 执行页面
│   ├── requirements_analyzer.html  # 需求分析
│   └── ...
├── static/                     # 静态资源
│   ├── js/                     # JavaScript
│   └── css/                    # 样式
└── utils/                      # 工具函数
```

## 核心模块

### 1. API 路由层

采用 Flask Blueprint 模块化设计：

```python
# api/__init__.py
def register_api_routes(app):
    app.register_blueprint(api_bp)              # 主 API
    app.register_blueprint(requirements_bp)     # 需求分析
    app.register_blueprint(ai_configs_bp)       # AI 配置
```

**主要端点：**

| 模块 | 前缀 | 功能 |
|------|------|------|
| testcases | `/api/testcases` | 测试用例 CRUD |
| executions | `/api/executions` | 执行管理 |
| templates | `/api/templates` | 模板管理 |
| requirements | `/api/requirements` | 需求分析会话 |
| ai_configs | `/api/ai-configs` | AI 模型配置 |
| midscene | `/api/midscene` | MidScene 集成 |

### 2. LangGraph 智能体

基于 LangGraph 实现的对话式智能体：

```python
# services/langgraph_agents/graph.py

def create_alex_graph(checkpointer=None):
    """创建 Alex 需求分析师图"""
    builder = StateGraph(AssistantState)
    builder.add_node("chat", chat_node)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    return builder.compile(checkpointer=checkpointer)

def create_lisa_graph(checkpointer=None):
    """创建 Lisa 测试分析师图"""
    # 结构相同，提示词不同
    ...
```

**状态模型：**

```python
class AssistantState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    assistant_type: Literal["alex", "lisa"]
    current_stage: str
    project_name: Optional[str]
    consensus_content: Dict[str, Any]
    analysis_context: Dict[str, Any]
    should_extract_consensus: bool
    should_generate_document: bool
    is_turn_complete: bool
    error_message: Optional[str]
```

### 3. 数据模型

核心实体：

| 模型 | 描述 |
|------|------|
| `TestCase` | 测试用例（名称、步骤、优先级等） |
| `ExecutionHistory` | 执行历史（状态、时长、截图路径） |
| `StepExecution` | 步骤执行详情 |
| `Template` | 测试模板 |
| `ExecutionVariable` | 执行变量（跨步骤数据传递） |
| `RequirementsSession` | 需求分析会话 |
| `RequirementsMessage` | 需求消息 |
| `RequirementsAIConfig` | AI 配置 |
| `VariableReference` | 变量引用追踪 |

### 4. Web GUI

基于 Jinja2 模板的传统 Web 界面：

| 页面 | 功能 |
|------|------|
| `index.html` | 仪表板首页 |
| `testcases.html` | 测试用例列表 |
| `testcase_edit.html` | 用例编辑 |
| `execution.html` | 执行监控 |
| `reports.html` | 报告查看 |
| `requirements_analyzer.html` | 需求分析助手 |
| `config_management.html` | 配置管理 |
| `local_proxy.html` | 本地代理状态 |

## 服务层

### AI 服务 (`ai_service.py`)

封装 LLM 调用：

```python
class AIService:
    def __init__(self, config: RequirementsAIConfig):
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self.model = config.model_name
    
    def chat(self, messages: List[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content
```

### 执行服务 (`execution_service.py`)

管理测试执行生命周期：

```python
class ExecutionService:
    def start_execution(self, testcase_id: int, mode: str) -> str:
        # 创建执行记录
        # 调用 MidScene 服务
        # 返回 execution_id
        
    def get_execution_status(self, execution_id: str) -> dict:
        # 查询执行状态
        
    def stop_execution(self, execution_id: str) -> bool:
        # 停止执行
```

### 变量解析服务 (`variable_resolver_service.py`)

处理 `${variable}` 语法：

```python
class VariableResolverService:
    def resolve(self, text: str, context: dict) -> str:
        # 解析 ${variable} 和 ${variable.property} 语法
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}'
        return re.sub(pattern, lambda m: self._get_value(m.group(1), context), text)
```

## 配置管理

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///local.db` |
| `SECRET_KEY` | Flask 密钥 | - |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OPENAI_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `MIDSCENE_SERVER_URL` | MidScene 服务地址 | `http://localhost:3001` |

### 数据库配置

```python
# database_config.py
class DatabaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///local.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300
    }
```

## 部署

### 本地开发

```bash
python start.py
# 服务运行在 http://localhost:5001
```

### Docker

```yaml
# docker-compose.yml
services:
  web-app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://...
```

### Vercel (Serverless)

入口文件：`api/index.py`

```python
from flask import Flask
app = Flask(__name__)
# ... 路由注册
application = app
```

