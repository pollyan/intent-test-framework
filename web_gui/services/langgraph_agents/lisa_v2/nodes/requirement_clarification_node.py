"""
需求澄清节点：需求澄清与分解

完全由 LLM 驱动，使用 HTML 注释标记管理状态。
"""

import re
from typing import Dict, Optional
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.builder import build_requirement_clarification_prompt
from ..utils.llm_helper import get_llm_with_error_handling, invoke_llm_with_validation
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit

logger = get_lisa_logger()

# 阶段常量
CURRENT_STAGE = "REQUIREMENT_CLARIFICATION"


def requirement_clarification_node(
    state: LisaState, 
    config: Optional[RunnableConfig] = None
) -> Dict:
    """
    需求澄清阶段节点
    
    Args:
        state: 当前状态
        config: LangChain 配置
        
    Returns:
        更新后的状态
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "requirement_clarification_node", session_id, CURRENT_STAGE)
    
    try:
        # 1. 获取 LLM
        llm, error = get_llm_with_error_handling(session_id, "requirement_clarification")
        if error:
            return error
        
        # 2. 组装 Prompt（3 层自动合并）
        context = {
            "previous_output": None,  # 无前置阶段
            "requirement_summary": state.get("requirement_summary"),
            "current_status": "需求澄清阶段",
        }
        prompt = build_requirement_clarification_prompt(context)
        
        # 3. 构建消息
        messages = [SystemMessage(content=prompt)] + state["messages"][-15:]
        
        # 4. 调用 LLM
        response_content, error = invoke_llm_with_validation(
            llm, messages, session_id, "requirement_clarification", config
        )
        if error:
            return error
        
        # 5. 解析状态标记
        stage, action = _extract_stage_and_action(response_content)
        
        # 6. 提取产出物（如果完成了当前阶段）
        checklist = None
        if stage != CURRENT_STAGE:
            checklist = _extract_clarification_checklist(response_content)
        
        # 7. 记录 LLM 决策
        logger.info(f"[{session_id[:8]}] 🤖 LLM 决策: STAGE={stage}, ACTION={action}")
        
        # 8. 清理响应（移除 HTML 注释）
        clean_content = _clean_response(response_content)
        
        log_node_exit(logger, "requirement_clarification_node", session_id, 
                     stage != CURRENT_STAGE, {"stage": stage, "action": action})
        
        return {
            "messages": [AIMessage(content=clean_content)],
            "clarification_checklist": checklist,
            "workflow_stage": stage,
            "workflow_action": action,
            "gate_passed": stage != CURRENT_STAGE,
        }
        
    except Exception as e:
        logger.error(f"[{session_id[:8]}] 节点异常: {e}")
        return {
            "messages": [AIMessage(content=f"抱歉，发生了错误: {str(e)}")],
            "workflow_stage": CURRENT_STAGE,
            "gate_passed": False,
        }


def _extract_stage_and_action(response: str) -> tuple[str, Optional[str]]:
    """
    从 LLM 响应中提取状态标记
    
    Args:
        response: LLM 的响应内容
        
    Returns:
        (stage, action) 元组
    """
    # 提取 <!-- STAGE: XX | ACTION: xx -->
    match = re.search(
        r'<!--\s*STAGE:\s*(\w+)(?:\s*\|ACTION:\s*(\w+))?\s*-->', 
        response
    )
    
    if match:
        stage = match.group(1)
        action = match.group(2) if match.lastindex >= 2 else None
        return stage, action
    
    # 没有找到标记，默认保持当前阶段
    return CURRENT_STAGE, None


def _extract_clarification_checklist(response: str) -> Optional[Dict]:
    """
    从响应中提取需求澄清清单
    
    Args:
        response: LLM 响应
        
    Returns:
        结构化的清单字典
    """
    return {
        "content": response,
        "extracted_at": "requirement_clarification_completion",
    }


def _clean_response(response: str) -> str:
    """
    清理响应，移除 HTML 注释标记
    
    Args:
        response: 原始响应
        
    Returns:
        清理后的响应
    """
    # 移除所有 HTML 注释
    cleaned = re.sub(r'<!--.*?-->', '', response, flags=re.DOTALL)
    return cleaned.strip()
