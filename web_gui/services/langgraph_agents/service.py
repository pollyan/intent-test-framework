"""
LangGraph 智能体服务封装

提供统一的服务接口，支持：
- 多种助手类型（Alex、Lisa 等）
- 流式和非流式对话
- PostgreSQL 持久化检查点
- LangSmith 追踪和观测（通过环境变量自动启用）
"""

import os
import logging
from typing import AsyncIterator, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from .graph import get_graph_for_assistant
from .state import AssistantState

logger = logging.getLogger(__name__)


class LangGraphAssistantService:
    """
    LangGraph 智能体服务
    
    提供基于 LangGraph 的智能助手功能，支持流式对话和检查点持久化。
    """
    
    def __init__(self, assistant_type: str, database_url: Optional[str] = None, use_checkpointer: bool = True):
        """
        初始化 LangGraph 服务
        
        Args:
            assistant_type: 助手类型 ('alex' 或 'lisa')
            database_url: PostgreSQL 数据库连接 URL (可选)
            use_checkpointer: 是否使用检查点持久化 (默认 True)
        """
        self.assistant_type = assistant_type
        self.database_url = database_url
        self.use_checkpointer = use_checkpointer
        self.session_id = None
        self.graph = None
        self.checkpointer = None
        
        logger.info(f"初始化 LangGraph 智能体服务: {assistant_type}")
        
        # LangSmith 追踪（通过环境变量自动启用，无需额外代码）
        if os.getenv('LANGCHAIN_TRACING_V2') == 'true':
            langchain_project = os.getenv('LANGCHAIN_PROJECT', 'intent-test-framework')
            logger.info(f"✅ LangSmith 追踪已启用")
            logger.info(f"   项目: {langchain_project}")
            logger.info(f"   模式: 自动追踪（LangChain 内置）")
        else:
            logger.info("ℹ️ LangSmith 追踪未启用（设置 LANGCHAIN_TRACING_V2=true 启用）")
    
    async def _setup_checkpointer(self):
        """
        设置 PostgreSQL 检查点保存器
        
        使用现有数据库连接字符串。
        """
        if not self.use_checkpointer:
            logger.info("跳过检查点设置（use_checkpointer=False）")
            return None
        
        try:
            # 从环境变量或配置获取数据库连接字符串
            database_url = os.getenv("DATABASE_URL")
            
            if not database_url:
                logger.warning("未找到 DATABASE_URL，使用内存模式")
                return None
            
            # 创建异步 PostgreSQL 检查点保存器
            checkpointer = AsyncPostgresSaver.from_conn_string(database_url)
            
            # 初始化检查点表
            await checkpointer.setup()
            
            logger.info("PostgreSQL 检查点保存器设置完成")
            return checkpointer
            
        except Exception as e:
            logger.error(f"设置检查点保存器失败: {str(e)}")
            logger.warning("降级为内存模式（无状态持久化）")
            return None
    
    async def initialize(self):
        """
        异步初始化服务
        
        必须在使用服务前调用。
        """
        logger.info(f"异步初始化 {self.assistant_type} 智能体服务")
        
        # 设置检查点
        self.checkpointer = await self._setup_checkpointer()
        
        # 创建图
        self.graph = get_graph_for_assistant(
            self.assistant_type,
            checkpointer=self.checkpointer
        )
        
        logger.info(f"{self.assistant_type} 智能体服务初始化完成")
    
    async def process_message(
        self, 
        session_id: str, 
        user_message: str,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息（非流式）
        
        Args:
            session_id: 会话 ID（用作 thread_id）
            user_message: 用户消息内容
            project_name: 可选的项目名称
            
        Returns:
            包含 AI 回复的字典
        """
        if not self.graph:
            await self.initialize()
        
        logger.info(f"处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")
        
        try:
            # 配置（使用 session_id 作为 thread_id）
            # LangSmith 会自动记录所有 LangChain/LangGraph 调用
            config = {
                "configurable": {
                    "thread_id": session_id
                },
                "tags": [self.assistant_type, "langgraph"],
                "metadata": {
                    "session_id": session_id,
                    "project_name": project_name or "default"
                }
            }
            
            # 构建输入
            input_data = {
                "messages": [HumanMessage(content=user_message)],
                "session_id": session_id,
                "assistant_type": self.assistant_type,
                "project_name": project_name,
            }
            
            # 调用图
            result = await self.graph.ainvoke(input_data, config=config)
            
            # 提取 AI 回复
            messages = result.get("messages", [])
            ai_message = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    ai_message = msg.content
                    break
            
            if not ai_message:
                raise ValueError("未能从图中获取 AI 回复")
            
            logger.info(f"消息处理完成，回复长度: {len(ai_message)}")
            
            return {
                "ai_response": ai_message,
                "consensus_content": result.get("consensus_content", {}),
                "analysis_context": result.get("analysis_context", {}),
                "current_stage": result.get("current_stage", "initial"),
            }
            
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
            raise
    
    async def stream_message(
        self, 
        session_id: str, 
        user_message: str,
        project_name: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        处理用户消息（流式响应）
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息内容
            project_name: 可选的项目名称
            
        Yields:
            AI 回复的文本片段
        """
        if not self.graph:
            await self.initialize()
        
        logger.info(f"流式处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")
        logger.info(f"用户消息预览: {user_message[:200]}...")
        
        try:
            # 配置（使用 session_id 作为 thread_id）
            # LangSmith 会自动记录所有 LangChain/LangGraph 调用
            config = {
                "configurable": {
                    "thread_id": session_id
                },
                "tags": [self.assistant_type, "langgraph"],
                "metadata": {
                    "session_id": session_id,
                    "project_name": project_name or "default"
                }
            }
            
            # 构建输入
            input_data = {
                "messages": [HumanMessage(content=user_message)],
                "session_id": session_id,
                "assistant_type": self.assistant_type,
                "project_name": project_name,
            }
            
            # 流式调用图
            has_streamed_content = False
            async for event in self.graph.astream_events(input_data, config=config, version="v2"):
                # 方法1: 提取 LLM 的流式输出（逐字符）
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        has_streamed_content = True
                        yield chunk.content
                
                # 方法2: 捕获节点完成事件（处理静态消息，如 Lisa 的欢迎消息）
                elif event["event"] == "on_chain_end" and not has_streamed_content:
                    # 检查是否有新的 AI 消息输出
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "messages" in output:
                        messages = output["messages"]
                        # 查找最新的 AI 消息
                        for msg in reversed(messages):
                            if isinstance(msg, AIMessage) and msg.content:
                                # 静态消息一次性返回全部内容
                                logger.info(f"检测到静态 AI 消息，长度: {len(msg.content)}")
                                yield msg.content
                                has_streamed_content = True
                                break
            
            logger.info("流式消息处理完成")
            
        except Exception as e:
            logger.error(f"流式处理消息失败: {str(e)}")
            yield f"\n\n错误: {str(e)}"
    
    async def get_session_history(
        self, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        获取会话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话状态字典
        """
        if not self.graph or not self.checkpointer:
            logger.warning("无法获取历史：图或检查点未初始化")
            return {}
        
        try:
            config = {
                "configurable": {
                    "thread_id": session_id
                }
            }
            
            # 获取最新状态
            state = await self.graph.aget_state(config)
            
            return state.values if state else {}
            
        except Exception as e:
            logger.error(f"获取会话历史失败: {str(e)}")
            return {}


# 为了保持兼容，创建别名
RequirementsAIService = LangGraphAssistantService
