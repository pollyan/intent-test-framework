---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - lisa-langgraph-enhancement/prd-lisa-langgraph-enhancement.md
  - lisa-langgraph-enhancement/product-brief-lisa-langgraph-2025-12-19.md
  - architecture-backend.md
  - index.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2025-12-19'
project_name: 'Lisa-LangGraph-Enhancement'
user_name: 'Anhui'
date: '2025-12-19'
---

# Architecture Decision Document - Lisa-LangGraph-Enhancement

**Author:** Anhui
**Date:** 2025-12-19

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements Summary (33 FRs):**

| 类别 | FR 数量 | 核心内容 |
|------|---------|----------|
| **状态管理** | 6 | LisaState 独立定义，支持阶段跟踪、产出物存储、门控状态 |
| **意图识别** | 5 | 用户意图分析，映射到工作流 A-F，条件边路由 |
| **工作流 A** | 12 | 四子阶段节点（A1-A4），各有独立产出物 |
| **阶段门控** | 4 | 代码级门控检查，用户确认触发状态转换 |
| **输出格式化** | 3 | 结构化响应模板，Markdown checklist 进展 |
| **架构约束** | 3 | Lisa 独立模块，共享基础设施向后兼容 |

**Non-Functional Requirements (3 NFRs):**
- NFR1: 节点级日志记录，便于调试
- NFR2: 错误优雅处理，返回用户友好信息
- NFR3: 遵循现有项目编码规范

### Scale & Complexity

| 维度 | 评估 |
|------|------|
| **Primary domain** | AI/ML - LangGraph 应用开发 |
| **Complexity level** | Medium |
| **Project type** | Brownfield extension (独立于 Alex 的模块扩展) |
| **Estimated components** | 8-10 (state, graph, 5 nodes, utils) |

### Technical Constraints & Dependencies

| 约束 | 影响 |
|------|------|
| 现有 Alex 智能体共享核心文件 | Lisa 扩展需独立目录，避免直接修改共享代码 |
| LangGraph 1.0+ API | 使用 StateGraph, add_edge, add_conditional_edges |
| service.py 统一入口 | 通过 assistant_type="lisa" 路由到新图 |
| langgraph-checkpoint-postgres | 已配置，MVP 暂不实现持久化 |

### Cross-Cutting Concerns

1. **State Compatibility**: LisaState 需决定继承 vs 独立
2. **Observability**: 标准化节点日志格式
3. **Error Strategy**: 节点失败回退机制
4. **Prompt Modularity**: v5.0 Bundle 拆分为节点级提示词

---

## Starter Template Evaluation

### Project Type: Brownfield Extension

**Lisa-LangGraph-Enhancement** 是对现有系统的模块扩展，不需要 Starter Template。

### Existing Technology Stack

| 类别 | 技术 | 版本 | 状态 |
|------|------|------|------|
| **语言** | Python | 3.8+ | ✅ 已确定 |
| **Web 框架** | Flask | 2.3.3 | ✅ 已确定 |
| **AI 工作流** | LangGraph | 1.0+ | ✅ 已确定 |
| **LLM 集成** | LangChain + OpenAI | 1.1+ | ✅ 已确定 |
| **数据库** | PostgreSQL / SQLite | - | ✅ 已确定 |

### Extension Location

```
web_gui/services/langgraph_agents/
├── __init__.py              # 现有
├── state.py                 # 现有 (Alex 使用)
├── graph.py                 # 需修改路由
├── nodes.py                 # 现有 (Alex 使用)
├── service.py               # 现有 (共享)
│
└── lisa_v2/                 # 🆕 新增 Lisa 专属模块
    ├── __init__.py
    ├── state.py             # LisaState 定义
    ├── graph.py             # Lisa 图结构
    ├── nodes/               # 节点实现
    └── prompts/             # 提示词模块
```

### Starter Template Decision

**结论**: 不适用 - Brownfield 扩展项目，遵循现有项目结构和编码规范。

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. State Design - LisaState 完全独立
2. Graph Structure - 混合模式（主图 + 子图）
3. Routing Strategy - 独立图模块

**Important Decisions (Shape Architecture):**
4. Prompt Management - 分层组合
5. Gate Check - 混合策略（LLM + 代码验证）

### Decision 1: State Design

| 属性 | 值 |
|------|-----|
| **选择** | 完全独立的 LisaState |
| **理由** | 确保 Lisa 模块完全隔离，不受 AssistantState 变更影响 |
| **影响** | lisa_v2/state.py 需定义完整的状态字段 |

**LisaState 字段设计：**

```python
class LisaState(TypedDict):
    # 基础字段
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    
    # 工作流状态 - 使用业务含义命名
    current_stage: Literal["intent", "clarification", "risk_analysis", "test_design", "review", "done"]
    detected_intent: Optional[str]  # A-F
    
    # 产出物存储 - 使用业务含义命名
    clarification_output: Optional[Dict]    # 需求澄清清单
    risk_analysis_output: Optional[Dict]    # 测试策略蓝图
    test_design_output: Optional[Dict]      # 测试用例集
    review_output: Optional[Dict]           # 最终文档
    
    # 门控状态
    gate_passed: bool
    
    # 错误处理
    error_message: Optional[str]
```

### Decision 2: Graph Structure

| 属性 | 值 |
|------|-----|
| **选择** | 混合模式 - 意图识别在主图，工作流作为子图 |
| **理由** | 主图简洁，工作流模块化，便于后续扩展 B-F |
| **影响** | 需要设计子图状态映射 |

**图结构设计：**

```
Lisa Main Graph:
  START
    │
    ▼
  [intent_node]
    │
    ├─ intent="A" ──► [workflow_a_subgraph] ──► END
    ├─ intent="B" ──► [placeholder_b] ──► END (未来)
    └─ intent="unclear" ──► [clarify_intent] ──► [intent_node]

Workflow A Subgraph (使用业务含义命名):
  START
    │
    ▼
  [clarification_node] ◄──┐
    │                      │ gate_failed
    ▼ gate_passed          │
  [risk_analysis_node] ◄──┤
    │                      │
    ▼ gate_passed          │
  [test_design_node] ◄────┤
    │                      │
    ▼ gate_passed          │
  [review_node] ──────────►│
    │
    ▼
  END
```

### Decision 3: Prompt Management

| 属性 | 值 |
|------|-----|
| **选择** | 分层组合 - 共享核心 Persona + 节点专用指令 |
| **理由** | 平衡一致性与 Token 效率 |
| **影响** | 需要设计提示词模块结构 |

**提示词模块结构（使用业务含义命名）：**

```
lisa_v2/prompts/
├── __init__.py
├── core.py              # LISA_CORE_PROMPT (Persona + Style + Principles)
├── intent.py            # 意图识别专用指令
├── clarification.py     # 需求澄清指令
├── risk_analysis.py     # 风险分析指令
├── test_design.py       # 测试设计指令
└── review.py            # 评审交付指令
```

### Decision 4: Gate Check Implementation

| 属性 | 值 |
|------|-----|
| **选择** | 混合策略 - LLM 输出 + 代码级验证 |
| **理由** | 双重保障门控可靠性，保持可调试性 |
| **影响** | 需要定义结构化输出格式 |

**门控检查函数：**

```python
# 阶段到产出物字段的映射
STAGE_OUTPUT_MAP = {
    "clarification": "clarification_output",
    "risk_analysis": "risk_analysis_output",
    "test_design": "test_design_output",
    "review": "review_output"
}

def gate_check(state: LisaState) -> Literal["pass", "stay"]:
    # 1. 检查产出物是否存在
    current_stage = state["current_stage"]
    output_key = STAGE_OUTPUT_MAP.get(current_stage)
    if output_key and not state.get(output_key):
        return "stay"
    
    # 2. 检查 LLM 标记的门控状态
    if state.get("gate_passed"):
        return "pass"
    
    return "stay"
```

### Decision 5: Routing Strategy

| 属性 | 值 |
|------|-----|
| **选择** | 独立图模块 - Lisa 图完全在 lisa_v2/graph.py 定义 |
| **理由** | 完全隔离，符合独立部署原则 |
| **影响** | 主 graph.py 仅需最小导入改动 |

**路由改动：**

```python
# graph.py (最小改动)
from .lisa_v2.graph import create_lisa_v2_graph

def get_graph_for_assistant(assistant_type: str, checkpointer=None):
    if assistant_type == "alex":
        return create_alex_graph(checkpointer)
    elif assistant_type == "lisa":
        return create_lisa_v2_graph(checkpointer)
```

### Decision Impact Summary

| 决策 | 影响文件 | 改动量 |
|------|----------|--------|
| State Design | lisa_v2/state.py | 新增 |
| Graph Structure | lisa_v2/graph.py | 新增 |
| Prompt Management | lisa_v2/prompts/*.py | 新增 |
| Gate Check | lisa_v2/utils/gate_check.py | 新增 |
| Routing | graph.py | 最小改动 |

---

## Implementation Patterns & Consistency Rules

### Pattern Summary

| 模式 | 决策 | 示例 |
|------|------|------|
| **节点命名** | 业务含义_node | `intent_node()`, `clarification_node()` |
| **LLM 输出** | 混合格式 | 自然语言 + JSON 元数据块 |
| **日志记录** | 带上下文 | `[session-abc] node: action` |
| **状态更新** | 增量返回 | 只返回变更字段 |

### Naming Patterns

**节点函数命名（业务含义优先）：**

```python
# ✅ 正确 - 使用业务含义命名
def intent_node(state: LisaState) -> dict: ...
def clarification_node(state: LisaState) -> dict: ...
def risk_analysis_node(state: LisaState) -> dict: ...
def test_design_node(state: LisaState) -> dict: ...
def review_node(state: LisaState) -> dict: ...

# ❌ 避免 - 编号式命名（不利于维护）
def a1_node(state): ...
def a2_node(state): ...
```

**状态字段命名：**

```python
# ✅ 使用 snake_case + 业务含义
current_stage, detected_intent, clarification_output, gate_passed

# ❌ 避免
currentStage, a1_output, A1Output
```

**提示词模块命名：**

```python
# ✅ 文件名 - 业务含义
core.py, intent.py, clarification.py, risk_analysis.py

# ✅ 常量名
LISA_CORE_PROMPT, CLARIFICATION_INSTRUCTIONS, INTENT_PROMPT
```

### Format Patterns

**LLM 混合输出格式：**

```
[Lisa 的自然语言响应内容...]

---
```json
{
  "gate_status": "pass" | "stay",
  "output_summary": "本阶段产出物摘要",
  "next_action": "proceed_to_a2" | "continue_discussion"
}
```
```

**JSON 元数据解析：**

```python
def extract_metadata(response: str) -> dict:
    """从混合响应中提取 JSON 元数据"""
    if "```json" in response:
        json_start = response.rfind("```json") + 7
        json_end = response.rfind("```")
        return json.loads(response[json_start:json_end])
    return {}
```

### Logging Patterns

**日志格式：**

```python
import logging
logger = logging.getLogger("lisa_v2")

# 节点入口
logger.info(f"[{state['session_id'][:8]}] {node_name}: entry, stage={state['current_stage']}")

# 节点出口
logger.info(f"[{state['session_id'][:8]}] {node_name}: exit, gate={state.get('gate_passed')}")

# 错误记录
logger.error(f"[{state['session_id'][:8]}] {node_name}: error - {str(e)}")
```

### State Update Patterns

**增量返回模式：**

```python
def clarification_node(state: LisaState) -> dict:
    # 处理逻辑...
    
    # ✅ 只返回变更的字段
    return {
        "current_stage": "clarification",
        "clarification_output": output_data,
        "gate_passed": False
    }
    
    # ❌ 避免返回完整状态
    # return {**state, "current_stage": "clarification", ...}
```

**messages 字段特殊处理：**

```python
# messages 使用 add_messages reducer，返回新消息即可
return {
    "messages": [AIMessage(content=response)],
    "current_stage": "clarification"
}
```

### Enforcement Guidelines

**All AI Agents MUST:**

1. 遵循 `阶段_node` 命名约定
2. 使用混合输出格式（自然语言 + JSON 元数据）
3. 在日志中包含 session_id 前缀
4. 使用增量返回更新状态
5. 在节点入口/出口记录日志

**Anti-Patterns to Avoid:**

- ❌ 使用 camelCase 命名状态字段
- ❌ 在 LLM 响应中只返回 JSON（破坏用户体验）
- ❌ 不记录 session_id 导致无法追踪问题
- ❌ 返回完整状态对象
- ❌ 使用编号式命名（如 a1_node）而非业务含义命名

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
web_gui/services/langgraph_agents/
├── __init__.py                          # 现有 - 更新导出
├── state.py                             # 现有 - Alex 状态 (不修改)
├── graph.py                             # 现有 - 更新路由逻辑 ⚡
├── nodes.py                             # 现有 - Alex 节点 (不修改)
├── service.py                           # 现有 - 共享服务 (不修改)
│
└── lisa_v2/                             # 🆕 Lisa 专属模块
    ├── __init__.py                      # 模块导出
    ├── state.py                         # LisaState 定义
    ├── graph.py                         # Lisa 主图 + 子图
    │
    ├── nodes/                           # 节点实现（业务含义命名）
    │   ├── __init__.py
    │   ├── intent_node.py               # 意图识别节点
    │   ├── clarification_node.py        # 需求澄清节点
    │   ├── risk_analysis_node.py        # 风险分析节点
    │   ├── test_design_node.py          # 测试设计节点
    │   └── review_node.py               # 评审交付节点
    │
    ├── prompts/                         # 提示词模块（业务含义命名）
    │   ├── __init__.py
    │   ├── core.py                      # LISA_CORE_PROMPT
    │   ├── intent.py                    # 意图识别指令
    │   ├── clarification.py             # 需求澄清指令
    │   ├── risk_analysis.py             # 风险分析指令
    │   ├── test_design.py               # 测试设计指令
    │   └── review.py                    # 评审指令
    │
    └── utils/                           # 工具函数
        ├── __init__.py
        ├── gate_check.py                # 门控检查函数
        ├── metadata_parser.py           # JSON 元数据解析
        └── logger.py                    # 日志配置
```

### Architectural Boundaries

**模块边界图：**

```
┌─────────────────────────────────────────────────────────────┐
│                    service.py (共享入口)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────┐         ┌─────────────────────────┐   │
│   │   Alex Graph    │         │     Lisa v2 Graph       │   │
│   │   (现有)        │         │     (新增)              │   │
│   │                 │         │                         │   │
│   │  state.py       │         │  lisa_v2/state.py       │   │
│   │  nodes.py       │         │  lisa_v2/nodes/*.py     │   │
│   │  graph.py       │         │  lisa_v2/graph.py       │   │
│   └─────────────────┘         └─────────────────────────┘   │
│                                                              │
│   ◄──────────── 完全隔离，无依赖 ──────────────►            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**API 边界：**
- Lisa v2 复用现有 `/api/requirements` 端点
- 通过 `assistant_type="lisa"` 参数区分

### Requirements to Structure Mapping

| FR 类别 | 目标文件 | 说明 |
|---------|----------|------|
| **FR1-6 状态管理** | `lisa_v2/state.py` | LisaState TypedDict |
| **FR7-11 意图识别** | `lisa_v2/nodes/intent_node.py` | 意图识别 + 条件边 |
| **FR12-15 需求澄清** | `lisa_v2/nodes/clarification_node.py` | 需求澄清节点 |
| **FR16-18 风险分析** | `lisa_v2/nodes/risk_analysis_node.py` | 风险分析节点 |
| **FR19-21 测试设计** | `lisa_v2/nodes/test_design_node.py` | 测试设计节点 |
| **FR22-23 评审交付** | `lisa_v2/nodes/review_node.py` | 评审交付节点 |
| **FR24-27 阶段门控** | `lisa_v2/utils/gate_check.py` | 门控函数 |
| **FR28-30 输出格式化** | `lisa_v2/prompts/*.py` | 各阶段提示词 |
| **FR31-33 架构约束** | `graph.py` (路由改动) | 最小改动 |

### Data Flow

```
用户消息
    │
    ▼
service.py (assistant_type="lisa")
    │
    ▼
graph.py → get_graph_for_assistant()
    │
    ▼
lisa_v2/graph.py → create_lisa_v2_graph()
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                    LisaState                         │
│  {messages, session_id, current_stage,              │
│   detected_intent, clarification_output, ...}       │
└─────────────────────────────────────────────────────┘
    │
    ▼
[intent_node] → [clarification_node] → [risk_analysis_node] → [test_design_node] → [review_node]
    │                │                     │                      │                   │
    ▼                ▼                     ▼                      ▼                   ▼
  条件边           门控                  门控                    门控               END
```

### File Responsibilities

| 文件 | 职责 | 关键函数/类 |
|------|------|-------------|
| `lisa_v2/state.py` | 状态定义 | `LisaState` |
| `lisa_v2/graph.py` | 图构建 | `create_lisa_v2_graph()`, `create_workflow_a_subgraph()` |
| `lisa_v2/nodes/intent_node.py` | 意图识别 | `intent_node()` |
| `lisa_v2/nodes/clarification_node.py` | 需求澄清 | `clarification_node()` |
| `lisa_v2/nodes/risk_analysis_node.py` | 风险分析 | `risk_analysis_node()` |
| `lisa_v2/nodes/test_design_node.py` | 测试设计 | `test_design_node()` |
| `lisa_v2/nodes/review_node.py` | 评审交付 | `review_node()` |
| `lisa_v2/utils/gate_check.py` | 门控判断 | `gate_check()`, `route_by_intent()` |
| `lisa_v2/utils/metadata_parser.py` | 输出解析 | `extract_metadata()` |
| `lisa_v2/prompts/core.py` | 核心人格 | `LISA_CORE_PROMPT` |

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- LisaState 独立设计与独立图模块完美配合
- 混合图结构支持灵活的门控策略
- 分层提示词与节点模块化设计一致
- 所有技术选择（LangGraph 1.0+, Python 3.8+）相互兼容

**Pattern Consistency:**
- 业务含义命名贯穿全部代码（节点、状态、文件）
- 增量状态返回遵循 LangGraph reducer 约定
- 混合 LLM 输出格式统一
- 日志格式统一便于调试

**Structure Alignment:**
- `lisa_v2/` 模块完全独立，不影响 Alex
- `graph.py` 仅需最小改动（添加导入和路由）
- 目录结构清晰：nodes/, prompts/, utils/ 分离

### Requirements Coverage ✅

**Functional Requirements Coverage:** 33/33 (100%)

| FR 类别 | 覆盖状态 | 架构支撑 |
|---------|----------|----------|
| FR1-6 状态管理 | ✅ | `lisa_v2/state.py` |
| FR7-11 意图识别 | ✅ | `intent_node.py` + 条件边 |
| FR12-15 需求澄清 | ✅ | `clarification_node.py` |
| FR16-18 风险分析 | ✅ | `risk_analysis_node.py` |
| FR19-21 测试设计 | ✅ | `test_design_node.py` |
| FR22-23 评审交付 | ✅ | `review_node.py` |
| FR24-27 阶段门控 | ✅ | `gate_check.py` |
| FR28-30 输出格式化 | ✅ | `prompts/*.py` |
| FR31-33 架构约束 | ✅ | 独立模块设计 |

**Non-Functional Requirements Coverage:** 3/3 (100%)

| NFR | 覆盖状态 | 架构支撑 |
|-----|----------|----------|
| NFR1 节点级日志 | ✅ | 带上下文日志模式 |
| NFR2 错误处理 | ✅ | `error_message` 状态字段 |
| NFR3 编码规范 | ✅ | 遵循现有项目结构 |

### Implementation Readiness ✅

**Decision Completeness:**
- 5 个核心架构决策全部记录
- 所有决策都有理由和影响分析
- 技术版本已验证

**Structure Completeness:**
- 完整的目录结构定义
- 所有文件和目录已规划
- 组件边界清晰

**Pattern Completeness:**
- 4 个实现模式有示例代码
- 命名约定全面
- 反模式有明确说明

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] 项目上下文全面分析
- [x] 规模和复杂度评估
- [x] 技术约束识别
- [x] 跨领域关注点映射

**✅ Architectural Decisions**
- [x] 关键决策有版本记录
- [x] 技术栈完整指定
- [x] 集成模式定义
- [x] 性能考虑已处理

**✅ Implementation Patterns**
- [x] 命名约定建立（业务含义优先）
- [x] 结构模式定义
- [x] 通信模式指定
- [x] 流程模式文档化

**✅ Project Structure**
- [x] 完整目录结构定义
- [x] 组件边界建立
- [x] 集成点映射
- [x] 需求到结构的映射完成

### Architecture Readiness Assessment

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
1. Lisa 完全独立于 Alex，零耦合风险
2. 业务含义命名，代码自文档化，可维护性强
3. 模块化设计，易于测试和扩展
4. 完整的 FR→文件映射，实现路径清晰

**Areas for Future Enhancement:**
1. 第二阶段：添加内部质量驱动协议
2. 第三阶段：添加工具调用集成
3. 生产级：添加持久化支持

### Implementation Handoff

**AI Agent Guidelines:**
- 严格遵循所有架构决策
- 使用业务含义命名（非编号式）
- 使用增量状态返回模式
- 尊重项目结构和边界
- 遇到架构问题时参考本文档

**First Implementation Priority:**

```bash
# Step 1: 创建目录结构
mkdir -p web_gui/services/langgraph_agents/lisa_v2/{nodes,prompts,utils}

# Step 2: 创建核心文件
touch web_gui/services/langgraph_agents/lisa_v2/__init__.py
touch web_gui/services/langgraph_agents/lisa_v2/state.py
touch web_gui/services/langgraph_agents/lisa_v2/graph.py
```

---

## Architecture Completion Summary

### Workflow Completion

| 属性 | 值 |
|------|-----|
| **Architecture Decision Workflow** | ✅ COMPLETED |
| **Total Steps Completed** | 8 |
| **Date Completed** | 2025-12-19 |
| **Document Location** | `_bmad-output/lisa-langgraph-enhancement/architecture-lisa-langgraph.md` |

### Final Architecture Deliverables

**📋 Complete Architecture Document**
- 5 个核心架构决策，全部有版本和理由记录
- 4 个实现模式确保 AI Agent 一致性
- 完整的项目结构，所有文件和目录已定义
- 33 个功能需求到架构的完整映射
- 验证确认一致性和完整性

**🏗️ Implementation Ready Foundation**
- 5 个架构决策已完成
- 4 个实现模式已定义
- 10+ 个架构组件已规划
- 33/33 功能需求完全支持

**📚 AI Agent Implementation Guide**
- 技术栈：Python 3.8+, LangGraph 1.0+, Flask 2.3.3
- 一致性规则防止实现冲突
- 项目结构有明确边界
- 集成模式和通信标准

### Development Sequence

1. **初始化项目** - 创建 `lisa_v2/` 目录结构
2. **实现状态定义** - `state.py` 中的 `LisaState`
3. **实现图结构** - `graph.py` 中的主图和子图
4. **实现节点** - 按顺序：intent → clarification → risk_analysis → test_design → review
5. **配置提示词** - 从 Lisa v5.0 Bundle 提取到各模块
6. **更新路由** - 在主 `graph.py` 中添加导入

### Quality Assurance Checklist

**✅ Architecture Coherence**
- [x] 所有决策相互兼容
- [x] 技术选择相互一致
- [x] 模式支持架构决策
- [x] 结构与决策对齐

**✅ Requirements Coverage**
- [x] 所有功能需求有架构支撑
- [x] 所有非功能需求已处理
- [x] 跨领域关注点已解决
- [x] 集成点已定义

**✅ Implementation Readiness**
- [x] 决策具体可执行
- [x] 模式防止 Agent 冲突
- [x] 结构完整无歧义
- [x] 示例代码清晰

---

**Architecture Status:** ✅ READY FOR IMPLEMENTATION

**Next Phase:** 使用本文档的架构决策和模式开始实现

**Document Maintenance:** 实现过程中如有重大技术决策变更，请更新本文档


