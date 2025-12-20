"""
Lisa v2 日志配置

带上下文的日志格式，便于调试追踪
"""

import logging
from typing import Optional


def get_lisa_logger(name: str = "lisa_v2") -> logging.Logger:
    """
    获取 Lisa v2 专用日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def log_node_entry(
    logger: logging.Logger,
    node_name: str,
    session_id: str,
    current_stage: str,
    extra: Optional[dict] = None
) -> None:
    """
    记录节点入口日志
    
    格式: [session_id前8位] node_name: entry, stage=current_stage
    
    Args:
        logger: 日志器
        node_name: 节点名称
        session_id: 会话ID
        current_stage: 当前阶段
        extra: 额外信息
    """
    session_short = session_id[:8] if session_id else "unknown"
    msg = f"[{session_short}] {node_name}: entry, stage={current_stage}"
    
    if extra:
        msg += f", {extra}"
    
    logger.info(msg)


def log_node_exit(
    logger: logging.Logger,
    node_name: str,
    session_id: str,
    gate_passed: bool,
    extra: Optional[dict] = None
) -> None:
    """
    记录节点出口日志
    
    格式: [session_id前8位] node_name: exit, gate=gate_passed
    
    Args:
        logger: 日志器
        node_name: 节点名称
        session_id: 会话ID
        gate_passed: 门控状态
        extra: 额外信息
    """
    session_short = session_id[:8] if session_id else "unknown"
    msg = f"[{session_short}] {node_name}: exit, gate={gate_passed}"
    
    if extra:
        msg += f", {extra}"
    
    logger.info(msg)


def log_node_error(
    logger: logging.Logger,
    node_name: str,
    session_id: str,
    error: Exception
) -> None:
    """
    记录节点错误日志
    
    格式: [session_id前8位] node_name: error - error_message
    
    Args:
        logger: 日志器
        node_name: 节点名称
        session_id: 会话ID
        error: 异常对象
    """
    session_short = session_id[:8] if session_id else "unknown"
    logger.error(f"[{session_short}] {node_name}: error - {str(error)}")

