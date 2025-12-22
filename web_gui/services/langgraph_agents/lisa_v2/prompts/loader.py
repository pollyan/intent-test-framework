"""
Prompt loader for Lisa v5.0 workflows
"""
import os
from typing import Dict

def load_v5_workflow_a_prompt() -> str:
    """
    加载工作流 A: 新需求/功能测试设计的完整 v5.0 prompt
    
    Returns:
        str: 完整的 system prompt
    """
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "v5_workflows",
        "workflow_a.txt"
    )
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def load_v5_workflow_f_prompt() -> str:
    """
    加载工作流 F: 通用测试咨询的完整 v5.0 prompt
    
    Returns:
        str: 完整的 system prompt
    """
    # TODO: 后续实现
    # 目前先返回基础配置
    return load_v5_workflow_a_prompt()  # Temporary fallback
