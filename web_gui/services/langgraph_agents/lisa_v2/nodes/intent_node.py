"""
意图识别节点

对应 Lisa v5.0 的 4.1 意图识别与工作流调度器
"""

from typing import Dict, Optional, Any
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.core import LISA_CORE_PROMPT
from ..prompts.intent import INTENT_RECOGNITION_PROMPT, WORKFLOW_MAP
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit, log_node_error
from ..utils.metadata_parser import extract_metadata
from ..utils.llm_factory import get_llm_from_db

logger = get_lisa_logger()


def analyze_intent(user_message: str) -> tuple[str, float]:
    """
    分析用户意图
    
    基于关键词匹配进行快速意图预判
    
    Args:
        user_message: 用户消息内容
        
    Returns:
        (detected_intent, confidence) 元组
    """
    user_message_lower = user_message.lower()
    
    # 遍历工作流映射，查找匹配的关键词
    for workflow_id, workflow_info in WORKFLOW_MAP.items():
        keywords = workflow_info.get("keywords", [])
        
        for keyword in keywords:
            if keyword in user_message_lower:
                # 找到匹配的关键词，返回高置信度
                return workflow_id, 0.9
    
    # 没有找到明确匹配，返回低置信度
    return "F", 0.3


def format_intent_clarification_message() -> str:
    """
    生成意图澄清消息
    
    Returns:
        意图澄清的消息内容
    """
    return """您好！我是 **Lisa Song**，您的首席测试领域专家。

很高兴为您提供专业的测试分析服务。在开始之前，让我们先明确您本次的核心任务场景。

请问您的任务更接近以下哪一种？

**A. 新需求/功能测试设计**  
为一个全新的功能或需求设计完整的测试方案。

**B. 需求评审与可测试性分析**  
审查需求文档，寻找逻辑漏洞、模糊点和不可测试之处。

**C. 生产缺陷分析与回归策略**  
针对一个已发现的线上问题，进行根因分析并设计回归测试。

**D. 专项测试策略规划**  
聚焦于非功能性领域，如性能、安全或自动化，进行策略规划。

**E. 产品测试现状评估**  
对现有的测试现状进行分析、审查和优化建议。

**F. 其他测试任务**  
上述场景都不完全匹配，需要进行更开放的探讨或咨询。

💡 **提示**：您可以直接输入字母（如 A），或者直接描述您的测试需求，我会为您匹配最合适的工作流。"""


def format_intent_confirmation_message(
    workflow_id: str,
    user_input_summary: str
) -> str:
    """
    生成意图确认消息
    
    Args:
        workflow_id: 工作流ID (A-F)
        user_input_summary: 用户输入摘要
        
    Returns:
        意图确认的消息内容
    """
    workflow_info = WORKFLOW_MAP.get(workflow_id, WORKFLOW_MAP["F"])
    workflow_name = workflow_info["name"]
    
    return f"""您好！我是 Lisa Song。

根据您的需求「{user_input_summary}」，我理解您的任务是进行 **{workflow_name}**。

我将启动对应的工作流来展开工作。您看可以吗？"""


def intent_node(state: LisaState, config: Optional[RunnableConfig] = None) -> Dict:
    """
    意图识别节点
    
    执行逻辑：
    1. 分析用户最新消息的意图
    2. 高置信度 -> 生成确认式建议
    3. 低置信度 -> 生成选择题
    
    Args:
        state: 当前状态
        config: LangChain 运行配置（包含 callbacks，用于 Langfuse 追踪）
        
    Returns:
        状态增量更新
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "intent_node", session_id, state.get("current_stage", "intent"))
    
    try:
        # 获取 LLM 实例
        llm = get_llm_from_db()
        if not llm:
            logger.warning("LLM 未配置，使用降级模式")
            # 降级：返回静态消息
            return _handle_intent_fallback(state, session_id)
        
        messages = state.get("messages", [])
        is_activated = state.get("is_activated", False)
        
        # 如果尚未激活（首次交互），显示欢迎语
        if not is_activated:
            logger.info(f"[{session_id[:8]}] 首次交互，显示欢迎语")
            response = format_intent_clarification_message()
            
            log_node_exit(logger, "intent_node", session_id, False, {"action": "welcome"})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "intent",
                "detected_intent": None,
                "intent_confidence": 0.0,
                "gate_passed": False,
                "is_activated": True,  # 标记为已激活
            }
        
        # 获取用户最新消息
        user_message = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break
        
        # 检查是否是用户选择意图（A-F）
        if user_message.strip().upper() in ["A", "B", "C", "D", "E", "F"]:
            # 用户明确选择了意图
            selected_intent = user_message.strip().upper()
            workflow_info = WORKFLOW_MAP.get(selected_intent, WORKFLOW_MAP["F"])
            
            response = f"""好的！您选择了 **{workflow_info['name']}**。

我将立即启动该工作流，让我们开始吧！"""
            
            log_node_exit(logger, "intent_node", session_id, True, {"intent": selected_intent})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "intent",
                "detected_intent": selected_intent,
                "intent_confidence": 1.0,
                "gate_passed": True,
            }
        
        # 检查是否是用户确认（"可以"、"好的"、"是"等）
        confirmation_keywords = ["可以", "好的", "是", "确认", "开始", "ok", "yes"]
        is_confirmation = any(kw in user_message.lower() for kw in confirmation_keywords)
        
        if is_confirmation and state.get("detected_intent"):
            # 用户确认了之前的意图建议
            detected_intent = state.get("detected_intent")
            workflow_info = WORKFLOW_MAP.get(detected_intent, WORKFLOW_MAP["F"])
            
            response = f"""好的！让我们开始 **{workflow_info['name']}** 工作流。"""
            
            log_node_exit(logger, "intent_node", session_id, True, {"intent": detected_intent})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "intent",
                "gate_passed": True,
            }
        
        # 分析意图
        detected_intent, confidence = analyze_intent(user_message)
        
        # 使用 LLM 生成响应
        if confidence >= 0.8:
            # 高置信度：让 LLM 生成确认式建议
            workflow_info = WORKFLOW_MAP.get(detected_intent, WORKFLOW_MAP["F"])
            summary = user_message[:50] + "..." if len(user_message) > 50 else user_message
            
            prompt = f"""{LISA_CORE_PROMPT}

{INTENT_RECOGNITION_PROMPT}

## 当前场景
用户输入："{summary}"
识别到的意图：{workflow_info['name']}（置信度：{confidence:.0%}）

## 你的任务
生成一个专业、友好的确认式建议，告诉用户你理解了他的意图，并准备启动对应的工作流。

输出格式要求：
- 简洁明了，不超过100字
- 使用礼貌、专业的语气
- 明确说明将要启动的工作流名称"""
            
            # 调用 LLM，传递 config 以启用 Langfuse 追踪
            response_msg = llm.invoke([HumanMessage(content=prompt)], config=config)
            response = response_msg.content
            gate_passed = False
        else:
            # 低置信度：使用固定模板
            response = format_intent_clarification_message()
            gate_passed = False
        
        log_node_exit(logger, "intent_node", session_id, gate_passed, 
                     {"intent": detected_intent, "confidence": confidence})
        
        return {
            "messages": [AIMessage(content=response)],
            "current_stage": "intent",
            "detected_intent": detected_intent,
            "intent_confidence": confidence,
            "gate_passed": gate_passed,
        }
        
    except Exception as e:
        log_node_error(logger, "intent_node", session_id, e)
        
        return {
            "messages": [AIMessage(content=f"抱歉，意图识别时发生错误：{str(e)}")],
            "error_message": str(e),
            "gate_passed": False,
        }


def _handle_intent_fallback(state: LisaState, session_id: str) -> Dict:
    """
    降级处理函数（当 LLM 不可用时）
    
    Args:
        state: 当前状态
        session_id: 会话ID
        
    Returns:
        状态增量更新
    """
    is_activated = state.get("is_activated", False)
    
    # 如果尚未激活，显示欢迎语
    if not is_activated:
        response = format_intent_clarification_message()
        return {
            "messages": [AIMessage(content=response)],
            "current_stage": "intent",
            "detected_intent": None,
            "intent_confidence": 0.0,
            "gate_passed": False,
            "is_activated": True,
        }
    
    # 获取用户最新消息
    user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    # 使用静态意图识别
    detected_intent, confidence = analyze_intent(user_message)
    
    # 使用静态消息
    if confidence >= 0.8:
        summary = user_message[:50] + "..." if len(user_message) > 50 else user_message
        response = format_intent_confirmation_message(detected_intent, summary)
    else:
        response = format_intent_clarification_message()
    
    return {
        "messages": [AIMessage(content=response)],
        "current_stage": "intent",
        "detected_intent": detected_intent,
        "intent_confidence": confidence,
        "gate_passed": False,
    }

