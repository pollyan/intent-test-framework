# Local Proxy 架构文档

## 概述

Local Proxy 是运行在**用户本地机器**上的浏览器控制代理服务，基于 **MidSceneJS + Playwright** 实现 AI 驱动的浏览器自动化。

**核心定位**：作为云端 Backend 和用户浏览器之间的桥梁，接收测试指令并控制本地浏览器执行。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户本地环境                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Local Proxy (Node.js)                   │   │
│  │              Port: 3001                              │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────────┐  │   │
│  │  │ Express   │ │ Socket.IO │ │ PlaywrightAgent   │  │   │
│  │  │ HTTP API  │ │ WebSocket │ │ (MidSceneJS)      │  │   │
│  │  └─────┬─────┘ └─────┬─────┘ └─────────┬─────────┘  │   │
│  │        │             │                 │             │   │
│  └────────┼─────────────┼─────────────────┼─────────────┘   │
│           │             │                 │                 │
│           │             │                 ▼                 │
│           │             │     ┌─────────────────────┐       │
│           │             │     │  Chrome/Chromium    │       │
│           │             │     │  (Playwright)       │       │
│           │             │     └─────────────────────┘       │
│           │             │                                   │
└───────────┼─────────────┼───────────────────────────────────┘
            │             │
            ▼             ▼
    ┌───────────────────────────────┐
    │   Backend (Flask)             │
    │   云端服务器                   │
    └───────────────────────────────┘
```

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Node.js | 18+ | 运行环境 |
| Express | 4.21 | HTTP 服务 |
| Socket.IO | 4.7 | WebSocket 通信 |
| Playwright | 1.57 | 浏览器自动化 |
| MidSceneJS | 0.30 | AI 视觉驱动 |
| Axios | 1.13 | HTTP 客户端 |

## 核心文件

```
/                               # 项目根目录
├── midscene_server.js          # 主服务入口 (~2400 行)
├── package.json                # Node.js 依赖
├── midscene_framework/         # Python 辅助框架
│   ├── config.py
│   ├── data_extractor.py
│   ├── mock_service.py
│   ├── retry_handler.py
│   └── validators.py
└── dist/intent-test-proxy/     # 可分发包
    ├── midscene_server.js
    ├── package.json
    ├── start.sh
    └── start.bat
```

## 核心模块

### 1. 服务初始化

```javascript
// midscene_server.js

const { PlaywrightAgent } = require('@midscene/web');
const { chromium } = require('playwright');
const express = require('express');
const { Server } = require('socket.io');

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: { origin: "*", methods: ["GET", "POST"] }
});
```

### 2. 浏览器管理

```javascript
// 全局浏览器实例
let browser = null;
let page = null;
let agent = null;

async function initBrowser(headless = true, timeoutConfig = {}, enableCache = true, testcaseName = '') {
    if (!browser) {
        browser = await chromium.launch({
            headless: headless,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                // ... 其他优化参数
            ]
        });
    }
    
    // 配置 MidSceneJS Agent
    agent = new PlaywrightAgent(page, {
        aiModel: {
            modelName: process.env.MIDSCENE_MODEL_NAME,
            apiKey: process.env.OPENAI_API_KEY,
            baseUrl: process.env.OPENAI_BASE_URL
        }
    });
    
    return { page, agent };
}
```

### 3. 步骤执行引擎

支持的操作类型：

| 类型 | 别名 | 描述 |
|------|------|------|
| `navigate` | `goto` | 导航到 URL |
| `ai_tap` | `click`, `aiTap` | AI 识别并点击元素 |
| `ai_input` | `type`, `aiInput` | AI 识别并输入文本 |
| `ai_assert` | `assert`, `aiAssert` | AI 断言验证 |
| `ai_query` | `aiQuery` | AI 查询提取数据 |
| `ai_string` | `aiString` | AI 提取字符串 |
| `ai_number` | `aiNumber` | AI 提取数字 |
| `ai_boolean` | `aiBoolean` | AI 提取布尔值 |
| `ai_locate` | `aiLocate` | AI 定位元素坐标 |
| `ai_hover` | `aiHover` | AI 悬停 |
| `ai_scroll` | `aiScroll` | AI 滚动 |
| `ai_wait_for` | `aiWaitFor` | AI 等待元素 |
| `screenshot` | `logScreenshot` | 截图 |
| `wait` | `sleep` | 等待指定时间 |
| `refresh` | - | 刷新页面 |
| `back` | - | 返回上一页 |

### 4. 变量解析

支持 `${variable}` 和 `${variable.property}` 语法：

```javascript
function resolveVariableReferences(text, variableContext) {
    const variablePattern = /\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}/g;
    
    return text.replace(variablePattern, (match, variablePath) => {
        const pathParts = variablePath.split('.');
        let value = variableContext[pathParts[0]];
        
        for (let i = 1; i < pathParts.length; i++) {
            value = value[pathParts[i]];
        }
        
        return typeof value === 'object' ? JSON.stringify(value) : String(value);
    });
}
```

## API 端点

### HTTP API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/execute-testcase` | POST | 执行完整测试用例 |
| `/api/execution-status/:id` | GET | 获取执行状态 |
| `/api/execution-report/:id` | GET | 获取执行报告 |
| `/api/executions` | GET | 获取所有执行记录 |
| `/api/stop-execution/:id` | POST | 停止执行 |
| `/api/status` | GET | 服务器状态 |
| `/goto` | POST | 导航到 URL |
| `/ai-tap` | POST | AI 点击 |
| `/ai-input` | POST | AI 输入 |
| `/ai-query` | POST | AI 查询 |
| `/ai-assert` | POST | AI 断言 |
| `/ai-wait-for` | POST | AI 等待 |
| `/health` | GET | 健康检查 |
| `/cleanup` | POST | 清理资源 |

### 请求示例

**执行测试用例：**

```json
POST /api/execute-testcase
{
  "testcase": {
    "id": 1,
    "name": "登录测试",
    "steps": [
      {"type": "goto", "params": {"url": "https://example.com"}},
      {"type": "aiInput", "params": {"text": "admin", "locate": "用户名输入框"}},
      {"type": "aiTap", "params": {"locate": "登录按钮"}},
      {"type": "aiAssert", "params": {"condition": "页面显示欢迎信息"}}
    ]
  },
  "mode": "browser",
  "timeout_settings": {
    "page_timeout": 30000,
    "action_timeout": 30000
  },
  "enable_cache": true
}
```

### WebSocket 事件

| 事件 | 方向 | 描述 |
|------|------|------|
| `execution-start` | Server → Client | 执行开始 |
| `step-start` | Server → Client | 步骤开始 |
| `step-progress` | Server → Client | 步骤进度 |
| `step-completed` | Server → Client | 步骤完成 |
| `step-failed` | Server → Client | 步骤失败 |
| `screenshot-taken` | Server → Client | 截图完成 |
| `execution-completed` | Server → Client | 执行完成 |
| `execution-stopped` | Server → Client | 执行停止 |
| `log-message` | Server → Client | 日志消息 |

## MidSceneJS AI 能力

### AI 操作方法

```javascript
// 点击元素
await agent.aiTap('登录按钮');

// 输入文本
await agent.aiInput('测试用户', '用户名输入框');

// 断言验证
await agent.aiAssert('页面显示欢迎信息');

// 查询数据
const result = await agent.aiQuery('获取表格中的所有商品名称');

// 提取字符串
const title = await agent.aiString('页面标题是什么');

// 提取数字
const price = await agent.aiNumber('商品价格是多少');

// 等待元素
await agent.aiWaitFor('加载完成提示', { timeout: 10000 });
```

### AI 模型配置

通过环境变量配置：

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API 密钥（必需） | - |
| `OPENAI_BASE_URL` | API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `MIDSCENE_MODEL_NAME` | 模型名称 | `qwen-vl-max-latest` |

## 执行流程

```
1. 接收测试用例
   ├── 解析步骤列表
   ├── 初始化执行状态
   └── 通知后端执行开始

2. 初始化浏览器
   ├── 启动 Chromium (headless/visible)
   ├── 创建页面上下文
   └── 初始化 MidSceneJS Agent

3. 遍历执行步骤
   ├── 检查中断标志
   ├── 解析变量 (${xxx})
   ├── 调用 MidSceneJS AI 方法
   │   ├── AI 视觉截图
   │   ├── 发送到 VLM 模型
   │   └── 解析响应执行操作
   ├── 截图并发送 WebSocket
   └── 记录步骤结果

4. 收集执行结果
   ├── 计算统计信息
   ├── 生成执行报告
   └── 通知后端执行完成

5. 清理资源
   └── 关闭浏览器
```

## 重试机制

所有 AI 操作都内置重试机制：

```javascript
let retryCount = 0;
const maxRetries = 3;

while (retryCount < maxRetries) {
    try {
        await agent.aiTap(target);
        break;
    } catch (error) {
        retryCount++;
        if (error.message.includes('Connection error')) {
            await page.waitForTimeout(2000 * retryCount);
        } else {
            throw error;
        }
    }
}
```

## 部署

### 本地运行

```bash
# 安装依赖
npm install

# 安装 Playwright 浏览器
npx playwright install chromium

# 启动服务
node midscene_server.js

# 或指定模式
HEADLESS=false SLOW_MO=100 node midscene_server.js
```

### 作为可分发包

```bash
# 构建分发包
node scripts/build-proxy-package.js

# 输出到 dist/intent-test-proxy/
```

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `PORT` | 服务端口 | `3001` |
| `MAIN_APP_URL` | 后端 API 地址 | `http://localhost:5001/api` |
| `HEADLESS` | 无头模式 | `true` |
| `SLOW_MO` | 操作延迟(ms) | `0` |

## 安全注意事项

1. **仅在本地运行** - 不应暴露到公网
2. **API 密钥保护** - 使用环境变量，不要硬编码
3. **浏览器隔离** - 建议使用独立的用户配置
4. **敏感数据** - 变量中的密码等信息会在日志中脱敏

