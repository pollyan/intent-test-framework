"""
Lisa v2 LangGraph 图结构

扁平化架构：所有节点直接添加到主图，避免子图递归问题
"""

import re
from typing import Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import LisaState
from .nodes.intent_node import intent_node
from .nodes.requirement_clarification_node import requirement_clarification_node
from .nodes.risk_analysis_node import risk_analysis_node
from .nodes.test_case_design_node import test_case_design_node
from .nodes.delivery_node import delivery_node
from .utils.logger import get_lisa_logger

logger = get_lisa_logger()

# 阶段到节点的映射
STAGE_TO_NODE = {
    "REQUIREMENT_CLARIFICATION": "requirement_clarification",
    "RISK_ANALYSIS": "risk_analysis",
    "TEST_CASE_DESIGN": "test_case_design",
    "DELIVERY": "delivery",
    "COMPLETED": "end",
}


def route_after_intent(state: LisaState) -> Literal["requirement_clarification", "end"]:
    """
    意图识别后的路由
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    # 检查门控：如果未通过，结束本轮
    if not state.get("gate_passed"):
        return "end"
    
    detected_intent = state.get("detected_intent")
    
    # MVP 只实现测试设计工作流
    if detected_intent == "TEST_DESIGN":
        logger.info("路由到测试设计工作流")
        return "requirement_clarification"
    
    # 其他工作流暂时直接结束
    return "end"


def route_test_design_workflow(state: LisaState) -> str:
    """
    测试设计工作流路由 - 完全基于 LLM 的状态标记
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    # 检查门控：如果未通过（保持当前阶段），结束本轮
    if not state.get("gate_passed", False):
        logger.info("🚫 门控未通过，结束本轮对话")
        return "end"
    
    # 从 workflow_stage 获取目标阶段
    target_stage = state.get("workflow_stage")
    
    # 如果 workflow_stage 未设置，尝试从最后一条消息解析
    if not target_stage and state.get("messages"):
        last_message = state["messages"][-1].content if state["messages"] else ""
        match = re.search(r'<!-- STAGE: (\w+)', last_message)
        if match:
            target_stage = match.group(1)
    
    # 如果仍然没有找到目标阶段，结束对话
    if not target_stage:
        logger.warning("未找到 workflow_stage，结束对话")
        return "end"
    
    # 检查是否已完成
    if target_stage == "COMPLETED":
        logger.info("✅ 工作流已完成")
        return "end"
    
    # 记录决策
    action = state.get("workflow_action")
    action_str = f", ACTION={action}" if action else ""
    logger.info(f"🔀 路由决策: STAGE={target_stage}{action_str}")
    
    # 映射到节点
    next_node = STAGE_TO_NODE.get(target_stage, "end")
    
    return next_node


def create_lisa_v2_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    创建 Lisa v2 主图 - 扁平化结构
    
    图结构：
    START → intent_node ──► requirement_clarification ──► risk_analysis ──► test_case_design ──► delivery → END
                     ↓
                    end
    
    Args:
        checkpointer: 可选的检查点保存器
        
    Returns:
        编译后的图
    """
    builder = StateGraph(LisaState)
    
    # 添加所有节点（扁平化，不使用子图）
    builder.add_node("intent_node", intent_node)
    builder.add_node("requirement_clarification", requirement_clarification_node)
    builder.add_node("risk_analysis", risk_analysis_node)
    builder.add_node("test_case_design", test_case_design_node)
    builder.add_node("delivery", delivery_node)
    
    # 定义边
    builder.add_edge(START, "intent_node")
    
    # 意图识别后的条件路由
    builder.add_conditional_edges(
        "intent_node",
        route_after_intent,
        {
            "requirement_clarification": "requirement_clarification",
            "end": END,
        }
    )
    
    # 工作流节点的条件路由（支持任意跳转和回退）
    for node_name in ["requirement_clarification", "risk_analysis", "test_case_design", "delivery"]:
        builder.add_conditional_edges(
            node_name,
            route_test_design_workflow,
            {
                "requirement_clarification": "requirement_clarification",
                "risk_analysis": "risk_analysis",
                "test_case_design": "test_case_design",
                "delivery": "delivery",
                "end": END,
            }
        )
    
    # 编译图
    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    
    return builder.compile()
