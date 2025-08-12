# 🤖 AI引擎架构增强

## MidSceneJS集成架构
```
MidSceneJS Server (Node.js)
├── Express HTTP API
│   ├── /api/extract-data          # 数据提取接口
│   ├── /api/extract-string        # 字符串提取
│   ├── /api/extract-number        # 数字提取
│   ├── /api/extract-object        # 对象提取
│   └── /api/extract-array         # 数组提取
├── Playwright Browser Manager
│   ├── Browser Pool Management    # 浏览器池管理
│   ├── Page Context Isolation     # 页面上下文隔离
│   └── Resource Optimization      # 资源优化
└── AI Model Integration
    ├── OpenAI/Qwen-VL Integration # AI模型集成
    ├── Token Usage Optimization   # Token使用优化
    └── Response Caching          # 响应缓存
```

## 现有API返回值捕获设计

### 返回值捕获接口增强
```javascript
// 增强现有的Midscene API执行，支持返回值捕获
app.post('/api/execute-step', async (req, res) => {
    const { 
        action,          // 现有的Midscene API方法名 (aiQuery, aiString等)
        params,          // 原有的API参数
        outputVariable,  // 可选：输出变量名
        executionId      // 执行上下文ID
    } = req.body;
    
    try {
        // 获取当前页面实例
        const page = await getCurrentPage(req.headers['execution-id']);
        
        // 动态调用对应的Midscene API方法
        let result;
        switch(action) {
            case 'aiQuery':
                result = await page.aiQuery(params.query, params.dataDemand, params.options);
                break;
            case 'aiString':
                result = await page.aiString(params.query, params.options);
                break;
            case 'aiNumber':
                result = await page.aiNumber(params.query, params.options);
                break;
            case 'aiBoolean':
                result = await page.aiBoolean(params.query, params.options);
                break;
            case 'aiAsk':
                result = await page.aiAsk(params.question, params.options);
                break;
            case 'aiLocate':
                result = await page.aiLocate(params.prompt, params.options);
                break;
            case 'evaluateJavaScript':
                result = await page.evaluateJavaScript(params.script);
                break;
            default:
                // 对于没有返回值的方法，正常执行但不捕获返回值
                result = await page[action](params);
        }
        
        // 如果指定了输出变量名，则存储返回值
        if (outputVariable && result !== undefined) {
            await storeVariableData({
                executionId: executionId,
                variableName: outputVariable,
                value: result,
                dataType: typeof result,
                apiMethod: action,
                apiParams: params,
                timestamp: new Date()
            });
        }
        
        res.json({
            success: true,
            data: {
                result: result,
                variable: outputVariable,
                dataType: typeof result,
                executionTime: Date.now() - startTime
            }
        });
        
    } catch (error) {
        logger.error('API execution failed', { 
            error: error.message,
            action,
            params,
            executionId: executionId
        });
        
        res.status(500).json({
            success: false,
            error: {
                message: error.message,
                type: 'EXTRACTION_ERROR',
                query: query,
                suggestions: generateErrorSuggestions(error)
            }
        });
    }
});
```

### 专用数据提取接口
```javascript
// 字符串提取
app.post('/api/extract-string', async (req, res) => {
    const { query, outputVariable } = req.body;
    const result = await page.aiString(query);
    // ... 处理逻辑
});

// 数字提取  
app.post('/api/extract-number', async (req, res) => {
    const { query, outputVariable } = req.body;
    const result = await page.aiNumber(query);
    // ... 处理逻辑
});

// 布尔值提取
app.post('/api/extract-boolean', async (req, res) => {
    const { query, outputVariable } = req.body;
    const result = await page.aiBoolean(query);
    // ... 处理逻辑
});
```

## AI性能优化策略

### 1. 请求缓存机制
```javascript
class AIRequestCache {
    constructor() {
        this.cache = new Map();
        this.ttl = 5 * 60 * 1000; // 5分钟TTL
    }
    
    generateCacheKey(query, schema, pageHash) {
        return crypto.createHash('md5')
            .update(`${query}:${schema}:${pageHash}`)
            .digest('hex');
    }
    
    async get(cacheKey) {
        const cached = this.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.ttl) {
            return cached.data;
        }
        return null;
    }
    
    set(cacheKey, data) {
        this.cache.set(cacheKey, {
            data: data,
            timestamp: Date.now()
        });
    }
}
```

### 2. 浏览器资源池管理
```javascript
class BrowserPoolManager {
    constructor() {
        this.browserPool = [];
        this.maxPoolSize = 5;
        this.currentPool = 0;
    }
    
    async getBrowser() {
        if (this.currentPool < this.maxPoolSize) {
            const browser = await chromium.launch({
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            });
            this.browserPool.push(browser);
            this.currentPool++;
            return browser;
        }
        
        // 复用现有浏览器实例
        return this.browserPool[Math.floor(Math.random() * this.browserPool.length)];
    }
    
    async cleanup() {
        for (const browser of this.browserPool) {
            await browser.close();
        }
        this.browserPool = [];
        this.currentPool = 0;
    }
}
```

---
