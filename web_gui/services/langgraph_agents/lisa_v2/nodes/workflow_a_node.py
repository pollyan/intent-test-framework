"""
Workflow A Node: 新需求/功能测试设计

使用完整的 Lisa v5.0 工作流 A prompt，让 LLM 自主管理整个测试设计流程 (A1→A2→A3→A4)
"""
from typing import Dict
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..utils.llm_factory import get_llm
from ..utils.logger import logger
from ..prompts.loader import load_v5_workflow_a_prompt


def workflow_a_node(state: LisaState, config: RunnableConfig) -> Dict:
    """
    工作流 A 节点: 新需求/功能测试设计
    
    核心设计:
    1. 使用完整的 v5.0 工作流 A prompt (Section 1 + 2 + 4.2)
    2. LLM 自主管理子阶段推进 (A1→A2→A3→A4)
    3. 通过对话历史保持上下文连续性
    4. 不需要显式的状态管理和门控
    
    Args:
        state: LangGraph 状态
        config: Runnable 配置
        
    Returns:
        状态更新字典,包含 LLM 响应
    """
    session_id = state["session_id"]
    
    try:
        # 1. 获取 LLM
        llm = get_llm(session_id)
        logger.info(f"[{session_id[:8]}] 🎯 进入工作流 A: 测试设计")
        
        # 2. 加载完整的 v5.0 工作流 A prompt
        system_prompt = load_v5_workflow_a_prompt()
        logger.debug(f"[{session_id[:8]}] 📄 已加载 v5.0 工作流 A prompt ({len(system_prompt)} 字符)")
        
        # 3. 构建消息列表
        # 关键: 保留所有历史消息,不截断
        messages = [
            SystemMessage(content=system_prompt)
        ] + state["messages"]
        
        logger.info(f"[{session_id[:8]}] 📨 消息数量: {len(messages)} (包含 system prompt)")
        
        # 4. 调用 LLM
        response = llm.invoke(messages, config=config)
        logger.info(f"[{session_id[:8]}] ✅ LLM 响应完成 ({len(response.content)} 字符)")
        
        # 5. 返回状态更新
        return {
            "messages": [response]
        }
        
    except Exception as e:
        logger.error(f"[{session_id[:8]}] ❌ 工作流 A 执行错误: {str(e)}")
        error_message = f"抱歉,在执行测试设计流程时遇到了问题: {str(e)}"
        return {
            "messages": [SystemMessage(content=error_message)],
            "error_message": str(e)
        }
