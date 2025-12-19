# AI4SE Toolbox - 项目概述

## 📋 项目简介

AI4SE Toolbox 是一个 **AI 驱动的软件工程工具集**，专注于：

1. **智能测试用例管理** - 创建、执行、追踪测试用例
2. **AI 辅助需求分析** - 通过对话式交互澄清和提取需求
3. **浏览器自动化测试** - 基于 AI 视觉的端到端测试执行

## 🎯 核心价值

| 价值主张 | 描述 |
|---------|------|
| **效率提升** | 从"小时级"到"分钟级"的测试用例设计 |
| **深度洞察** | 通过 BVA/EP 方法论自动识别边界值与异常场景 |
| **人机协同** | AI 分析 + 人工审批，确保测试方向正确 |
| **智能执行** | AI 视觉驱动的浏览器自动化，无需维护脆弱的选择器 |

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户环境（本地）                         │
│  ┌─────────────────┐        ┌─────────────────────────────┐ │
│  │  Local Proxy    │◄──────►│       用户浏览器             │ │
│  │  (MidSceneJS)   │  控制   │  (Playwright/Chromium)      │ │
│  │  Port: 3001     │        │                             │ │
│  └────────┬────────┘        └─────────────────────────────┘ │
│           │ HTTP/WebSocket                                   │
└───────────┼─────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│                    云端/服务器环境                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Backend (Flask)                         │  │
│  │                  Port: 5001                              │  │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────────┐ │  │
│  │  │ REST API   │ │ LangGraph  │ │ Web GUI              │ │  │
│  │  │ /api/*     │ │ Agents     │ │ (Jinja2 Templates)   │ │  │
│  │  └────────────┘ └────────────┘ └──────────────────────┘ │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                             │                                  │
│                             ▼                                  │
│                  ┌─────────────────────┐                      │
│                  │   PostgreSQL /      │                      │
│                  │   SQLite            │                      │
│                  └─────────────────────┘                      │
└───────────────────────────────────────────────────────────────┘
```

## 📁 项目组成

| Part ID | 类型 | 描述 | 根路径 |
|---------|------|------|--------|
| `backend` | Backend API + Web GUI | Flask 服务端，提供 REST API、LangGraph 智能体、Web 界面 | `web_gui/` |
| `local-proxy` | CLI/Agent | 本地浏览器控制代理，基于 MidSceneJS + Playwright | `/` (root) |

## 🛠 技术栈

### Backend (Python)

| 技术 | 版本 | 用途 |
|------|------|------|
| Flask | 2.3.3 | Web 框架 |
| Flask-SQLAlchemy | 3.0.5 | ORM |
| LangGraph | 1.0+ | AI 工作流编排 |
| LangChain | 1.1+ | LLM 集成 |
| PostgreSQL / SQLite | - | 数据持久化 |

### Local Proxy (Node.js)

| 技术 | 版本 | 用途 |
|------|------|------|
| Express | 4.21 | HTTP 服务 |
| Playwright | 1.57 | 浏览器自动化 |
| MidSceneJS | 0.30 | AI 视觉驱动 |
| Socket.IO | 4.7 | 实时通信 |

## 🤖 核心 AI 智能体

### Alex - 需求分析师
- **职责**: 需求澄清、共识提取、PRD 生成
- **工作流**: `START → chat → END` (纯提示词驱动)
- **阶段**: initial → clarification → consensus → documentation

### Lisa - 测试分析师
- **职责**: 测试策略规划、用例设计
- **工作流**: `START → chat → END` (纯提示词驱动)
- **阶段**: initial → analysis → design → documentation

## 📊 核心功能模块

### 1. 测试用例管理
- CRUD 操作
- 分类、优先级、标签管理
- 执行历史追踪
- 模板系统

### 2. 测试执行引擎
- 基于 MidSceneJS 的 AI 视觉操作
- 支持 headless 和可视化模式
- 变量解析和跨步骤数据传递
- 实时截图和状态同步

### 3. 需求分析助手
- 对话式需求澄清
- 智能共识提取
- 多配置 AI 模型支持

## 🚀 快速开始

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 安装前端依赖
npm install

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 OPENAI_API_KEY 等

# 4. 启动服务
python start.py           # 启动后端 (Port 5001)
node midscene_server.js   # 启动本地代理 (Port 3001)
```

## 📚 相关文档

- [Backend 架构](./architecture-backend.md)
- [Local Proxy 架构](./architecture-local-proxy.md)
- [API 接口文档](./api-contracts.md)
- [数据模型](./data-models.md)
- [开发指南](./development-guide.md)

## 📖 参考资料

- [PRD 产品需求文档](./archive/PRD.md) - TestGen Agent 的原始需求
- [智能需求分析器](../intelligent-requirements-analyzer/README.md) - BMAD-METHOD 框架说明

