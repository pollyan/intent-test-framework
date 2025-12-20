"""
阶段门控检查函数

实现混合策略：LLM 输出 + 代码级验证
"""

from typing import Literal
from ..state import LisaState


# 阶段到产出物字段的映射
STAGE_OUTPUT_MAP = {
    "clarification": "clarification_output",
    "risk_analysis": "risk_analysis_output",
    "test_design": "test_design_output",
    "review": "review_output",
}

# 阶段转换映射
STAGE_TRANSITIONS = {
    "intent": "clarification",
    "clarification": "risk_analysis",
    "risk_analysis": "test_design",
    "test_design": "review",
    "review": "done",
}


def gate_check(state: LisaState) -> Literal["pass", "stay"]:
    """
    门控检查函数
    
    双重验证：
    1. 检查当前阶段的产出物是否存在
    2. 检查 LLM 标记的门控状态
    
    Args:
        state: 当前状态
        
    Returns:
        "pass" - 可以进入下一阶段
        "stay" - 保持在当前阶段
    """
    current_stage = state.get("current_stage", "intent")
    
    # 意图阶段特殊处理：只要识别到意图且置信度高就通过
    if current_stage == "intent":
        detected_intent = state.get("detected_intent")
        confidence = state.get("intent_confidence", 0)
        if detected_intent and confidence >= 0.8:
            return "pass"
        return "stay"
    
    # 其他阶段：检查产出物是否存在
    output_key = STAGE_OUTPUT_MAP.get(current_stage)
    if output_key and not state.get(output_key):
        return "stay"
    
    # 检查 LLM 标记的门控状态
    if state.get("gate_passed"):
        return "pass"
    
    return "stay"


def get_next_stage(current_stage: str) -> str:
    """
    获取下一阶段
    
    Args:
        current_stage: 当前阶段
        
    Returns:
        下一阶段名称
    """
    return STAGE_TRANSITIONS.get(current_stage, "done")


def route_by_intent(state: LisaState) -> str:
    """
    根据意图路由到对应工作流
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    detected_intent = state.get("detected_intent")
    confidence = state.get("intent_confidence", 0)
    
    # 意图不清晰，需要澄清
    if not detected_intent or confidence < 0.8:
        return "clarify_intent"
    
    # MVP 只实现工作流 A
    if detected_intent == "A":
        return "workflow_a"
    
    # 其他工作流暂未实现，返回占位
    return "workflow_placeholder"


def route_by_gate(state: LisaState) -> str:
    """
    根据门控状态路由
    
    Args:
        state: 当前状态
        
    Returns:
        "next" - 进入下一阶段
        "stay" - 保持当前阶段
    """
    result = gate_check(state)
    return "next" if result == "pass" else "stay"

