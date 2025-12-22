"""
测试设计工作流阶段 Prompt (Layer 2)

定义 4 个阶段的专用 Prompt：
- 需求澄清: 需求澄清与分解
- 风险分析: 风险分析与策略制定
- 测试用例设计: 详细测试设计与用例编写
- 交付: 评审与交付
"""

from .requirement_clarification import REQUIREMENT_CLARIFICATION_STAGE
from .risk_analysis import RISK_ANALYSIS_STAGE
from .test_case_design import TEST_CASE_DESIGN_STAGE
from .delivery import DELIVERY_STAGE

__all__ = [
    "REQUIREMENT_CLARIFICATION_STAGE",
    "RISK_ANALYSIS_STAGE",
    "TEST_CASE_DESIGN_STAGE",
    "DELIVERY_STAGE",
]
