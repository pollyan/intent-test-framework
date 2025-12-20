# LangSmith 集成指南

LangSmith 是 LangChain 官方的 LLM 追踪和调试平台，提供强大的可观测性功能。

## 为什么选择 LangSmith？

1. **官方支持**：LangChain 官方产品，与 LangChain/LangGraph 深度集成
2. **零配置集成**：只需设置环境变量，无需修改代码
3. **完整追踪**：自动捕获所有 LLM 调用、工具调用、Agent 决策
4. **云端服务**：无需自建服务器，开箱即用
5. **优秀的 UI**：直观的追踪可视化、性能分析、错误调试

## 快速开始

### 1. 注册 LangSmith 账号

访问 [https://smith.langchain.com/](https://smith.langchain.com/) 注册账号（免费）。

### 2. 获取 API Key

1. 登录后，点击右上角头像 → **Settings**
2. 左侧菜单选择 **API Keys**
3. 点击 **Create API Key**
4. 复制生成的 API Key

### 3. 配置环境变量

在项目根目录的 `.env` 文件中添加：

```bash
# LangSmith 追踪配置
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=intent-test-framework
```

**环境变量说明**：
- `LANGCHAIN_TRACING_V2=true`：启用 LangSmith 追踪
- `LANGCHAIN_API_KEY`：你的 LangSmith API Key
- `LANGCHAIN_PROJECT`：项目名称（可自定义，用于组织追踪数据）

### 4. 重启应用

```bash
# 重启 Docker 容器以加载新环境变量
cd /Users/anhui/Documents/myProgram/intent-test-framework
docker-compose down
docker-compose up -d
```

### 5. 验证集成

1. 启动应用后，查看日志：
```bash
docker logs intent-test-web --tail 50 -f
```

应该看到：
```
✅ LangSmith 追踪已启用
   项目: intent-test-framework
   模式: 自动追踪（LangChain 内置）
```

2. 与 Agent 进行对话

3. 打开 LangSmith Dashboard：[https://smith.langchain.com/](https://smith.langchain.com/)

4. 选择你的项目（`intent-test-framework`），应该能看到追踪记录

## 功能特性

### 自动追踪

LangSmith 会自动记录：
- 所有 LLM 调用（输入、输出、token 使用量）
- LangGraph 节点执行（状态转换、决策路径）
- 工具调用（参数、返回值）
- 错误和异常

### 追踪可视化

- **Timeline 视图**：查看每个步骤的执行顺序和耗时
- **Graph 视图**：可视化 LangGraph 的执行流程
- **树形视图**：层级展示嵌套的 LLM 调用

### 性能分析

- Token 使用量统计
- 延迟分析（P50/P95/P99）
- 成本估算

### 调试功能

- 查看完整的输入/输出
- 错误堆栈跟踪
- 重放历史会话
- 比较不同版本的 Prompt

## 高级配置

### 自定义 Tags 和 Metadata

在 `service.py` 中，我们已经配置了自动添加 tags 和 metadata：

```python
config = {
    "configurable": {
        "thread_id": session_id
    },
    "tags": [self.assistant_type, "langgraph"],  # 自定义标签
    "metadata": {
        "session_id": session_id,
        "project_name": project_name or "default"
    }
}
```

这些信息会在 LangSmith Dashboard 中显示，方便筛选和分析。

### 多环境管理

可以为不同环境创建不同的项目：

```bash
# 开发环境
LANGCHAIN_PROJECT=intent-test-dev

# 测试环境
LANGCHAIN_PROJECT=intent-test-staging

# 生产环境
LANGCHAIN_PROJECT=intent-test-prod
```

### 临时禁用追踪

如果需要临时禁用追踪（例如调试时），只需设置：

```bash
LANGCHAIN_TRACING_V2=false
```

或者在代码中：

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"
```

## 最佳实践

1. **为不同的 Agent 使用不同的 tags**：方便分别分析 Alex 和 Lisa 的性能
2. **使用有意义的 metadata**：记录项目名称、用户 ID、会话上下文
3. **定期查看 Dashboard**：监控性能趋势、识别瓶颈
4. **利用 Datasets 功能**：保存典型对话，用于回归测试
5. **使用 Annotations**：标注好的/坏的回复，用于改进 Prompt

## 故障排除

### 追踪未显示

1. 检查环境变量是否正确设置
2. 确认 API Key 有效
3. 查看应用日志是否有错误
4. 检查网络连接（需要访问 smith.langchain.com）

### 追踪数据不完整

- 确保所有 LLM 调用都使用了 `config` 参数
- 检查是否有异常导致追踪中断

### 性能影响

LangSmith 追踪对性能影响很小（< 5ms overhead），但在高并发场景下可以考虑：
- 采样追踪（只记录部分请求）
- 使用异步发送（默认已启用）

## 相关资源

- [LangSmith 官方文档](https://docs.smith.langchain.com/)
- [LangSmith Python SDK](https://github.com/langchain-ai/langsmith-sdk)
- [LangChain 追踪指南](https://python.langchain.com/docs/langsmith/walkthrough)

## 与 Langfuse 对比

| 特性 | LangSmith | Langfuse |
|-----|-----------|----------|
| **集成复杂度** | ⭐⭐⭐⭐⭐ 零配置 | ⭐⭐⭐ 需要额外代码 |
| **部署方式** | 云端 SaaS | 自建 + 云端 |
| **资源需求** | 无（云端） | 高（V3 需要 ClickHouse） |
| **LangChain 支持** | ⭐⭐⭐⭐⭐ 官方产品 | ⭐⭐⭐⭐ 第三方集成 |
| **UI 体验** | ⭐⭐⭐⭐⭐ 优秀 | ⭐⭐⭐⭐ 良好 |
| **开源** | ❌ | ✅ |
| **数据隐私** | 云端存储 | 可私有化部署 |

**选择建议**：
- 优先推荐 LangSmith（官方、简单、功能强大）
- 如果有严格的数据隐私要求，可以考虑自建 Langfuse V2

