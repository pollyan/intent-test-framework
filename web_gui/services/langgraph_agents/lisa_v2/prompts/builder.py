"""
Prompt 组装器

统一组装 3 层 Prompt：
- Layer 1: 共享人格（来自 core.py）
- Layer 2: 阶段专用（来自 stages/）
- Layer 3: 动态上下文（运行时注入）
"""

from typing import Dict, Optional
from .core import LISA_SHARED_PROMPT


def build_stage_prompt(
    stage: str,
    context: Optional[Dict] = None,
    stage_prompts: Optional[Dict[str, str]] = None
) -> str:
    """
    组装完整的阶段 Prompt
    
    Args:
        stage: 阶段代码（REQUIREMENT_CLARIFICATION/RISK_ANALYSIS/TEST_CASE_DESIGN/DELIVERY）
        context: 动态上下文字典，包含：
            - previous_output: 前置阶段的产出物
            - current_status: 当前状态描述
            - requirement_summary: 需求摘要
        stage_prompts: 阶段 Prompt 字典（用于注入，测试时可覆盖）
        
    Returns:
        完整的 3 层组合 Prompt
    """
    if context is None:
        context = {}
    
    # Layer 2: 阶段专用 Prompt
    # 如果没有提供 stage_prompts，从 stages 模块导入
    if stage_prompts is None:
        try:
            from .stages import (
                REQUIREMENT_CLARIFICATION_STAGE,
                RISK_ANALYSIS_STAGE,
                TEST_CASE_DESIGN_STAGE,
                DELIVERY_STAGE,
            )
            stage_prompts = {
                "REQUIREMENT_CLARIFICATION": REQUIREMENT_CLARIFICATION_STAGE,
                "RISK_ANALYSIS": RISK_ANALYSIS_STAGE,
                "TEST_CASE_DESIGN": TEST_CASE_DESIGN_STAGE,
                "DELIVERY": DELIVERY_STAGE,
            }
        except ImportError:
            # 如果 stages 模块还未创建，返回基础 Prompt
            stage_prompts = {}
    
    # 获取阶段专用 Prompt（如果没有，使用空字符串）
    stage_prompt = stage_prompts.get(stage, "")
    
    # Layer 3: 动态上下文
    context_section = _build_context_section(context)
    
    # 组装完整 Prompt
    full_prompt = f"""{LISA_SHARED_PROMPT}

---

{stage_prompt}

---

{context_section}
""".strip()
    
    return full_prompt


def _build_context_section(context: Dict) -> str:
    """
    构建动态上下文部分
    
    Args:
        context: 上下文字典
        
    Returns:
        格式化的上下文字符串
    """
    sections = []
    
    sections.append("## 当前上下文")
    
    # 前置产出物
    previous_output = context.get("previous_output")
    if previous_output:
        sections.append(f"""
**前置阶段产出物**:
{previous_output}
""".strip())
    else:
        sections.append("**前置阶段产出物**: 无")
    
    # 需求摘要
    requirement_summary = context.get("requirement_summary")
    if requirement_summary:
        sections.append(f"""
**需求摘要**:
{requirement_summary}
""".strip())
    
    # 当前状态
    current_status = context.get("current_status", "首次进入阶段")
    sections.append(f"""
**当前状态**: {current_status}
""".strip())
    
    return "\n\n".join(sections)


# 便捷函数：为特定阶段构建 Prompt
def build_requirement_clarification_prompt(context: Optional[Dict] = None) -> str:
    """构建需求漄清阶段 Prompt"""
    return build_stage_prompt("REQUIREMENT_CLARIFICATION", context)


def build_risk_analysis_prompt(context: Optional[Dict] = None) -> str:
    """构建风险分析阶段 Prompt"""
    return build_stage_prompt("RISK_ANALYSIS", context)


def build_test_case_design_prompt(context: Optional[Dict] = None) -> str:
    """构建测试用例设计阶段 Prompt"""
    return build_stage_prompt("TEST_CASE_DESIGN", context)


def build_delivery_prompt(context: Optional[Dict] = None) -> str:
    """构建交付阶段 Prompt"""
    return build_stage_prompt("DELIVERY", context)
