"""
Lisa v2 工作流配置

定义所有可用的工作流及其元数据
"""

# 工作流映射表：意图代码 → 工作流信息
WORKFLOW_MAP = {
    "TEST_DESIGN": {
        "code": "TEST_DESIGN",
        "name": "新需求/功能测试设计",
        "description": "为全新的功能或需求设计完整的测试方案",
        "node": "workflow_a",  # 对应的节点名称
    },
    "REQUIREMENT_REVIEW": {
        "code": "REQUIREMENT_REVIEW",
        "name": "需求评审与可测试性分析",
        "description": "审查需求文档，识别逻辑漏洞、模糊点和不可测试之处",
        "node": "workflow_b",  # 暂未实现
    },
    "DEFECT_ANALYSIS": {
        "code": "DEFECT_ANALYSIS",
        "name": "生产缺陷分析与回归策略",
        "description": "针对线上问题进行根因分析并设计回归测试",
        "node": "workflow_c",  # 暂未实现
    },
    "SPECIALIZED_TESTING": {
        "code": "SPECIALIZED_TESTING",
        "name": "专项测试策略规划",
        "description": "性能、安全、自动化等专项测试策略",
        "node": "workflow_d",  # 暂未实现
    },
    "TEST_ASSESSMENT": {
        "code": "TEST_ASSESSMENT",
        "name": "产品测试现状评估",
        "description": "分析和优化现有测试体系",
        "node": "workflow_e",  # 暂未实现
    },
    "GENERAL_CONSULTING": {
        "code": "GENERAL_CONSULTING",
        "name": "通用测试咨询",
        "description": "开放式的测试咨询和讨论",
        "node": "workflow_general",  # 暂未实现
    },
}


def get_workflow_info(intent_code: str) -> dict:
    """
    根据意图代码获取工作流信息
    
    Args:
        intent_code: 意图代码（如 TEST_DESIGN）
        
    Returns:
        工作流信息字典
    """
    return WORKFLOW_MAP.get(intent_code, WORKFLOW_MAP["GENERAL_CONSULTING"])


def get_node_name(intent_code: str) -> str:
    """
    根据意图代码获取对应的节点名称
    
    Args:
        intent_code: 意图代码（如 TEST_DESIGN）
        
    Returns:
        节点名称（如 workflow_a）
    """
    workflow_info = get_workflow_info(intent_code)
    return workflow_info.get("node", "workflow_general")
