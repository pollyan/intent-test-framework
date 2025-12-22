"""
工作流配置 - 业务命名映射

将抽象的字母代码映射到具体的业务工作流
"""

WORKFLOW_MAP = {
    "TEST_DESIGN": {
        "name": "新需求/功能测试设计",
        "description": "为一个全新的功能或需求设计完整的测试方案",
        "node_name": "test_design",
    },
    "REQUIREMENT_REVIEW": {
        "name": "需求评审与可测试性分析",
        "description": "审查需求文档，寻找逻辑漏洞、模糊点和不可测试之处",
        "node_name": "requirement_review",  # 待实现
    },
    "DEFECT_ANALYSIS": {
        "name": "生产缺陷分析与回归策略",
        "description": "针对一个已发现的线上问题，进行根因分析并设计回归测试",
        "node_name": "defect_analysis",  # 待实现
    },
    "SPECIALIZED_TESTING": {
        "name": "专项测试策略规划",
        "description": "聚焦于非功能性领域，如性能、安全或自动化",
        "node_name": "specialized_testing",  # 待实现
    },
    "TEST_ASSESSMENT": {
        "name": "产品测试现状评估",
        "description": "对现有的测试现状进行分析、审查和优化建议",
        "node_name": "test_assessment",  # 待实现
    },
    "GENERAL_CONSULTING": {
        "name": "通用测试咨询",
        "description": "其他测试相关问题的开放探讨或咨询",
        "node_name": "general_consulting",  # 待实现
    },
}
