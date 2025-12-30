# AI4SE 项目文档

> **文档生成日期**: 2025-12-30
> **扫描模式**: 穷尽扫描 (Exhaustive Scan)
> **文档语言**: 中文

---

## 项目概述

AI4SE 是一个模块化的软件工程辅助工具集，采用模块化单体 (Modular Monorepo) 架构，包含以下核心功能：

- **AI 智能体** - 基于 Google ADK 的对话式需求分析和测试策略规划
- **意图测试工具** - AI 驱动的浏览器自动化测试框架

---

## 技术栈

| 分类 | 技术 | 版本 |
|---|---|---|
| **后端语言** | Python | 3.11+ |
| **后端框架** | Flask | ≥2.0.0 |
| **AI 框架** | Google ADK | ≥1.2.1 |
| **数据库** | PostgreSQL | 15 |
| **ORM** | Flask-SQLAlchemy | ≥3.0.0 |
| **前端** | Jinja2 + 原生 JavaScript | - |
| **浏览器自动化** | Playwright + MidSceneJS | 1.57.0 / 0.30.9 |
| **运行时** | Node.js | 20+ |
| **容器化** | Docker Compose | 3.8 |
| **反向代理** | Nginx Alpine | - |

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                     Nginx Gateway (:80)                      │
│                   统一入口 + 反向代理                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌───────────────┐ ┌─────────────┐ ┌──────────────┐
│ /intent-tester│ │  /ai-agents │ │ 静态资源      │
│    (:5001)    │ │   (:5002)   │ │ /static      │
└───────┬───────┘ └──────┬──────┘ └──────────────┘
        │                │
        └────────┬───────┘
                 │
        ┌────────▼────────┐
        │   PostgreSQL    │
        │     (:5432)     │
        └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           MidScene Server (客户端本地 :3001)                  │
│           ↓ WebSocket/HTTP → 驱动本地浏览器                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块详解

### 1. AI 智能体 (`tools/ai-agents`)

**类型**: Backend (Python/Flask)  
**端口**: 5002  
**关键技术**: Google ADK, LiteLLM

#### 核心组件

| 文件 | 说明 |
|---|---|
| `backend/app.py` | Flask 应用入口，注册蓝图和路由 |
| `backend/agents/service.py` | `AdkAssistantService` 服务类，支持流式/非流式消息处理 |
| `backend/agents/alex/` | Alex 需求分析师智能体 |
| `backend/agents/lisa/` | Lisa 测试专家智能体 |
| `backend/api/requirements.py` | 会话管理 API (~30 个端点) |

#### 数据模型

| 模型 | 表名 | 说明 |
|---|---|---|
| `RequirementsSession` | `requirements_sessions` | 需求分析会话 |
| `RequirementsMessage` | `requirements_messages` | 会话消息记录 |
| `RequirementsAIConfig` | `requirements_ai_configs` | AI 服务配置 (API Key, Base URL 等) |

#### API 端点 (主要)

```
/ai-agents/api/requirements/sessions          POST   创建会话
/ai-agents/api/requirements/sessions/<id>     GET    获取会话
/ai-agents/api/requirements/sessions/<id>/messages      GET    获取消息
/ai-agents/api/requirements/sessions/<id>/messages      POST   发送消息
/ai-agents/api/requirements/sessions/<id>/messages/stream  POST  流式消息 (SSE)
/ai-agents/api/requirements/assistants        GET    获取助手列表
```

---

### 2. 意图测试工具 (`tools/intent-tester`)

**类型**: Web (Python/Flask + Node.js)  
**端口**: 5001  
**关键技术**: Playwright, MidSceneJS

#### 核心组件

| 目录/文件 | 说明 |
|---|---|
| `backend/app.py` | Flask 应用入口 |
| `backend/api/testcases.py` | 测试用例 CRUD API |
| `backend/api/executions.py` | 测试执行管理 API |
| `backend/api/midscene.py` | MidScene Server 通信 API |
| `browser-automation/midscene_server.js` | **MidScene Server** - 客户端代理服务器 (2447 行) |
| `midscene_framework/` | MidScene 测试框架封装 |

#### MidScene Server 架构说明

> **重要**: MidScene Server 是一个运行在**客户端本地**的代理服务器，而非服务端组件。

```
用户本地机器
┌──────────────────────────────────────────┐
│  ┌─────────────────┐  ┌───────────────┐  │
│  │ MidScene Server │◀─│ Intent Tester │  │
│  │    (:3001)      │  │  Web UI       │  │
│  └────────┬────────┘  └───────────────┘  │
│           │ Playwright                    │
│           ▼                               │
│  ┌─────────────────┐                      │
│  │  Chrome 浏览器   │                      │
│  └─────────────────┘                      │
└──────────────────────────────────────────┘
                 │
                 │ WebSocket / HTTP
                 ▼
┌──────────────────────────────────────────┐
│           云端 Intent Tester             │
│           (AI4SE 服务器)                 │
└──────────────────────────────────────────┘
```

**工作流程**:
1. 用户在 Web 界面创建/运行测试用例
2. 服务端发送测试步骤到 MidScene Server (通过 WebSocket)
3. MidScene Server 使用 Playwright 驱动本地 Chrome
4. MidSceneJS AI 识别页面元素并执行操作
5. 执行结果实时回传到服务端

#### 数据模型

| 模型 | 表名 | 说明 |
|---|---|---|
| `TestCase` | `test_cases` | 测试用例 |
| `ExecutionHistory` | `execution_history` | 执行历史 |
| `StepExecution` | `step_executions` | 步骤执行详情 |
| `Template` | `templates` | 测试模板 |
| `ExecutionVariable` | `execution_variables` | 执行变量 |
| `VariableReference` | `variable_references` | 变量引用追踪 |

#### API 端点 (主要)

```
/intent-tester/api/testcases                  GET    获取测试用例列表
/intent-tester/api/testcases                  POST   创建测试用例
/intent-tester/api/testcases/<id>             GET    获取测试用例详情
/intent-tester/api/testcases/<id>             PUT    更新测试用例
/intent-tester/api/testcases/<id>             DELETE 删除测试用例
/intent-tester/api/executions                 GET    获取执行历史
/intent-tester/api/executions/<id>/start      POST   启动执行
/intent-tester/api/executions/<id>/stop       POST   停止执行
/intent-tester/api/midscene/execution-start   POST   开始执行通知 (来自 MidScene Server)
/intent-tester/api/midscene/execution-result  POST   执行结果通知 (来自 MidScene Server)
```

---

### 3. 共享模块 (`tools/shared`)

**类型**: Library (Python)

| 文件 | 说明 |
|---|---|
| `config/__init__.py` | `SharedConfig` 类，管理环境变量 (SECRET_KEY, LANGCHAIN_*) |
| `database/__init__.py` | `get_database_config()` 函数，提供数据库连接配置 |

---

### 4. 共享前端 (`tools/frontend`)

**类型**: Web (HTML/CSS/JS)

统一入口页面和共享静态资源，由 Nginx 直接提供服务。

| 路径 | 说明 |
|---|---|
| `public/index.html` | 主页 |
| `public/static/` | 共享 CSS/JS/图片资源 |

---

## 部署架构

### 本地开发环境

```bash
# 使用专用部署脚本
./scripts/dev/deploy-dev.sh        # 增量部署 (默认)
./scripts/dev/deploy-dev.sh full   # 完全重建
```

**配置文件**: `docker-compose.dev.yml`

### 生产环境 (腾讯云)

通过 GitHub Actions 自动部署:

1. `push` 到 `main/master` 触发测试
2. `workflow_dispatch` 手动触发部署
3. 文件通过 rsync 传输到服务器
4. 执行 `scripts/ci/deploy.sh production`

**配置文件**: `docker-compose.prod.yml`

---

## 目录结构

```
AI4SE/
├── docker-compose.dev.yml     # 本地开发 Docker 配置
├── docker-compose.prod.yml    # 生产环境 Docker 配置
├── nginx/
│   └── nginx.conf             # Nginx 反向代理配置
├── scripts/
│   ├── ci/                    # CI/CD 脚本
│   │   ├── deploy.sh          # 统一部署脚本
│   │   └── build-proxy-package.js  # 代理包构建
│   └── dev/
│       └── deploy-dev.sh      # 本地开发部署脚本
├── tools/
│   ├── ai-agents/             # AI 智能体模块
│   │   ├── backend/           # Flask 后端
│   │   ├── frontend/          # 前端模板
│   │   ├── docker/            # Dockerfile
│   │   └── requirements.txt
│   ├── intent-tester/         # 意图测试工具模块
│   │   ├── backend/           # Flask 后端
│   │   ├── frontend/          # 前端模板
│   │   ├── browser-automation/  # MidScene Server (客户端代理)
│   │   ├── midscene_framework/  # MidScene 封装
│   │   ├── docker/            # Dockerfile
│   │   ├── package.json       # Node.js 依赖
│   │   └── requirements.txt
│   ├── frontend/              # 共享前端资源
│   └── shared/                # 共享 Python 模块
├── docs/                      # 项目文档
└── .github/workflows/         # GitHub Actions
```

---

## 快速开始

### 前置条件

- Docker & Docker Compose
- Node.js 20+ (用于本地 MidScene Server)
- `.env` 文件配置

### 环境变量

```bash
# .env 示例
DB_USER=ai4se_user
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 启动服务

```bash
# 1. 启动服务端 (Docker)
./scripts/dev/deploy-dev.sh

# 2. 启动本地 MidScene Server (在本地机器上)
cd tools/intent-tester
npm install
npm start
```

### 访问地址

| 服务 | URL |
|---|---|
| 主页 | http://localhost |
| AI 智能体 | http://localhost/ai-agents/ |
| 意图测试工具 | http://localhost/intent-tester/ |
| MidScene Server | http://localhost:3001 (本地) |

---

## 相关文档

### 项目文档

- [数据模型文档](./data-models.md) - 完整的数据库表结构和 ER 图
- [API 接口文档](./api-reference.md) - REST API 端点参考

### 外部资源

- [Google ADK 文档](https://github.com/google/adk)
- [MidSceneJS 文档](https://midscenejs.com)
- [Playwright 文档](https://playwright.dev)
