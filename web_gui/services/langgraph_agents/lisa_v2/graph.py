"""
Lisa v2 LangGraph 图结构

实现混合模式：
- 主图处理意图识别和工作流路由
- 子图实现具体工作流 (MVP 只实现工作流 A)
"""

from typing import Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import LisaState
from .nodes.intent_node import intent_node
from .nodes.clarification_node import clarification_node
from .utils.gate_check import gate_check, route_by_intent
from .utils.logger import get_lisa_logger

logger = get_lisa_logger()


def route_after_intent(state: LisaState) -> Literal["workflow_a", "end"]:
    """
    意图识别后的路由
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    # 检查门控：如果未通过，结束本轮，等待用户下一次输入
    if not state.get("gate_passed"):
        return "end"
    
    detected_intent = state.get("detected_intent")
    
    # MVP 只实现工作流 A
    if detected_intent == "A":
        return "workflow_a"
    
    # 其他工作流暂时直接结束
    return "end"


def route_in_workflow_a(state: LisaState) -> Literal["clarification_node", "end"]:
    """
    工作流 A 内部路由
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    current_stage = state.get("current_stage", "clarification")
    gate_passed = state.get("gate_passed", False)
    
    if current_stage == "clarification" and not gate_passed:
        return "clarification_node"
    
    # MVP 版本：完成 clarification 后直接结束
    # 后续版本可以扩展到 risk_analysis, test_design, review
    return "end"


def create_workflow_a_subgraph() -> StateGraph:
    """
    创建工作流 A 子图
    
    工作流 A: 新需求/功能测试设计
    - clarification_node: 需求澄清 (MVP 实现)
    - risk_analysis_node: 风险分析 (TODO)
    - test_design_node: 测试设计 (TODO)
    - review_node: 评审交付 (TODO)
    
    Returns:
        配置好的子图
    """
    builder = StateGraph(LisaState)
    
    # 添加节点
    builder.add_node("clarification_node", clarification_node)
    
    # 定义边
    builder.add_edge(START, "clarification_node")
    
    # 条件边：根据门控状态决定是否继续
    builder.add_conditional_edges(
        "clarification_node",
        route_in_workflow_a,
        {
            "clarification_node": "clarification_node",
            "end": END,
        }
    )
    
    return builder


def create_lisa_v2_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> StateGraph:
    """
    创建 Lisa v2 主图
    
    图结构：
    START → intent_node ──条件边──► workflow_a_subgraph → END
                          ╲
                           ╲──► end (其他工作流暂未实现)
    
    Args:
        checkpointer: 可选的检查点保存器
        
    Returns:
        编译后的图
    """
    builder = StateGraph(LisaState)
    
    # 添加意图识别节点
    builder.add_node("intent_node", intent_node)
    
    # 添加工作流 A 子图
    workflow_a_graph = create_workflow_a_subgraph()
    builder.add_node("workflow_a", workflow_a_graph.compile())
    
    # 定义边
    builder.add_edge(START, "intent_node")
    
    # 意图识别后的条件路由
    builder.add_conditional_edges(
        "intent_node",
        route_after_intent,
        {
            "workflow_a": "workflow_a",
            "end": END,
        }
    )
    
    # 工作流 A 完成后结束
    builder.add_edge("workflow_a", END)
    
    # 编译图
    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    
    return builder.compile()


def get_lisa_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    获取 Lisa v2 图实例（兼容旧 API）
    
    Args:
        checkpointer: 可选的检查点保存器
        
    Returns:
        编译后的图
    """
    return create_lisa_v2_graph(checkpointer)

