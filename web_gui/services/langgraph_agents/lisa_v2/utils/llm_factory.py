"""
LLM 工厂 - 从数据库配置创建 LLM 实例
"""

import logging
from typing import Optional
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


_cached_llm = None
_cached_config_id = None


def get_llm_from_db() -> Optional[ChatOpenAI]:
    """
    从数据库获取默认 AI 配置并创建 LLM 实例
    
    Returns:
        ChatOpenAI 实例，如果配置不存在则返回 None
    """
    global _cached_llm, _cached_config_id
    
    try:
        # 延迟导入，避免循环依赖
        from web_gui.models import RequirementsAIConfig
        
        # 获取默认配置
        default_config = RequirementsAIConfig.get_default_config()
        
        if not default_config:
            logger.warning("未找到默认 AI 配置")
            return None
        
        # 检查缓存
        if _cached_llm and _cached_config_id == default_config.id:
            logger.debug(f"使用缓存的 LLM (config_id={_cached_config_id})")
            return _cached_llm
        
        # 获取配置信息
        config_data = default_config.get_config_for_ai_service()
        api_key = config_data.get("api_key")
        base_url = config_data.get("base_url")
        model_name = config_data.get("model_name")
        
        if not all([api_key, base_url, model_name]):
            logger.error("AI 配置不完整")
            return None
        
        # 创建 LLM 实例
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=0.7,
            streaming=True  # 启用流式输出
        )
        
        # 更新缓存
        _cached_llm = llm
        _cached_config_id = default_config.id
        
        logger.info(f"✅ LLM 初始化成功: {model_name} @ {base_url}")
        return llm
        
    except Exception as e:
        logger.error(f"从数据库创建 LLM 失败: {e}")
        return None


def clear_llm_cache():
    """清除 LLM 缓存（配置更新后调用）"""
    global _cached_llm, _cached_config_id
    _cached_llm = None
    _cached_config_id = None
    logger.info("LLM 缓存已清除")

