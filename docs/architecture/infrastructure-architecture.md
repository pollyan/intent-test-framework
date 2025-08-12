# 🏗️ 基础设施架构

## 云服务架构
```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │   CDN + WAF     │
                    └─────────┬───────┘
                              │
                    ┌─────────▼───────┐
                    │     Vercel      │
                    │  Frontend Host  │
                    └─────────┬───────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼──────┐ ┌───────▼──────┐ ┌───────▼──────┐
    │   Supabase   │ │   Node.js    │ │    Redis     │
    │  PostgreSQL  │ │ MidSceneJS   │ │    Cache     │
    │   Database   │ │   Server     │ │   (Optional) │
    └──────────────┘ └──────────────┘ └──────────────┘
```

## 部署架构设计

### 1. Vercel无服务器部署
```javascript
// vercel.json配置
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "web_gui/static/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/index.py"
    },
    {
      "src": "/static/(.*)",
      "dest": "/web_gui/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/api/index.py"
    }
  ],
  "env": {
    "DATABASE_URL": "@database_url",
    "OPENAI_API_KEY": "@openai_api_key",
    "REDIS_URL": "@redis_url"
  },
  "functions": {
    "api/index.py": {
      "memory": 1024,
      "maxDuration": 30
    }
  }
}
```

### 2. 本地代理包架构
```
Local Proxy Package
├── midscene_server.js          # MidSceneJS服务器
├── package.json                # 依赖定义
├── start.sh / start.bat        # 启动脚本
├── config/
│   ├── default.json           # 默认配置
│   └── production.json        # 生产配置
├── lib/
│   ├── browser-manager.js     # 浏览器管理
│   ├── cache-manager.js       # 缓存管理
│   └── performance-monitor.js # 性能监控
└── logs/                      # 日志目录
```

### 3. 数据库架构优化
```sql
-- 分库分表策略
-- 1. 按执行ID hash分表execution_contexts
CREATE TABLE execution_contexts_0 LIKE execution_contexts;
CREATE TABLE execution_contexts_1 LIKE execution_contexts;
-- ... 更多分表

-- 2. 数据归档策略
-- 执行历史数据按月归档
CREATE TABLE execution_history_archive_202501 LIKE execution_history;

-- 3. 读写分离配置
-- 主库：写操作
-- 从库：读操作和报表查询
```

## 监控和可观测性

### 1. 应用性能监控(APM)
```python