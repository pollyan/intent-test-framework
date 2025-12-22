"""
Lisa v2 状态定义

定义 Agent 的状态结构，用于在节点之间传递信息。
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class LisaState(TypedDict):
    """Lisa Agent 的状态"""
    
    # ========== 基础字段 ==========
    messages: Annotated[List[BaseMessage], add_messages]
    """对话历史"""
    
    session_id: str
    """会话 ID"""
    
    assistant_type: Optional[str]
    """助手类型"""
    
    project_name: Optional[str]
    """项目名称"""
    
    is_activated: Optional[bool]
    """是否已激活（用于首次交互检测）"""
    
    # ========== 意图识别相关 ==========
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
    
    # ============ 测试设计工作流结构化产出物（新设计）============
    requirement_summary: Optional[str]
    """需求概要描述"""
    
    clarification_checklist: Optional[Dict]
    """需求澄清阶段产出：需求澄清清单"""
    
    test_strategy: Optional[Dict]
    """风险分析阶段产出：测试策略蓝图"""
    
    test_cases: Optional[List[Dict]]
    """测试用例设计阶段产出：测试用例集"""
    
    final_document: Optional[str]
    """交付阶段产出：最终测试设计文档"""
    
    # ============ 工作流状态控制 ============
    workflow_stage: Optional[str]
    """工作流当前阶段（REQUIREMENT_CLARIFICATION/RISK_ANALYSIS/TEST_CASE_DESIGN/DELIVERY/COMPLETED）"""
    
    workflow_action: Optional[str]
    """工作流操作（supplement/reopen/modify）"""
    
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

