"""
Lisa v2 状态定义

完全独立于 Alex 的 AssistantState，确保两个智能体之间零耦合。
"""

from typing import TypedDict, Annotated, Sequence, Optional, Dict, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class LisaState(TypedDict):
    """
    Lisa 智能体的状态定义
    
    使用业务含义命名，便于维护和扩展。
    """
    
    # ============ 基础字段 ============
    # 对话历史，使用 add_messages reducer 自动追加
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 会话标识
    session_id: str
    
    # ============ 工作流状态 ============
    # 当前阶段 - 使用业务含义命名
    current_stage: Literal[
        "intent",           # 意图识别阶段
        "clarification",    # 需求澄清阶段 (工作流 A 子阶段 1)
        "risk_analysis",    # 风险分析阶段 (工作流 A 子阶段 2)
        "test_design",      # 测试设计阶段 (工作流 A 子阶段 3)
        "review",           # 评审交付阶段 (工作流 A 子阶段 4)
        "done"              # 完成
    ]
    
    # 识别到的用户意图 (A-F 工作流)
    detected_intent: Optional[str]
    
    # 意图置信度 (用于决定是否需要澄清)
    intent_confidence: Optional[float]
    
    # ============ 产出物存储 (业务含义命名) ============
    # 需求澄清阶段产出物：《需求澄清与可测试性分析清单》
    clarification_output: Optional[Dict]
    
    # 风险分析阶段产出物：《综合测试策略蓝图》
    risk_analysis_output: Optional[Dict]
    
    # 测试设计阶段产出物：《测试用例集》
    test_design_output: Optional[Dict]
    
    # 评审交付阶段产出物：《测试设计文档》
    review_output: Optional[Dict]
    
    # ============ 门控状态 ============
    # 当前阶段的门控是否通过 (用户确认)
    gate_passed: bool
    
    # ============ 任务进度跟踪 ============
    # 当前讨论的议题列表 (全景-聚焦协议)
    current_agenda: Optional[list]
    
    # 当前聚焦的议题索引
    current_agenda_index: Optional[int]
    
    # ============ 系统状态 ============
    # 是否已激活（首次交互标志）
    is_activated: bool
    
    # ============ 错误处理 ============
    # 错误信息
    error_message: Optional[str]


def create_initial_state(session_id: str, is_activated: bool = False) -> LisaState:
    """
    创建初始状态
    
    Args:
        session_id: 会话标识
        is_activated: 是否已激活（默认 False，首次交互时为 False）
        
    Returns:
        初始化的 LisaState
    """
    return LisaState(
        messages=[],
        session_id=session_id,
        current_stage="intent",
        detected_intent=None,
        intent_confidence=None,
        clarification_output=None,
        risk_analysis_output=None,
        test_design_output=None,
        review_output=None,
        gate_passed=False,
        current_agenda=None,
        current_agenda_index=None,
        is_activated=is_activated,
        error_message=None,
    )

