"""
Lisa v2 配置模块

包含工作流配置等
"""

from .workflows import WORKFLOW_MAP, get_workflow_info, get_node_name

__all__ = ["WORKFLOW_MAP", "get_workflow_info", "get_node_name"]
