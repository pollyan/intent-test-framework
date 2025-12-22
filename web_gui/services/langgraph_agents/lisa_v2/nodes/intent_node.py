"""
意图识别节点 - LLM 驱动的对话式版本（使用 HTML 注释标记）
"""

from typing import Dict, Optional
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.intent_chat import INTENT_CHAT_PROMPT
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit, log_node_error
from ..utils.llm_factory import get_llm_from_db

logger = get_lisa_logger()


def intent_node(state: LisaState, config: Optional[RunnableConfig] = None) -> Dict:
    """
    意图识别节点 - 纯 LLM 对话驱动版
    
    核心逻辑：
    1. LLM 自由对话，直到它认为意图明确
    2. LLM 添加隐藏标记 <!-- INTENT: X --> 来锁定意图
    3. Python 提取标记，设置门控状态
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "intent_node", session_id, "intent")
    
    try:
        # 使用公共方法获取 LLM
        from ..utils.llm_helper import get_llm_with_error_handling, invoke_llm_with_validation
        
        llm, error = get_llm_with_error_handling(session_id, "intent")
        if error:
            return error
        
        messages = state.get("messages", [])
        is_activated = state.get("is_activated", False)
        
        logger.info(f"[{session_id[:8]}] is_activated={is_activated}, messages_count={len(messages)}")
        
        # 首次交互：直接返回欢迎语，不调用 LLM
        if not is_activated:
            response = """您好！我是 **Lisa Song**，您的首席测试领域专家，拥有15年跨行业测试经验。

**我能为您提供以下专业服务：**

- **新需求/功能测试设计** - 为全新功能设计完整的测试方案
- **需求评审与可测试性分析** - 审查需求文档，识别逻辑漏洞
- **生产缺陷分析与回归策略** - 分析线上问题并设计回归测试
- **专项测试策略规划** - 性能、安全、自动化测试策略
- **产品测试现状评估** - 评估和优化现有测试体系
- **通用测试咨询** - 其他测试相关问题

💡 **直接描述您的测试需求，我会为您匹配合适的工作流**

请问今天有什么测试任务需要我帮忙规划吗？"""
            
            log_node_exit(logger, "intent_node", session_id, False, {"action": "welcome"})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "intent",
                "gate_passed": False,
                "is_activated": True,
            }
        
        # 意图已锁定时：检测是否切换任务
        detected_intent = state.get("detected_intent")
        if detected_intent:
            # 使用轻量级prompt快速判断
            switch_check_prompt = f"""当前用户正在执行\"{detected_intent}\"任务。

请分析用户的最新消息，判断用户是：
A. 继续当前任务的正常对话
B. 想要切换到其他任务

只回复 \"CONTINUE\" 或 \"SWITCH\"，不要有其他内容。"""
            
            switch_msg = [
                SystemMessage(content=switch_check_prompt),
                HumanMessage(content=messages[-1].content if messages else "")
            ]
            
            switch_response, error = invoke_llm_with_validation(
                llm, switch_msg, session_id, "intent_switch_check", config
            )
            if error:
                return error
            
            if "CONTINUE" in switch_response.upper():
                # 继续当前任务，直接透传到workflow
                logger.info(f"[{session_id[:8]}] ✅ 继续当前任务: {detected_intent}")
                log_node_exit(logger, "intent_node", session_id, True, {"action": "continue_workflow"})
                
                return {
                    "messages": [],  # 不添加消息，让workflow处理
                    "gate_passed": True,
                }
            else:
                # 用户想切换，清空意图，重新识别
                logger.info(f"[{session_id[:8]}] 🔄 检测到任务切换请求")
                # 继续执行下面的意图识别流程
        
        # 构建对话上下文
        system_msg = SystemMessage(content=INTENT_CHAT_PROMPT)
        conversation = [system_msg] + messages[-20:]  # 最近 20 轮
        
        # 使用公共方法调用 LLM
        response_content, error = invoke_llm_with_validation(
            llm, conversation, session_id, "intent", config
        )
        if error:
            return error
        
        # 检查是否包含意图确认标记（支持新的意图代码）
        import re
        intent_match = re.search(r'<!--\s*INTENT:\s*(\w+)\s*-->', response_content)
        
        if intent_match:
            # LLM 锁定了意图
            intent_code = intent_match.group(1)
            
            from ..config.workflows import WORKFLOW_MAP
            workflow_info = WORKFLOW_MAP.get(intent_code, WORKFLOW_MAP.get("GENERAL_CONSULTING", {}))
            workflow_name = workflow_info.get("name", "未知工作流")
            
            logger.info(f"[{session_id[:8]}] ✅ 意图已锁定: {intent_code} - {workflow_name}")
            
            log_node_exit(logger, "intent_node", session_id, True, {"intent": intent_code})
            
            # 关键修改：不返回消息内容，让下一个节点来回复
            # 这样避免了两段回复的问题
            return {
                "messages": [],  # 不添加新消息
                "current_stage": "intent",
                "detected_intent": intent_code,
                "intent_confidence": 0.95,
                "gate_passed": True,  # 通过门控
            }
        else:
            # LLM 继续对话
            logger.info(f"[{session_id[:8]}] 💬 继续对话，未锁定意图")
            
            log_node_exit(logger, "intent_node", session_id, False, {"action": "continue_chat"})
            
            return {
                "messages": [AIMessage(content=response_content)],
                "current_stage": "intent",
                "gate_passed": False,  # 继续循环
            }
        
    except Exception as e:
        log_node_error(logger, "intent_node", session_id, e)
        return {
            "messages": [AIMessage(content=f"发生错误: {str(e)}")],
            "current_stage": "intent",
            "gate_passed": False,
        }
