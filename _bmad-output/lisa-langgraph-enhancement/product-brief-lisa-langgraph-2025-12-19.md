---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/index.md
  - _bmad-output/project-overview.md
  - _bmad-output/architecture-backend.md
  - intelligent-requirements-analyzer/dist/testmaster-song-bundlev5.0.md
  - web_gui/services/langgraph_agents/state.py
  - web_gui/services/langgraph_agents/graph.py
  - web_gui/services/langgraph_agents/nodes.py
workflowType: 'product-brief'
lastStep: 0
project_name: 'Lisa-LangGraph-Enhancement'
user_name: 'Anhui'
date: '2025-12-19'
---

# Product Brief: Lisa-LangGraph-Enhancement

**Date:** 2025-12-19
**Author:** Anhui

---

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

**Lisa-LangGraph-Enhancement** 是一个针对 AI4SE Toolbox 测试分析智能体（Lisa Song）的技术架构重构项目。

当前 Lisa 智能体采用"纯提示词驱动"模式（START → chat → END），所有分析逻辑都打包在 Bundle 提示词中由 LLM 自主执行。这种架构存在两个核心问题：**工作流遵从性不稳定**（LLM 可能跳过步骤或忽略协议）和**调试困难**（状态不透明，无法追踪中间过程）。

本项目将 Lisa v5.0 提示词中的结构化逻辑迁移到 **LangGraph 图驱动架构**，通过代码级别的图结构强制执行工作流，显著提升系统的可靠性和可维护性。MVP 聚焦于意图识别路由和工作流 A（新需求/功能测试设计）的完整实现。

---

## Core Vision

### Problem Statement

当前 Lisa 测试分析智能体采用"纯提示词驱动"架构，即所有工作流逻辑（意图识别、阶段门控、质量评估等）都编码在提示词中，由 LLM 自主解释和执行。

这种架构导致：
1. **执行不稳定** - LLM 对指令和工作流的遵从性依赖于模型"自觉"，可能跳过步骤、忽略协议
2. **调试困难** - 系统对开发者是"黑盒"，无法观测 LLM 当前处于哪个阶段，出问题时只能看输入输出

### Problem Impact

| 受影响群体 | 影响描述 |
|------------|----------|
| **一线测试人员** | 相同输入可能得到不一致的输出，需要多次重试 |
| **维护开发者** | 无法有效调试问题，定位故障困难 |
| **系统整体** | 随着提示词复杂度增加，不稳定性会加剧 |

### Why Existing Solutions Fall Short

当前的"纯提示词驱动"架构（`START → chat_node → END`）虽然实现简单，但存在根本性的局限：

1. **工作流遵从靠"自觉"** - 提示词定义了 8 个系统协议（阶段门控、质量驱动等），但 LLM 是否遵守完全不可控
2. **状态隐藏在 LLM 内部** - 无法从外部观测当前阶段、已完成的步骤、待处理的议题
3. **调试只能靠猜测** - 出问题时，开发者只能通过对比输入输出来推测问题原因

### Proposed Solution

将 Lisa v5.0 提示词的结构化逻辑迁移到 **LangGraph 图驱动架构**：

```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph 图驱动                      │
├─────────────────────────────────────────────────────────┤
│  START                                                   │
│    │                                                     │
│    ▼                                                     │
│  [intent_recognition] ──条件边──► 工作流 B-F (待实现)    │
│    │                                                     │
│    ▼ workflow="A"                                        │
│  ┌─────────────────────────────────────┐                │
│  │         Workflow A Subgraph         │                │
│  │  [A1] ──门控──► [A2] ──门控──► [A3] ──门控──► [A4]   │
│  └─────────────────────────────────────┘                │
│    │                                                     │
│    ▼                                                     │
│  END                                                     │
└─────────────────────────────────────────────────────────┘
```

**核心改变：**
- **图结构强制执行** - 节点顺序由代码控制，LLM 无法跳过
- **条件边实现门控** - 阶段转换由代码级别的检查函数控制
- **显式状态管理** - 每个节点的输入输出都可追踪、可调试
- **节点级可观测** - 每个节点独立，可单独测试和记录日志

### Key Differentiators

| 维度 | 当前架构 | 目标架构 |
|------|----------|----------|
| **控制方式** | 提示词隐式控制 | 代码显式控制 |
| **工作流保证** | 依赖 LLM 自觉 | 图结构强制 |
| **状态可见性** | 黑盒 | 显式 State |
| **调试体验** | 只能看输入输出 | 节点级追踪 |
| **可扩展性** | 提示词越长越难维护 | 模块化节点 |

**关键架构约束：**
- 保持 Alex 智能体现有功能不变
- 为 Lisa 创建独立的扩展模块
- 共享基础设施只做向后兼容的扩展

---

## Target Users

### Primary Users

**维护开发者 (Maintainer Developer)**

| 属性 | 描述 |
|------|------|
| **角色** | 负责 Lisa 智能体代码维护和功能扩展的工程师 |
| **背景** | 熟悉 Python、LangGraph/LangChain、了解 LLM 应用开发 |
| **核心诉求** | 可调试、可追踪、代码可维护 |
| **当前痛点** | 系统是黑盒，无法观测中间状态，出问题只能靠猜测 |
| **成功标准** | 能够清晰追踪每个节点的执行，快速定位问题根因 |

### Secondary Users

**一线测试人员 (QA Engineer)**

| 属性 | 描述 |
|------|------|
| **角色** | 使用 Lisa 智能体进行测试策略规划和用例设计的 QA 工程师 |
| **背景** | 测试领域专家，不一定了解系统内部实现 |
| **核心诉求** | 稳定、一致的输出结果 |
| **当前痛点** | 相同输入可能得到不一致的输出，需要多次重试 |
| **成功标准** | 智能体严格遵循工作流，输出可预期 |

### User Journey

由于这是技术重构项目，用户旅程聚焦于**开发者体验**：

```
[维护开发者旅程]

1. 发现问题
   └─► 用户反馈 Lisa 输出不符合预期

2. 调试定位 (目标状态)
   └─► 查看 LangGraph 状态日志
   └─► 定位到具体节点（如 A2_risk_analysis）
   └─► 检查节点输入/输出

3. 修复验证
   └─► 修改特定节点逻辑
   └─► 单独测试该节点
   └─► 验证整体流程

4. 扩展功能
   └─► 添加新节点或子图
   └─► 复用现有状态定义
   └─► 独立于 Alex 智能体部署
```

---

## Success Metrics

*Demo 级别项目，暂不定义详细指标。核心验收标准：MVP 功能完整可运行。*

---

## MVP Scope

### Core Features (第一阶段迁移)

| 模块 | 功能 | 对应提示词章节 |
|------|------|----------------|
| **1. State Schema** | Lisa 专用状态定义，独立于 Alex | 新增 |
| **2. System Prompt** | Persona/Style/Principles 静态配置 | 1.1-1.3 |
| **3. 意图识别节点** | `intent_recognition_node` + 路由条件边 | 4.1 |
| **4. 工作流 A 子图** | A1→A2→A3→A4 四个子阶段节点 | 4.2 |
| **5. 阶段门控** | `gate_check` 条件边函数 | 2.5 |
| **6. 输出格式化** | 结构化响应模板 | 3.1 |

### Out of Scope for MVP

| 阶段 | 内容 | 原因 |
|------|------|------|
| **第二阶段** | 内部质量驱动协议 (2.1) | 复杂度高，需要子图嵌套 |
| **第二阶段** | 全景-聚焦交互协议 (2.3) | 依赖状态管理完善 |
| **第三阶段** | 工具调用协议 (2.4) | 需要 Tool Calling 集成 |
| **第三阶段** | 用户命令处理 (5.1) | 非核心功能 |
| **第三阶段** | 工作流 B-F | 先验证 A 的架构 |

### Key Architecture Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| **Lisa 独立性** | 为 Lisa 创建独立模块 `lisa_v2/` | 不破坏 Alex 现有功能 |
| **状态继承** | 扩展 `AssistantState` 或创建 `LisaState` | 待实现时确定 |
| **持久化** | 暂不实现 Checkpoint | Demo 级别简化 |

### Future Vision

**第二阶段：协议增强**
- 内部质量驱动协议（PDCA 质量环）
- 全景-聚焦交互协议
- 进展跟踪机制

**第三阶段：完整功能**
- 工具调用协议集成
- 用户命令处理（*summary, *focus 等）
- 工作流 B-F 实现
- 生产级持久化支持

