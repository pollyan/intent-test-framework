# Lisa Agent 架构设计原则

> 本文档定义了 Lisa Agent 的核心架构设计原则，所有开发必须严格遵循。

## 🎯 核心哲学

### "LLM 驱动，框架编排"

**原则：** LLM 是决策中心，LangGraph 只负责执行和状态持久化。

- ✅ **LLM 决定**：对话流程、状态转换、异常处理
- ❌ **代码不决定**：不写 `if user_intent == "A"` 这样的硬编码逻辑

**理由：**
- LLM 能够理解上下文和语义，做出灵活决策
- 硬编码逻辑僵化，无法处理边缘情况
- Prompt 即文档，易于理解和维护

---

## 📐 架构设计规则

### 1. 零硬编码原则

**禁止：** 关键词匹配、正则表达式匹配用户意图

```python
# ❌ 错误示例
if "测试用例" in user_message or "写用例" in user_message:
    intent = "A"

# ✅ 正确示例
# 让 LLM 通过提示词理解意图，输出标记
response = llm.invoke(INTENT_CHAT_PROMPT + user_message)
# "我理解您要写测试用例 <!-- INTENT: A -->"
```

**唯一例外：** 提取 LLM 输出的结构化标记（HTML 注释）

```python
# ✅ 允许：提取标记
intent_match = re.search(r'<!-- INTENT: ([A-F]) -->', llm_response)
```

---

### 2. 状态管理机制

#### 2.1 使用 HTML 注释标记

**格式：**
```html
<!-- INTENT: A -->                          # 意图识别
<!-- STAGE: A2 -->                          # 工作流阶段
<!-- STAGE: A1 | ACTION: supplement -->    # 带操作说明
```

**为什么用 HTML 注释？**
- ✅ 对用户不可见
- ✅ LLM 容易理解和生成
- ✅ 可以携带元数据
- ✅ 解析简单可靠

#### 2.2 状态决策权归属

| 职责 | 归属 | 说明 |
|------|------|------|
| **判断状态** | LLM | 根据上下文决定当前处于什么阶段 |
| **决定转换** | LLM | 决定是前进、保持还是回退 |
| **解析标记** | Python | 提取 LLM 输出的标记 |
| **执行路由** | LangGraph | 根据标记路由到对应 Node |
| **持久化** | LangGraph | 保存状态到 State |

**示例：**

```python
# Prompt 赋予 LLM 完全自主权
PROMPT = """
你有完全的决策权：
- 前进：需求已清晰 → <!-- STAGE: A2 -->
- 保持：还需澄清 → <!-- STAGE: A1 -->
- 回退：发现遗漏 → <!-- STAGE: A1 | ACTION: reopen -->
"""

# Python 代码只执行
def route(state):
    stage = extract_stage_from_llm_response(state["messages"][-1])
    return stage_to_node_mapping[stage]  # 不做任何业务判断
```

---

### 3. Node 设计原则

#### 3.1 按业务阶段拆分

**拆分标准：**
- ✅ 每个阶段有明确的目标和产出物
- ✅ 不同阶段的 Prompt 差异显著
- ✅ 需要上下文隔离（避免前期讨论干扰后期）

**示例：测试设计工作流**
```
A1: requirement_clarification_node  # 需求澄清
A2: risk_analysis_node              # 风险分析
A3: test_design_node                # 用例编写
A4: delivery_node                   # 文档交付
```

#### 3.2 Node 命名规范

**使用业务含义，避免抽象代码：**

```python
# ❌ 错误命名
workflow_a_node.py
workflow_b_node.py

# ✅ 正确命名
test_design_node.py
requirement_review_node.py
defect_analysis_node.py
```

#### 3.3 Node 的职责

每个 Node 只做三件事：

1. **构建专用 Prompt** - 注入当前阶段的上下文
2. **调用 LLM** - 使用公共辅助函数
3. **解析响应** - 提取状态标记和产出物

```python
def requirement_clarification_node(state, config):
    # 1. 构建 Prompt
    prompt = build_prompt(
        template=REQUIREMENT_CLARIFICATION_PROMPT,
        context=state
    )
    
    # 2. 调用 LLM（使用公共函数）
    response, error = invoke_llm_with_validation(
        llm, prompt, session_id, "A1", config
    )
    if error:
        return error
    
    # 3. 解析响应
    stage = extract_stage(response)
    output = extract_checklist(response) if stage != "A1" else None
    
    return {
        "messages": [AIMessage(content=clean_response(response))],
        "clarification_list": output,
        "current_stage": stage,
        "gate_passed": stage != "A1",
    }
```

---

### 4. State 设计原则

#### 4.1 结构化存储产出物

**不要依赖从对话历史中提取，而是显式存储：**

```python
class TestDesignWorkflowState(TypedDict):
    # 原始输入
    user_requirement: str
    
    # 各阶段结构化产出物
    clarification_list: Optional[Dict]      # A1 产出
    test_strategy: Optional[Dict]           # A2 产出
    test_cases: Optional[List[Dict]]        # A3 产出
    final_doc: Optional[str]                # A4 产出
    
    # 对话历史（自动共享）
    messages: List[BaseMessage]
    
    # 流程控制
    current_stage: str
    gate_passed: bool
```

#### 4.2 对话历史共享

**所有 Nodes 自动共享对话历史，无需手动传递：**

```python
# Node A
def node_a(state):
    messages = state["messages"]  # 包含所有历史
    # ...
    return {"messages": [new_message]}  # 追加新消息

# Node B（自动看到 A 的消息）
def node_b(state):
    messages = state["messages"]  # 自动包含 A 的输出
```

---

### 5. Prompt 设计原则

#### 5.1 赋予 LLM 完全自主权

Prompt 必须明确告知 LLM 它拥有的权力：

```python
PROMPT_TEMPLATE = """
## 你的权力

你有**完全的自主决策权**：

1. **前进**：条件满足 → `<!-- STAGE: NEXT -->`
2. **保持**：需要更多信息 → `<!-- STAGE: CURRENT -->`
3. **回退**：发现问题 → `<!-- STAGE: PREVIOUS | ACTION: reason -->`

不要犹豫使用这些权力。如果有任何疑问，立即回退或保持，不要带着问题前进。
"""
```

#### 5.2 动态加载阶段指导

**基础 Prompt + 阶段专用指导：**

```python
# 基础部分（所有阶段共享）
BASE_PROMPT = """
你是 Lisa Song，测试专家。
当前工作流：测试设计
"""

# 阶段专用（按需加载）
STAGE_GUIDES = {
    "A1": "A1 阶段的详细指导...",
    "A2": "A2 阶段的详细指导...",
}

# 构建完整 Prompt
full_prompt = BASE_PROMPT + STAGE_GUIDES[current_stage]
```

#### 5.3 提供决策标准

告诉 LLM **何时**应该转换状态：

```python
"""
## 决策标准

**何时前进到 A2？**
- ✅ 所有功能点都有明确的输入、输出
- ✅ 没有"可能"、"应该"等模糊词汇
- ✅ 边界条件和异常场景都已明确

**何时保持在 A1？**
- ⚠️ 用户回答含糊
- ⚠️ 发现新的待澄清点

**何时回退？**
- 🔄 发现之前遗漏的需求
- 🔄 用户主动要求修改
"""
```

---

### 6. 代码组织原则

#### 6.1 目录结构

```
lisa_v2/
├── config/              # 配置
│   └── workflows.py    # 工作流映射（字母代码 → 业务名称）
├── nodes/              # 节点（业务逻辑）
│   ├── intent_node.py
│   ├── test_design_node.py
│   └── requirement_review_node.py
├── prompts/            # LLM 提示词
│   ├── intent_chat.py
│   └── test_design_workflow.py
├── models/             # Pydantic 模型
├── utils/              # 工具函数
│   ├── llm_helper.py  # LLM 调用公共函数
│   └── logger.py
└── state.py            # 状态定义
```

#### 6.2 消除代码重复

**创建公共辅助函数：**

```python
# utils/llm_helper.py

def get_llm_with_error_handling(session_id, stage):
    """统一的 LLM 获取和错误处理"""
    # ...

def invoke_llm_with_validation(llm, messages, session_id, stage, config):
    """统一的 LLM 调用和响应验证"""
    # ...

def create_error_response(message, stage, **kwargs):
    """统一的错误响应格式"""
    # ...
```

**在 Nodes 中使用：**

```python
# 旧代码：每个 node 重复 50 行
llm = get_llm_from_db()
if not llm:
    return {"messages": [...], "gate_passed": False}
try:
    response = llm.invoke(...)
    if not response:
        ...
except Exception as e:
    ...

# 新代码：只需 2 行
llm, error = get_llm_with_error_handling(session_id, stage)
if error:
    return error

response, error = invoke_llm_with_validation(llm, messages, ...)
if error:
    return error
```

---

## 🚫 反模式（禁止的做法）

### 1. 硬编码业务规则

```python
# ❌ 禁止
if stage == "A1" and user_confirmed:
    next_stage = "A2"  # 僵化，无法处理异常

# ✅ 正确
# LLM 自己根据上下文决定是否应该进入 A2
```

### 2. 在 Python 中做语义理解

```python
# ❌ 禁止
if "不够" in user_message or "遗漏" in user_message:
    action = "回退"

# ✅ 正确
# 让 LLM 理解语义并输出标记
# "我发现有遗漏，让我们回到 A1 <!-- STAGE: A1 | ACTION: reopen -->"
```

### 3. 假设 LLM 会记住复杂规则

```python
# ❌ 禁止：期望 LLM 从文档中记住规则
PROMPT = "请遵循 v5.0 文档中的所有协议"

# ✅ 正确：在 Prompt 中明确展示规则
PROMPT = """
你必须遵循阶段门控协议：
1. 只有产出物获得用户确认后，才能进入下一阶段
2. 质量不足时，通过提问补充信息
...
"""
```

---

## ✅ 设计检查清单

在实现新功能前，确认：

- [ ] 业务逻辑由 LLM（Prompt）决定，不在 Python 代码中硬编码
- [ ] 使用 HTML 注释标记管理状态，不依赖关键词匹配
- [ ] LLM 有完全自主权（可前进、后退、保持）
- [ ] Node 按业务阶段拆分，使用业务命名
- [ ] 产出物结构化存储在 State 中
- [ ] 使用公共辅助函数，避免重复代码
- [ ] Prompt 明确告知 LLM 它的权力和决策标准
- [ ] 路由逻辑只解析标记，不做业务判断

---

## 📚 参考资源

- [AI 交互设计规则](./ai-interaction-rules.md)
- [Lisa v5.0 设计文档](../intelligent-requirements-analyzer/dist/testmaster-song-bundlev5.0.md)
- [重构记录](../web_gui/services/langgraph_agents/lisa_v2/REFACTORING.md)

---

**最后更新：2025-12-21**
**维护者：Development Team**
