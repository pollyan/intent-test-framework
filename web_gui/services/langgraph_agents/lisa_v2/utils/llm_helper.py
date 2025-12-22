"""
LLM 调用辅助函数

提供统一的 LLM 调用包装，处理常见的错误和验证逻辑
"""

from typing import Optional, Dict, List, Tuple
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from .logger import get_lisa_logger
from .llm_factory import get_llm_from_db

logger = get_lisa_logger()


def get_llm_with_error_handling(
    session_id: str,
    current_stage: str
) -> Tuple[Optional[ChatOpenAI], Optional[Dict]]:
    """
    获取 LLM，并处理错误情况
    
    Args:
        session_id: 会话 ID
        current_stage: 当前阶段名称
        
    Returns:
        (llm, error_response) 元组
        - 如果成功：(llm实例, None)
        - 如果失败：(None, 错误响应字典)
    """
    llm = get_llm_from_db()
    
    if not llm:
        logger.error(f"[{session_id[:8]}] LLM 未配置！")
        return None, {
            "messages": [AIMessage(content="抱歉，AI 服务未配置。请联系管理员。")],
            "current_stage": current_stage,
            "gate_passed": False,
        }
    
    return llm, None


def invoke_llm_with_validation(
    llm: ChatOpenAI,
    messages: List[BaseMessage],
    session_id: str,
    current_stage: str,
    config: Optional[RunnableConfig] = None
) -> Tuple[Optional[str], Optional[Dict]]:
    """
    调用 LLM 并验证响应
    
    Args:
        llm: LLM 实例
        messages: 消息列表
        session_id: 会话 ID
        current_stage: 当前阶段
        config: LangChain 配置
        
    Returns:
        (response_content, error_response) 元组
        - 如果成功：(响应内容字符串, None)
        - 如果失败：(None, 错误响应字典)
    """
    try:
        logger.info(f"[{session_id[:8]}] 调用 LLM，消息数: {len(messages)}")
        
        ai_response = llm.invoke(messages, config=config)
        
        # 验证响应对象
        if not ai_response or not hasattr(ai_response, 'content'):
            logger.error(f"[{session_id[:8]}] LLM 返回无效响应")
            return None, {
                "messages": [AIMessage(content="抱歉，我暂时无法理解。请再说一次？")],
                "current_stage": current_stage,
                "gate_passed": False,
            }
        
        response_content = ai_response.content
        
        # 验证内容不为空
        if not response_content or not response_content.strip():
            logger.error(f"[{session_id[:8]}] LLM 返回空内容")
            return None, {
                "messages": [AIMessage(content="请问您有什么测试相关的需求吗？")],
                "current_stage": current_stage,
                "gate_passed": False,
            }
        
        logger.info(f"[{session_id[:8]}] LLM 响应长度: {len(response_content)}")
        return response_content, None
        
    except Exception as e:
        logger.error(f"[{session_id[:8]}] LLM 调用失败: {e}")
        return None, {
            "messages": [AIMessage(content="抱歉，我现在遇到了技术问题。请稍后再试。")],
            "current_stage": current_stage,
            "gate_passed": False,
        }


def create_error_response(
    message: str,
    current_stage: str,
    gate_passed: bool = False,
    **extra_fields
) -> Dict:
    """
    创建统一格式的错误响应
    
    Args:
        message: 错误消息
        current_stage: 当前阶段
        gate_passed: 是否通过门控
        **extra_fields: 额外的状态字段
        
    Returns:
        错误响应字典
    """
    response = {
        "messages": [AIMessage(content=message)],
        "current_stage": current_stage,
        "gate_passed": gate_passed,
    }
    response.update(extra_fields)
    return response
