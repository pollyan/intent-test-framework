"""
Lisa v2 LangGraph 图结构 - 简化版

架构: Intent Node → Workflow Nodes → END
每个 Workflow 使用完整的 v5.0 prompt,LLM 自主管理内部流程
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import LisaState
from .nodes.intent_node import intent_node
from .nodes.workflow_a_node import workflow_a_node
from .utils.logger import get_lisa_logger

logger = get_lisa_logger()


def route_after_intent(state: LisaState) -> Literal["workflow_a", "end"]:
    """
    意图识别后的路由
    
    根据识别的意图,路由到对应的工作流节点:
    - TEST_DESIGN → workflow_a (测试设计工作流)
    - 其他 → end (暂未实现)
    """
    # 检查门控：如果未通过，结束本轮
    if not state.get("gate_passed"):
        logger.info("门控未通过,结束流程")
        return "end"
    
    detected_intent = state.get("detected_intent")
    
    # 路由到测试设计工作流
    if detected_intent == "TEST_DESIGN":
        logger.info("🎯 路由到工作流 A: 测试设计")
        return "workflow_a"
    
    # 其他工作流暂未实现
    logger.info(f"意图 '{detected_intent}' 对应的工作流暂未实现")
    return "end"


def create_lisa_graph(checkpointer: BaseCheckpointSaver = None) -> StateGraph:
    """
    创建 Lisa v2 LangGraph
    
    简化架构:
    - 意图识别节点: 识别用户意图 (TEST_DESIGN / CONSULTATION 等)
    - 工作流 A 节点: 使用完整 v5.0 prompt,LLM 自主管理 A1→A2→A3→A4
    - 其他工作流节点: 后续扩展
    
    Args:
        checkpointer: 可选的检查点保存器
        
    Returns:
        编译后的 LangGraph
    """
    # 创建图
    graph = StateGraph(LisaState)
    
    # 添加节点
    graph.add_node("intent", intent_node)
    graph.add_node("workflow_a", workflow_a_node)
    
    # 设置入口点
    graph.set_entry_point("intent")
    
    # 添加条件边: intent → workflow_a / end
    graph.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "workflow_a": "workflow_a",
            "end": END
        }
    )
    
    # workflow_a 执行完就结束
    graph.add_edge("workflow_a", END)
    
    # 编译
    logger.info("✅ Lisa v2 图结构已创建 (简化版: 3 节点)")
    return graph.compile(checkpointer=checkpointer)
