"""
需求澄清节点

对应 Lisa v5.0 的 子阶段 A1: 需求澄清与分解
"""

from typing import Dict, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.core import LISA_CORE_PROMPT
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit, log_node_error
from ..utils.metadata_parser import extract_metadata

logger = get_lisa_logger()


# 需求澄清阶段专用提示词
CLARIFICATION_PROMPT = """
## 子阶段 A1: 需求澄清与分解

### 目标
消除需求中的所有模糊点，将宏观需求分解为清晰、独立、可测试的特性点。

### 核心产出物
一份**通过逐一讨论最终形成的**《需求澄清与可测试性分析清单》。

### 执行逻辑

#### 第一步：生成并确认分析框架
1. 使用`思维导图`生成初步的需求分解结构
2. 以 Mermaid 代码块输出分析框架
3. 请求用户确认框架的准确性

#### 第二步：基于框架发起澄清讨论
1. 在用户确认框架后，基于框架启动需求澄清讨论
2. 遵循"全景-聚焦"交互协议
3. 将框架的各节点作为讨论议程

### 输出格式要求

📈 任务进展概览
- [-] 工作流 A: 新需求/功能测试设计
  - [-] A1: 需求澄清与分解
    - [当前状态] 分析框架生成/讨论中
  - [ ] A2: 风险分析与策略制定
  - [ ] A3: 详细测试设计与用例编写
  - [ ] A4: 评审与交付

---
[核心交互内容]
""".strip()


def clarification_node(state: LisaState, config: Optional[RunnableConfig] = None) -> Dict:
    """
    需求澄清节点
    
    执行逻辑：
    1. 首次进入：生成需求分析框架（思维导图）
    2. 后续交互：基于框架进行逐项澄清
    3. 用户确认后：输出《需求澄清与可测试性分析清单》
    
    Args:
        state: 当前状态
        config: LangChain 运行配置（包含 callbacks，用于 Langfuse 追踪）
        
    Returns:
        状态增量更新
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "clarification_node", session_id, state.get("current_stage", "clarification"))
    
    try:
        messages = state.get("messages", [])
        clarification_output = state.get("clarification_output")
        current_agenda = state.get("current_agenda")
        
        # 获取用户最新消息
        user_message = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break
        
        # 检查用户是否确认完成（进入下一阶段）
        completion_keywords = ["确认", "完成", "没问题", "可以", "下一步", "继续"]
        if clarification_output and any(kw in user_message for kw in completion_keywords):
            response = """📈 任务进展概览
- [-] 工作流 A: 新需求/功能测试设计
  - [X] A1: 需求澄清与分解 - 共识已达成
  - [-] A2: 风险分析与策略制定
  - [ ] A3: 详细测试设计与用例编写
  - [ ] A4: 评审与交付

---

非常好！需求澄清阶段已完成，我们已形成《需求澄清与可测试性分析清单》。

接下来，我将进入 **风险分析与策略制定** 阶段，基于已澄清的需求识别潜在风险。

---
```json
{
  "gate_status": "pass",
  "output_summary": "需求澄清完成，输出《需求澄清与可测试性分析清单》",
  "next_action": "proceed_to_risk_analysis"
}
```"""
            
            log_node_exit(logger, "clarification_node", session_id, True)
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "clarification",
                "gate_passed": True,
            }
        
        # 首次进入或需要生成分析框架
        if not current_agenda:
            # 生成初始分析框架
            response = f"""📈 任务进展概览
- [-] 工作流 A: 新需求/功能测试设计
  - [-] A1: 需求澄清与分解
    - [-] 生成分析框架
  - [ ] A2: 风险分析与策略制定
  - [ ] A3: 详细测试设计与用例编写
  - [ ] A4: 评审与交付

---

我已经使用`思维导图`为您完成了初步的需求分解，它帮助我们构建了一个分析框架。

```mermaid
mindmap
  root((需求分析))
    功能需求
      核心功能
      辅助功能
      集成功能
    非功能需求
      性能要求
      安全要求
      可用性要求
    业务规则
      输入验证
      业务逻辑
      输出处理
    边界条件
      正常流程
      异常流程
      边界值
```

基于您提供的需求信息，请帮我确认：

1. **这个框架是否准确地反映了需求的核心结构？**
2. **是否有需要补充或调整的分支？**

请您审阅后告诉我，我们将基于确认后的框架展开详细的需求澄清讨论。

---
```json
{{
  "gate_status": "stay",
  "output_summary": "生成初始分析框架",
  "next_action": "await_framework_confirmation"
}}
```"""
            
            # 初始化议程
            initial_agenda = [
                "功能需求 - 核心功能",
                "功能需求 - 辅助功能",
                "非功能需求",
                "业务规则",
                "边界条件"
            ]
            
            log_node_exit(logger, "clarification_node", session_id, False, {"action": "framework_generated"})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "clarification",
                "current_agenda": initial_agenda,
                "current_agenda_index": 0,
                "gate_passed": False,
            }
        
        # 框架已确认，进行逐项澄清
        agenda_index = state.get("current_agenda_index", 0)
        
        if agenda_index < len(current_agenda):
            current_topic = current_agenda[agenda_index]
            next_index = agenda_index + 1
            
            response = f"""📈 任务进展概览
- [-] 工作流 A: 新需求/功能测试设计
  - [-] A1: 需求澄清与分解
    - [X] 分析框架确认
    - [-] 议题 {agenda_index + 1}/{len(current_agenda)}: {current_topic}
  - [ ] A2: 风险分析与策略制定
  - [ ] A3: 详细测试设计与用例编写
  - [ ] A4: 评审与交付

---

感谢您的反馈！现在让我们聚焦讨论 **{current_topic}**。

针对这个议题，我需要了解：

1. **具体的功能描述是什么？**
2. **预期的输入和输出是什么？**
3. **有哪些已知的业务规则或约束？**

请您详细描述，或者如果这个议题已经足够清晰，输入「下一个」继续。

---
```json
{{
  "gate_status": "stay",
  "output_summary": "讨论议题: {current_topic}",
  "next_action": "continue_discussion"
}}
```"""
            
            # 更新产出物（累积）
            updated_output = clarification_output or {"topics": []}
            if user_message and "下一个" not in user_message:
                updated_output["topics"].append({
                    "topic": current_topic,
                    "discussion": user_message
                })
            
            log_node_exit(logger, "clarification_node", session_id, False, 
                         {"topic": current_topic, "index": agenda_index})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "clarification",
                "current_agenda_index": next_index,
                "clarification_output": updated_output,
                "gate_passed": False,
            }
        
        # 所有议题讨论完成，生成总结
        response = """📈 任务进展概览
- [-] 工作流 A: 新需求/功能测试设计
  - [-] A1: 需求澄清与分解
    - [X] 所有议题讨论完成
    - [-] 生成《需求澄清与可测试性分析清单》
  - [ ] A2: 风险分析与策略制定
  - [ ] A3: 详细测试设计与用例编写
  - [ ] A4: 评审与交付

---

## 《需求澄清与可测试性分析清单》

基于我们的讨论，我整理出以下清单：

| 序号 | 功能点 | 描述 | 可测试性 | 优先级 |
|------|--------|------|----------|--------|
| 1 | 核心功能 | 待确认 | 高 | P0 |
| 2 | 辅助功能 | 待确认 | 中 | P1 |
| 3 | 边界处理 | 待确认 | 高 | P0 |

**请确认以上清单是否准确？** 确认后我们将进入风险分析阶段。

---
```json
{
  "gate_status": "stay",
  "output_summary": "生成《需求澄清与可测试性分析清单》",
  "next_action": "await_confirmation"
}
```"""
        
        log_node_exit(logger, "clarification_node", session_id, False, {"action": "summary_generated"})
        
        return {
            "messages": [AIMessage(content=response)],
            "current_stage": "clarification",
            "clarification_output": clarification_output or {"topics": [], "summary": "待确认"},
            "gate_passed": False,
        }
        
    except Exception as e:
        log_node_error(logger, "clarification_node", session_id, e)
        
        return {
            "messages": [AIMessage(content=f"抱歉，需求澄清时发生错误：{str(e)}")],
            "error_message": str(e),
            "gate_passed": False,
        }

