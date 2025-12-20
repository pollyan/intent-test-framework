"""
Lisa v2 提示词模块

分层组合设计：
- core.py: 核心人格 (Persona + Style + Principles)
- 各阶段文件: 节点专用指令
"""

from .core import LISA_CORE_PROMPT, LISA_PERSONA, LISA_STYLE, LISA_PRINCIPLES

__all__ = [
    "LISA_CORE_PROMPT",
    "LISA_PERSONA",
    "LISA_STYLE",
    "LISA_PRINCIPLES",
]

