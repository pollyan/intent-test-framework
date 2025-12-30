# API 接口文档

> **生成日期**: 2025-12-30
> **来源**: 穷尽代码扫描

---

## AI 智能体 API (`/ai-agents/api`)

### 会话管理

#### 创建会话

```http
POST /ai-agents/api/requirements/sessions
```

**请求体**:
```json
{
  "project_name": "项目名称",
  "assistant_type": "alex"  // alex | lisa
}
```

**响应** (201):
```json
{
  "id": "uuid-string",
  "project_name": "项目名称",
  "session_status": "active",
  "current_stage": "initial",
  "created_at": "2025-12-30T10:00:00.000Z"
}
```

---

#### 获取会话详情

```http
GET /ai-agents/api/requirements/sessions/{session_id}
```

**响应** (200):
```json
{
  "id": "uuid-string",
  "project_name": "项目名称",
  "session_status": "active",
  "current_stage": "clarification",
  "user_context": {},
  "ai_context": {},
  "consensus_content": {},
  "created_at": "...",
  "updated_at": "..."
}
```

---

#### 更新会话状态

```http
PUT /ai-agents/api/requirements/sessions/{session_id}/status
```

**请求体**:
```json
{
  "session_status": "completed"  // active | paused | completed | archived
}
```

---

### 消息管理

#### 获取会话消息

```http
GET /ai-agents/api/requirements/sessions/{session_id}/messages
```

**查询参数**:
- `limit` (可选): 限制返回数量
- `offset` (可选): 分页偏移

**响应** (200):
```json
{
  "messages": [
    {
      "id": 1,
      "session_id": "uuid",
      "message_type": "user",
      "content": "消息内容",
      "metadata": {},
      "created_at": "..."
    }
  ]
}
```

---

#### 发送消息 (HTTP 轮询)

```http
POST /ai-agents/api/requirements/sessions/{session_id}/messages
```

**请求体** (支持文件上传 `multipart/form-data`):
```json
{
  "content": "用户消息内容"
}
```

**响应** (200):
```json
{
  "response": "AI 回复内容",
  "stage": "clarification",
  "consensus_content": {}
}
```

---

#### 流式发送消息 (SSE)

```http
POST /ai-agents/api/requirements/sessions/{session_id}/messages/stream
```

**请求体**:
```json
{
  "content": "用户消息内容"
}
```

**响应**: Server-Sent Events (SSE)
```
data: {"content": "AI", "type": "delta"}
data: {"content": "回复", "type": "delta"}
data: {"content": "内容", "type": "delta"}
data: {"type": "done"}
```

---

### 助手管理

#### 获取助手列表

```http
GET /ai-agents/api/requirements/assistants
```

**响应** (200):
```json
{
  "assistants": [
    {
      "id": "alex",
      "name": "Alex",
      "title": "需求分析专家",
      "description": "专业的软件需求分析师"
    },
    {
      "id": "lisa",
      "name": "Lisa",
      "title": "测试专家 (v5.0)",
      "description": "资深测试专家"
    }
  ]
}
```

---

#### 获取助手 Bundle

```http
GET /ai-agents/api/requirements/assistants/{assistant_type}/bundle
```

**响应** (200):
```json
{
  "bundle_content": "完整的 prompt bundle 内容..."
}
```

---

## 意图测试工具 API (`/intent-tester/api`)

### 测试用例管理

#### 获取测试用例列表

```http
GET /intent-tester/api/testcases
```

**查询参数**:
- `category` (可选): 按分类筛选
- `tags` (可选): 按标签筛选
- `is_active` (可选): 是否激活，默认 true
- `page` (可选): 页码
- `per_page` (可选): 每页数量

**响应** (200):
```json
{
  "testcases": [
    {
      "id": 1,
      "name": "登录测试",
      "description": "测试用户登录流程",
      "steps": [...],
      "tags": ["登录", "冒烟测试"],
      "category": "功能测试",
      "priority": 1,
      "execution_count": 10,
      "success_rate": 85.0
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20
}
```

---

#### 创建测试用例

```http
POST /intent-tester/api/testcases
```

**请求体**:
```json
{
  "name": "测试用例名称",
  "description": "描述",
  "steps": [
    {
      "type": "goto",
      "params": { "url": "https://example.com" },
      "description": "打开首页"
    },
    {
      "type": "ai_input",
      "params": { "locate": "用户名输入框", "text": "testuser" },
      "description": "输入用户名"
    },
    {
      "type": "ai_tap",
      "params": { "locate": "登录按钮" },
      "description": "点击登录"
    },
    {
      "type": "ai_assert",
      "params": { "condition": "页面显示欢迎信息" },
      "description": "验证登录成功"
    }
  ],
  "tags": ["登录", "冒烟测试"],
  "category": "功能测试",
  "priority": 1
}
```

**响应** (201): 创建的测试用例对象

---

#### 获取测试用例详情

```http
GET /intent-tester/api/testcases/{testcase_id}
```

---

#### 更新测试用例

```http
PUT /intent-tester/api/testcases/{testcase_id}
```

---

#### 删除测试用例

```http
DELETE /intent-tester/api/testcases/{testcase_id}
```

> 注意: 使用软删除，将 `is_active` 设为 `false`

---

### 步骤管理

#### 获取测试用例步骤

```http
GET /intent-tester/api/testcases/{testcase_id}/steps
```

---

#### 添加步骤

```http
POST /intent-tester/api/testcases/{testcase_id}/steps
```

**请求体**:
```json
{
  "type": "ai_tap",
  "params": { "locate": "提交按钮" },
  "description": "点击提交"
}
```

---

#### 更新步骤

```http
PUT /intent-tester/api/testcases/{testcase_id}/steps/{step_index}
```

---

#### 删除步骤

```http
DELETE /intent-tester/api/testcases/{testcase_id}/steps/{step_index}
```

---

#### 重排序步骤

```http
POST /intent-tester/api/testcases/{testcase_id}/steps/reorder
```

**请求体**:
```json
{
  "new_order": [2, 0, 1, 3]  // 新的步骤索引顺序
}
```

---

#### 复制步骤

```http
POST /intent-tester/api/testcases/{testcase_id}/steps/{step_index}/duplicate
```

---

### 执行管理

#### 获取执行历史

```http
GET /intent-tester/api/executions
```

**查询参数**:
- `testcase_id` (可选): 按测试用例筛选
- `status` (可选): 按状态筛选
- `page`, `per_page`: 分页

---

#### 获取执行详情

```http
GET /intent-tester/api/executions/{execution_id}
```

**响应** (200):
```json
{
  "id": 1,
  "execution_id": "exec_1234567890_abc",
  "test_case_id": 5,
  "test_case_name": "登录测试",
  "status": "success",
  "mode": "headless",
  "browser": "chrome",
  "start_time": "...",
  "end_time": "...",
  "duration": 45,
  "steps_total": 4,
  "steps_passed": 4,
  "steps_failed": 0,
  "step_executions": [...]
}
```

---

#### 启动执行

```http
POST /intent-tester/api/executions/{testcase_id}/start
```

**请求体**:
```json
{
  "mode": "browser",  // browser | headless
  "timeout_config": {
    "page_timeout": 30000,
    "action_timeout": 30000,
    "navigation_timeout": 30000
  },
  "enable_cache": true
}
```

**响应** (200):
```json
{
  "execution_id": "exec_1234567890_abc",
  "status": "running",
  "message": "执行已启动"
}
```

---

#### 停止执行

```http
POST /intent-tester/api/executions/{execution_id}/stop
```

---

### MidScene Server 通信 API

> 这些 API 供 MidScene Server (客户端代理) 调用，用于同步执行状态

#### 执行开始通知

```http
POST /intent-tester/api/midscene/execution-start
```

**请求体**:
```json
{
  "execution_id": "exec_xxx",
  "testcase_id": 5,
  "mode": "browser",
  "browser": "chrome",
  "steps_total": 10,
  "executed_by": "midscene-server"
}
```

---

#### 执行结果通知

```http
POST /intent-tester/api/midscene/execution-result
```

**请求体**:
```json
{
  "execution_id": "exec_xxx",
  "testcase_id": 5,
  "status": "success",
  "mode": "browser",
  "start_time": "...",
  "end_time": "...",
  "steps": [...],
  "error_message": null
}
```

---

### 代理下载

#### 获取本地代理包

```http
GET /intent-tester/api/proxy/download
```

**响应**: 文件下载 (`intent-test-proxy.zip`)

---

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "详细错误信息"
  }
}
```

### HTTP 状态码

| 状态码 | 说明 |
|---|---|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

---

## 测试步骤类型参考

| 类型 | 说明 | 必需参数 |
|---|---|---|
| `goto` | 导航到 URL | `url` |
| `ai_tap` | AI 智能点击 | `locate` |
| `ai_input` | AI 智能输入 | `locate`, `text` |
| `ai_assert` | AI 断言验证 | `condition` |
| `ai_wait_for` | AI 等待元素 | `condition` |
| `ai_scroll` | AI 智能滚动 | `direction` |
| `ai_query` | AI 数据提取 | `query`, `dataDemand` |
| `ai_string` | AI 提取字符串 | `query` |
| `sleep` | 等待指定时间 | `time` (ms) |
| `screenshot` | 截图 | - |
| `refresh` | 刷新页面 | - |
| `back` | 返回上一页 | - |

---

## 健康检查

```http
GET /health
GET /ai-agents/health
GET /intent-tester/health
```

**响应** (200):
```json
{
  "status": "ok",
  "service": "ai-agents"
}
```
