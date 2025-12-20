# Lisa Song 测试专家 v2 - LangGraph 实现

## 📋 概述

Lisa Song v2 是基于 LangGraph 的测试领域智能体，从纯提示词驱动的 v1 迁移而来。

## 🏗️ 架构设计

### 激活机制

**问题**：原始实现中，激活消息（Bundle）作为 `HumanMessage` 混在对话流中，导致：
- 节点需要通过字符串匹配识别激活消息
- 激活逻辑与业务逻辑耦合
- 不符合 LangGraph 最佳实践

**解决方案**：使用状态标志 `is_activated`

```python
# state.py
class LisaState(TypedDict):
    # ...
    is_activated: bool  # 首次交互标志
```

**工作流程**：

1. **会话创建**：`is_activated=False`（默认值）
2. **首次调用**：
   - `intent_node` 检测 `is_activated=False`
   - 返回欢迎语和工作流选择界面
   - 设置 `is_activated=True`
3. **后续交互**：
   - `is_activated=True`
   - 正常进行意图识别和工作流执行

### 优势

✅ **清晰的责任分离**：激活逻辑独立于业务逻辑  
✅ **状态驱动**：通过 State 标志而非内容匹配  
✅ **可扩展**：其他节点也可以利用此标志  
✅ **符合 LangGraph 最佳实践**：使用状态管理而非消息内容判断

## 📂 模块结构

```
lisa_v2/
├── __init__.py
├── README.md           # 本文件
├── state.py            # LisaState 定义（独立于 Alex）
├── graph.py            # 主图和子图定义
├── nodes/              # 节点实现
│   ├── __init__.py
│   ├── intent_node.py          # 意图识别节点
│   ├── clarification_node.py   # 需求澄清节点
│   └── ...
├── prompts/            # 提示词管理
│   ├── __init__.py
│   ├── core.py         # 核心 Persona
│   ├── intent.py       # 意图识别提示词
│   └── ...
└── utils/              # 工具函数
    ├── __init__.py
    ├── gate_check.py       # 门控和路由
    ├── metadata_parser.py  # 元数据解析
    ├── logger.py           # 日志工具
    └── llm_factory.py      # LLM 实例创建
```

## 🔄 LangGraph 流程

```
START → intent_node → [意图识别]
                        ↓
                    route_after_intent
                        ↓
                    workflow_a (子图)
                        ↓
                    clarification_node → risk_analysis_node → ...
                        ↓
                      END
```

## 🚀 使用方式

### 服务层调用

```python
from web_gui.services.langgraph_agents.service import LangGraphAssistantService

# 创建服务实例
service = LangGraphAssistantService(assistant_type="lisa")
await service.initialize()

# 流式交互（自动处理激活）
async for chunk in service.stream_message(session_id="xxx", user_message="..."):
    print(chunk, end="", flush=True)
```

### 首次交互处理

服务层**无需特殊处理**激活消息：
- 创建新会话时，`is_activated=False`（默认）
- 第一次调用 `stream_message` 时，`intent_node` 自动返回欢迎语
- 后续调用正常执行意图识别

## 🔍 LangSmith 追踪

Lisa v2 完全集成了 LangSmith（LangChain 官方可观测性平台），支持对所有 LLM 调用进行追踪和调试。

### 快速配置

1. 访问 [https://smith.langchain.com/](https://smith.langchain.com/) 并注册（免费）
2. 获取 API Key（Settings → API Keys）
3. 在 `.env` 中配置：
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_api_key_here
   LANGCHAIN_PROJECT=intent-test-framework
   ```
4. 重启服务：`docker-compose down && docker-compose up -d`

### 追踪内容

- **所有 LLM 调用**：输入、输出、Token 使用、延迟
- **LangGraph 工作流**：节点执行顺序、状态传递、路由决策
- **会话上下文**：session_id、tags（`lisa`、`langgraph`）、metadata

### 查看追踪

访问 [https://smith.langchain.com/](https://smith.langchain.com/)，选择你的项目（`intent-test-framework`），筛选：
- `tag:lisa` - 只看 Lisa 的追踪
- `metadata.session_id` - 追踪特定会话

详细指南：
- **[LangSmith 集成指南](../../../../docs/langsmith-integration.md)** - 完整配置和高级用法

## 📝 开发指南

### 添加新节点

1. 在 `nodes/` 下创建 `your_node.py`
2. 实现节点函数（**重要**：接收 `config` 参数以支持 LangSmith 追踪）：
   ```python
   from typing import Optional
   from langchain_core.runnables import RunnableConfig
   
   def your_node(state: LisaState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
       """节点描述"""
       
       # 调用 LLM 时传递 config（启用 LangSmith 追踪）
       response = llm.invoke([HumanMessage(content=prompt)], config=config)
       
       return {
           "messages": [AIMessage(content=response.content)],
           "your_field": value,
       }
   ```
3. 在 `graph.py` 中注册节点

### 添加新提示词

1. 在 `prompts/` 下创建 `your_prompt.py`
2. 定义提示词常量
3. 在节点中组合使用（Core Prompt + 专用 Prompt）

### 调试建议

- **查看日志**：`docker logs intent-test-web --tail 100 -f`
- **检查状态**：在节点函数中打印 `state` 内容
- **追踪流程**：关注 `route_after_intent` 等路由函数的日志
- **使用 LangSmith**：查看完整的 LLM 调用链和 Token 使用情况

## 🔗 相关文档

- [架构决策文档](../../../../_bmad-output/lisa-langgraph-enhancement/architecture-lisa-langgraph.md)
- [原始 Prompt v5.0](../../../../intelligent-requirements-analyzer/dist/testmaster-song-bundlev5.0.md)
- [PRD 文档](../../../../_bmad-output/lisa-langgraph-enhancement/prd-lisa-langgraph-2025-12-19.md)
- **[LangSmith 集成指南](../../../../docs/langsmith-integration.md)** - 调试和追踪

## 🏆 最佳实践

1. **状态驱动**：用状态标志而非消息内容判断
2. **分层提示词**：Core + Node-specific
3. **结构化输出**：LLM 返回 JSON，代码解析
4. **独立模块**：不影响 Alex 智能体
5. **日志完整**：每个节点记录进入/退出日志
6. **传递 config**：所有 LLM 调用都传递 `config` 参数以启用追踪

---

**版本**：v2.0  
**作者**：BMAD Team  
**最后更新**：2025-12-19

