"""
测试用例设计节点：详细测试设计与用例编写
"""

import re
from typing import Dict, Optional, List
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.builder import build_test_case_design_prompt
from ..utils.llm_helper import get_llm_with_error_handling, invoke_llm_with_validation
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit

logger = get_lisa_logger()

# 阶段常量
CURRENT_STAGE = "TEST_CASE_DESIGN"
REQUIREMENT_CLARIFICATION = "REQUIREMENT_CLARIFICATION"
RISK_ANALYSIS = "RISK_ANALYSIS"


def test_case_design_node(
    state: LisaState, 
    config: Optional[RunnableConfig] = None
) -> Dict:
    """
    测试用例设计阶段：详细测试设计与用例编写
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "test_case_design_node", session_id, CURRENT_STAGE)
    
    try:
        # 1. 获取 LLM
        llm, error = get_llm_with_error_handling(session_id, CURRENT_STAGE)
        if error:
            return error
        
        # 2. 组装 Prompt
        context = {
            "previous_output": _format_strategy(state.get("test_strategy")),
            "requirement_summary": state.get("requirement_summary"),
            "current_status": "测试用例设计阶段",
        }
        prompt = build_test_case_design_prompt(context)
        
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
        test_cases = None
        if stage not in [REQUIREMENT_CLARIFICATION, RISK_ANALYSIS, CURRENT_STAGE]:  # 前进到交付阶段
            test_cases = _extract_test_cases(response_content)
        
        # 7. 记录决策
        logger.info(f"[{session_id[:8]}] 🤖 LLM 决策: STAGE={stage}, ACTION={action}")
        
        # 8. 清理响应
        clean_content = _clean_response(response_content)
        
        log_node_exit(logger, "test_case_design_node", session_id, 
                     stage != CURRENT_STAGE, {"stage": stage, "action": action})
        
        return {
            "messages": [AIMessage(content=clean_content)],
            "test_cases": test_cases,
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


def _format_strategy(strategy: Optional[Dict]) -> str:
    """格式化风险分析阶段的策略输出"""
    if not strategy:
        return "未提供"
    return strategy.get("content", str(strategy))


def _extract_stage_and_action(response: str) -> tuple[str, Optional[str]]:
    """提取状态标记"""
    match = re.search(
        r'<!--\s*STAGE:\s*(\w+)(?:\s*\|\s*ACTION:\s*(\w+))?\s*-->', 
        response
    )
    if match:
        return match.group(1), match.group(2) if match.lastindex >= 2 else None
    return CURRENT_STAGE, None


def _extract_test_cases(response: str) -> Optional[List[Dict]]:
    """提取测试用例"""
    return [{
        "content": response,
        "extracted_at": "TEST_CASE_DESIGN_completion",
    }]


def _clean_response(response: str) -> str:
    """清理 HTML 注释"""
    cleaned = re.sub(r'<!--.*?-->', '', response, flags=re.DOTALL)
    return cleaned.strip()
