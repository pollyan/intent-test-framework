---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
inputDocuments:
  - analysis/product-brief-lisa-langgraph-2025-12-19.md
  - index.md
  - project-overview.md
  - architecture-backend.md
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 3
workflowType: 'prd'
lastStep: 0
project_name: 'Lisa-LangGraph-Enhancement'
user_name: 'Anhui'
date: '2025-12-19'
---

# Product Requirements Document - Lisa-LangGraph-Enhancement

**Author:** Anhui
**Date:** 2025-12-19

---

## Executive Summary

**Lisa-LangGraph-Enhancement** 是一个针对 AI4SE Toolbox 中 Lisa Song 测试分析智能体的**对话架构重构**项目。

### 背景与动机

当前 Lisa 智能体采用"纯提示词驱动"模式，所有工作流逻辑（意图识别、阶段门控、质量评估等）都编码在 Bundle 提示词中，由 LLM 自主解释和执行。这种架构存在两个核心问题：

1. **工作流遵从性不稳定** - LLM 对指令的遵从依赖于模型"自觉"，可能跳过步骤或忽略协议
2. **调试困难** - 系统对开发者是"黑盒"，无法观测中间状态，出问题时只能看输入输出

### 解决方案

将 Lisa v5.0 提示词中的结构化逻辑迁移到 **LangGraph 图驱动架构**，通过代码级别的图结构强制执行工作流。核心改变包括：

- **图结构强制执行** - 节点顺序由代码控制，LLM 无法跳过
- **条件边实现门控** - 阶段转换由代码级别的检查函数控制
- **显式状态管理** - 每个节点的输入输出都可追踪、可调试
- **模块化节点设计** - 每个节点独立，可单独测试和记录日志

### What Makes This Special

本项目的独特价值在于：

1. **从"自觉"到"强制"** - 工作流遵从性不再依赖 LLM 的解释，而是由代码结构保证
2. **从"黑盒"到"透明"** - 开发者可以清晰追踪每个节点的执行状态
3. **Lisa 专属扩展** - 独立于 Alex 智能体，不影响现有功能
4. **渐进式迁移** - MVP 聚焦核心工作流 A，后续可逐步扩展

---

## Project Classification

| 维度 | 分类 |
|------|------|
| **Technical Type** | developer_tool |
| **Domain** | scientific (AI/ML - LLM 应用开发) |
| **Complexity** | medium |
| **Project Context** | Brownfield - 扩展现有对话架构，专门针对 Lisa |

### 技术上下文

- **现有架构**: `START → chat_node → END` (纯提示词驱动)
- **目标架构**: `START → intent_recognition → [Workflow A Subgraph] → END` (图驱动)
- **关键约束**: 保持 Alex 智能体现有功能不变，为 Lisa 创建独立扩展模块

---

## Success Criteria

*技术改造项目，验收标准以功能实现为准。详见 MVP Scope 章节。*

---

## User Journeys

*技术改造项目，跳过用户旅程定义。开发者体验详见 Product Brief 中的 User Journey 章节。*

---

## Functional Requirements

### 1. 状态管理 (State Management)

- **FR1**: 系统可以定义 Lisa 专用的状态模式（LisaState），独立于 Alex 的 AssistantState
- **FR2**: 系统可以跟踪当前工作流阶段（intent, A1, A2, A3, A4, done）
- **FR3**: 系统可以存储和更新用户意图识别结果
- **FR4**: 系统可以存储工作流 A 各子阶段的产出物（需求框架、共识基线、测试策略蓝图、测试用例集）
- **FR5**: 系统可以维护门控通过状态（gate_passed）
- **FR6**: 系统可以通过 add_messages reducer 自动追加对话历史

### 2. 意图识别与路由 (Intent Recognition & Routing)

- **FR7**: 系统可以分析用户首次输入，识别其任务意图
- **FR8**: 系统可以将意图映射到预定义的工作流类型（A-F）
- **FR9**: 系统可以在高置信度时直接路由到对应工作流
- **FR10**: 系统可以在低置信度时触发意图澄清流程
- **FR11**: 系统可以通过条件边（Conditional Edge）实现路由分发

### 3. 工作流 A - 需求澄清子阶段 (Workflow A - Phase A1)

- **FR12**: A1 节点可以加载 Lisa v5.0 的 Persona/Style/Principles 作为 System Prompt
- **FR13**: A1 节点可以生成需求分析框架（使用思维导图等可视化技术）
- **FR14**: A1 节点可以基于框架启动需求澄清讨论
- **FR15**: A1 节点可以输出《需求澄清与可测试性分析清单》

### 4. 工作流 A - 风险分析子阶段 (Workflow A - Phase A2)

- **FR16**: A2 节点可以基于已澄清需求识别潜在风险
- **FR17**: A2 节点可以选择并应用风险分析技术（如 FMEA）
- **FR18**: A2 节点可以输出《综合测试策略蓝图》

### 5. 工作流 A - 测试设计子阶段 (Workflow A - Phase A3)

- **FR19**: A3 节点可以遍历策略蓝图中的各个模块
- **FR20**: A3 节点可以为每个模块选择适当的测试设计技术
- **FR21**: A3 节点可以生成具体的测试用例集

### 6. 工作流 A - 评审交付子阶段 (Workflow A - Phase A4)

- **FR22**: A4 节点可以汇总所有子阶段产出物
- **FR23**: A4 节点可以生成最终的《测试设计文档》

### 7. 阶段门控 (Phase Gating)

- **FR24**: 系统可以在每个子阶段结束时执行门控检查
- **FR25**: 门控检查可以验证用户是否确认了当前阶段的产出物
- **FR26**: 门控通过后，系统可以自动转换到下一个子阶段
- **FR27**: 门控未通过时，系统可以保持在当前阶段等待用户确认

### 8. 输出格式化 (Output Formatting)

- **FR28**: 每个节点可以按照结构化响应模板格式化输出
- **FR29**: 输出可以包含任务进展概览（Markdown checklist）
- **FR30**: 输出可以在分隔线后包含核心交互内容

### 9. 架构约束 (Architecture Constraints)

- **FR31**: Lisa 扩展模块可以独立部署，不影响 Alex 智能体
- **FR32**: 共享基础设施（如 service.py）可以同时支持 Alex 和 Lisa
- **FR33**: 系统可以通过 assistant_type 参数区分不同智能体的图结构

---

## Non-Functional Requirements

*技术改造项目（Demo 级别），简化非功能需求：*

- **NFR1**: 每个节点执行应有日志记录，便于调试
- **NFR2**: 节点执行错误应优雅处理，返回错误信息给用户
- **NFR3**: 代码应遵循现有项目的编码规范和目录结构

---

## MVP Scope

### 第一阶段迁移内容

| 模块 | 功能 | 对应提示词章节 | 优先级 |
|------|------|----------------|--------|
| **State Schema** | Lisa 专用状态定义 | 新增 | P0 |
| **System Prompt** | Persona/Style/Principles | 1.1-1.3 | P0 |
| **意图识别节点** | intent_recognition + 路由 | 4.1 | P0 |
| **工作流 A 子图** | A1→A2→A3→A4 | 4.2 | P0 |
| **阶段门控** | gate_check 条件边 | 2.5 | P0 |
| **输出格式化** | 结构化响应模板 | 3.1 | P1 |

### 文件结构规划

```
web_gui/services/langgraph_agents/
├── __init__.py              # 更新导出
├── state.py                 # 保持不变（Alex 使用）
├── graph.py                 # 更新路由逻辑
├── nodes.py                 # 保持不变（Alex 使用）
├── service.py               # 保持不变（共享服务）
│
└── lisa_v2/                 # 🆕 Lisa 专属扩展
    ├── __init__.py
    ├── state.py             # LisaState 定义
    ├── graph.py             # Lisa 图结构
    ├── nodes/
    │   ├── __init__.py
    │   ├── intent_recognition.py
    │   ├── a1_clarification.py
    │   ├── a2_risk_analysis.py
    │   ├── a3_test_design.py
    │   └── a4_review.py
    ├── prompts/
    │   └── system_prompt.py  # v5.0 Persona/Style/Principles
    └── utils/
        └── gate_check.py     # 门控检查函数
```

### 暂不实现（后续阶段）

| 阶段 | 内容 | 原因 |
|------|------|------|
| 第二阶段 | 内部质量驱动协议 (2.1) | 复杂度高 |
| 第二阶段 | 全景-聚焦交互协议 (2.3) | 依赖状态管理完善 |
| 第三阶段 | 工具调用协议 (2.4) | 需要 Tool Calling 集成 |
| 第三阶段 | 用户命令处理 (5.1) | 非核心功能 |
| 第三阶段 | 工作流 B-F | 先验证 A 的架构 |

---

## Reference Documents

- **Product Brief**: `_bmad-output/analysis/product-brief-lisa-langgraph-2025-12-19.md`
- **Lisa v5.0 提示词**: `intelligent-requirements-analyzer/dist/testmaster-song-bundlev5.0.md`
- **现有 LangGraph 代码**: `web_gui/services/langgraph_agents/`
- **项目架构文档**: `_bmad-output/architecture-backend.md`

---

*PRD 完成于 2025-12-19*

