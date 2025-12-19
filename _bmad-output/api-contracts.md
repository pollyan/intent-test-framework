# API 接口文档

## 概述

AI4SE Toolbox 提供两套 API：

1. **Backend API** (`http://localhost:5001/api`) - Flask 后端服务
2. **Local Proxy API** (`http://localhost:3001`) - 本地浏览器代理

---

## Backend API

### 测试用例管理

#### 获取测试用例列表

```http
GET /api/testcases
```

**Query 参数：**
| 参数 | 类型 | 描述 |
|------|------|------|
| `category` | string | 按分类筛选 |
| `priority` | int | 按优先级筛选 |
| `limit` | int | 返回数量限制 |
| `offset` | int | 分页偏移 |

**响应：**
```json
{
  "testcases": [
    {
      "id": 1,
      "name": "登录测试",
      "description": "验证用户登录功能",
      "category": "smoke",
      "priority": 1,
      "steps": [...],
      "tags": ["登录", "核心"],
      "execution_count": 10,
      "success_rate": 95.0,
      "created_at": "2025-01-01T00:00:00.000Z"
    }
  ]
}
```

#### 创建测试用例

```http
POST /api/testcases
Content-Type: application/json
```

**请求体：**
```json
{
  "name": "登录测试",
  "description": "验证用户登录功能",
  "category": "smoke",
  "priority": 1,
  "steps": [
    {
      "type": "goto",
      "params": {"url": "https://example.com/login"},
      "description": "打开登录页面"
    },
    {
      "type": "aiInput",
      "params": {"text": "${username}", "locate": "用户名输入框"},
      "description": "输入用户名"
    }
  ],
  "tags": ["登录", "核心"]
}
```

#### 更新测试用例

```http
PUT /api/testcases/{id}
```

#### 删除测试用例

```http
DELETE /api/testcases/{id}
```

---

### 测试执行

#### 启动执行

```http
POST /api/executions/start
Content-Type: application/json
```

**请求体：**
```json
{
  "testcase_id": 1,
  "mode": "browser",
  "variables": {
    "username": "admin",
    "password": "secret"
  }
}
```

**响应：**
```json
{
  "execution_id": "exec_1734567890_abc123",
  "status": "running",
  "started_at": "2025-01-01T00:00:00.000Z"
}
```

#### 获取执行状态

```http
GET /api/executions/{execution_id}
```

**响应：**
```json
{
  "execution_id": "exec_1734567890_abc123",
  "testcase_id": 1,
  "status": "success",
  "mode": "browser",
  "start_time": "2025-01-01T00:00:00.000Z",
  "end_time": "2025-01-01T00:01:30.000Z",
  "duration": 90000,
  "steps_total": 5,
  "steps_passed": 5,
  "steps_failed": 0,
  "step_executions": [...]
}
```

#### 停止执行

```http
POST /api/executions/{execution_id}/stop
```

---

### 需求分析

#### 创建会话

```http
POST /api/requirements/sessions
Content-Type: application/json
```

**请求体：**
```json
{
  "project_name": "我的项目",
  "assistant_type": "alex"
}
```

**响应：**
```json
{
  "id": "sess-uuid-123",
  "project_name": "我的项目",
  "session_status": "active",
  "current_stage": "initial"
}
```

#### 发送消息

```http
POST /api/requirements/sessions/{session_id}/send-message
Content-Type: application/json
```

**请求体：**
```json
{
  "content": "我想开发一个用户管理系统"
}
```

#### 轮询消息

```http
GET /api/requirements/sessions/{session_id}/poll-messages?since={timestamp}
```

**响应：**
```json
{
  "messages": [
    {
      "id": 1,
      "message_type": "assistant",
      "content": "好的，让我来帮你分析...",
      "created_at": "2025-01-01T00:00:01.000Z"
    }
  ],
  "has_more": false
}
```

---

### AI 配置管理

#### 获取配置列表

```http
GET /api/ai-configs
```

**响应：**
```json
{
  "configs": [
    {
      "id": 1,
      "config_name": "默认配置",
      "api_key_masked": "sk-****abcd",
      "base_url": "https://api.openai.com/v1",
      "model_name": "gpt-4-turbo",
      "is_default": true,
      "is_active": true
    }
  ]
}
```

#### 创建配置

```http
POST /api/ai-configs
Content-Type: application/json
```

**请求体：**
```json
{
  "config_name": "阿里云通义",
  "api_key": "sk-xxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "model_name": "qwen-vl-max-latest",
  "is_default": false
}
```

---

### MidScene 集成

#### 通知执行开始

```http
POST /api/midscene/execution-start
Content-Type: application/json
```

**请求体：**
```json
{
  "execution_id": "exec_123",
  "testcase_id": 1,
  "mode": "browser",
  "browser": "chrome",
  "steps_total": 5,
  "executed_by": "midscene-server"
}
```

#### 通知执行结果

```http
POST /api/midscene/execution-result
Content-Type: application/json
```

**请求体：**
```json
{
  "execution_id": "exec_123",
  "testcase_id": 1,
  "status": "success",
  "start_time": "...",
  "end_time": "...",
  "steps": [...],
  "error_message": null
}
```

---

### 健康检查

```http
GET /api/health
```

**响应：**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

---

## Local Proxy API

### 执行测试用例

```http
POST /api/execute-testcase
Content-Type: application/json
```

**请求体：**
```json
{
  "testcase": {
    "id": 1,
    "name": "登录测试",
    "steps": [...]
  },
  "mode": "browser",
  "timeout_settings": {
    "page_timeout": 30000,
    "action_timeout": 30000,
    "navigation_timeout": 30000
  },
  "enable_cache": true
}
```

**响应：**
```json
{
  "success": true,
  "executionId": "exec_1734567890_abc123",
  "message": "测试用例开始执行",
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

### 获取执行状态

```http
GET /api/execution-status/{executionId}
```

### 获取执行报告

```http
GET /api/execution-report/{executionId}
```

**响应：**
```json
{
  "success": true,
  "report": {
    "executionId": "exec_123",
    "testcase": "登录测试",
    "status": "success",
    "summary": {
      "totalSteps": 5,
      "successfulSteps": 5,
      "failedSteps": 0
    },
    "steps": [...],
    "logs": [...],
    "screenshots": [...]
  }
}
```

### 停止执行

```http
POST /api/stop-execution/{executionId}
```

### 服务器状态

```http
GET /api/status
```

**响应：**
```json
{
  "success": true,
  "status": "ready",
  "browserInitialized": false,
  "runningExecutions": 0,
  "totalExecutions": 10,
  "uptime": 3600
}
```

### 健康检查

```http
GET /health
```

**响应：**
```json
{
  "success": true,
  "message": "MidSceneJS服务器运行正常",
  "model": "qwen-vl-max-latest",
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

---

## 错误响应

所有 API 使用统一的错误格式：

```json
{
  "success": false,
  "error": "错误描述",
  "code": "ERROR_CODE",
  "details": {}
}
```

### 常见错误码

| 状态码 | 错误码 | 描述 |
|--------|--------|------|
| 400 | `INVALID_REQUEST` | 请求参数错误 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `CONFLICT` | 资源冲突 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 |
| 502 | `PROXY_ERROR` | 代理连接失败 |
| 503 | `AI_SERVICE_ERROR` | AI 服务不可用 |

