"""
交付节点：评审与交付
"""

import re
from typing import Dict, Optional
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.builder import build_delivery_prompt
from ..utils.llm_helper import get_llm_with_error_handling, invoke_llm_with_validation
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit

logger = get_lisa_logger()

# 阶段常量
CURRENT_STAGE = "DELIVERY"


def delivery_node(
    state: LisaState, 
    config: Optional[RunnableConfig] = None
) -> Dict:
    """
    交付阶段：评审与交付
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "delivery_node", session_id, CURRENT_STAGE)
    
    try:
        # 1. 获取 LLM
        llm, error = get_llm_with_error_handling(session_id, CURRENT_STAGE)
        if error:
            return error
        
        # 2. 组装 Prompt
        context = {
            "previous_output": _format_all_outputs(state),
            "requirement_summary": state.get("requirement_summary"),
            "current_status": "最终交付阶段",
        }
        prompt = build_delivery_prompt(context)
        
        # 3. 构建消息
        messages = [SystemMessage(content=prompt)] + state["messages"][-15:]
        
        # 4. 调用 LLM
        response_content, error = invoke_llm_with_validation(
            llm, messages, session_id, CURRENT_STAGE, config
        )
        if error:
            return error
        
        # 5. 解析状态标记
        stage, action = _extract_stage_and_action(response_content)
        
        # 6. 提取产出物
        final_doc = None
        if stage == "COMPLETED":
            final_doc = response_content
        
        # 7. 记录决策
        logger.info(f"[{session_id[:8]}] 🤖 LLM 决策: STAGE={stage}, ACTION={action}")
        
        # 8. 清理响应
        clean_content = _clean_response(response_content)
        
        log_node_exit(logger, "delivery_node", session_id, 
                     stage == "COMPLETED", {"stage": stage, "action": action})
        
        return {
            "messages": [AIMessage(content=clean_content)],
            "final_document": final_doc,
            "workflow_stage": stage,
            "workflow_action": action,
            "gate_passed": stage == "COMPLETED",
        }
        
    except Exception as e:
        logger.error(f"[{session_id[:8]}] 节点异常: {e}")
        return {
            "messages": [AIMessage(content=f"抱歉，发生了错误: {str(e)}")],
            "workflow_stage": CURRENT_STAGE,
            "gate_passed": False,
        }


def _format_all_outputs(state: LisaState) -> str:
    """格式化所有前置阶段的产出物"""
    sections = []
    
    # 需求澄清
    if checklist := state.get("clarification_checklist"):
        sections.append(f"**需求澄清清单**:\n{checklist.get('content', '')}")
    
    # 风险分析
    if strategy := state.get("test_strategy"):
        sections.append(f"**测试策略**:\n{strategy.get('content', '')}")
    
    # 测试用例
    if test_cases := state.get("test_cases"):
        if test_cases:
            sections.append(f"**测试用例**:\n{test_cases[0].get('content', '')}")
    
    return "\n\n---\n\n".join(sections) if sections else "未提供"


def _extract_stage_and_action(response: str) -> tuple[str, Optional[str]]:
    """提取状态标记"""
    match = re.search(
        r'<!--\s*STAGE:\s*(\w+)(?:\s*\|\s*ACTION:\s*(\w+))?\s*-->', 
        response
    )
    if match:
        return match.group(1), match.group(2) if match.lastindex >= 2 else None
    return CURRENT_STAGE, None


def _clean_response(response: str) -> str:
    """清理 HTML 注释"""
    cleaned = re.sub(r'<!--.*?-->', '', response, flags=re.DOTALL)
    return cleaned.strip()
