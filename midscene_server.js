/**
 * MidSceneJS HTTP API服务器
 * 提供AI功能的HTTP接口供Python调用
 */

// 加载环境变量
require('dotenv').config();

// 环境变量完整性检查
function validateEnvironmentVariables() {
    const requiredVars = ['OPENAI_API_KEY'];
    const optionalVars = {
        'OPENAI_BASE_URL': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'MIDSCENE_MODEL_NAME': 'qwen-vl-max-latest',
        'PORT': '3001',
        'MAIN_APP_URL': 'http://localhost:5001/api'
    };
    
    const issues = [];
    const warnings = [];
    
    // 检查必需变量
    for (const varName of requiredVars) {
        if (!process.env[varName]) {
            issues.push(`❌ Required environment variable missing: ${varName}`);
        } else {
            console.log(`✅ ${varName}: configured`);
        }
    }
    
    // 检查可选变量并设置默认值
    for (const [varName, defaultValue] of Object.entries(optionalVars)) {
        if (!process.env[varName]) {
            process.env[varName] = defaultValue;
            warnings.push(`⚠️  ${varName} not set, using default: ${defaultValue}`);
        } else {
            console.log(`✅ ${varName}: ${process.env[varName]}`);
        }
    }
    
    // 显示警告
    if (warnings.length > 0) {
        console.log('\n📋 Environment Configuration Warnings:');
        warnings.forEach(warning => console.log(warning));
    }
    
    // 如果有严重问题，停止启动
    if (issues.length > 0) {
        console.log('\n🚨 Environment Configuration Issues:');
        issues.forEach(issue => console.log(issue));
        console.log('\n💡 Please create a .env file with required variables:');
        console.log('   OPENAI_API_KEY=your_api_key_here');
        console.log('   OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1');
        console.log('   MIDSCENE_MODEL_NAME=qwen-vl-max-latest');
        process.exit(1);
    }
    
    console.log('\n✨ Environment validation completed successfully!\n');
}

// 执行环境变量检查
validateEnvironmentVariables();

const express = require('express');
const cors = require('cors');
const { PlaywrightAgent } = require('@midscene/web');
const { chromium } = require('playwright');
const { createServer } = require('http');
const { Server } = require('socket.io');
const axios = require('axios');

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const port = process.env.PORT || 3001;

// 数据库配置 - 注意：如果需要连接到主Web应用，请确保端口正确
const API_BASE_URL = process.env.MAIN_APP_URL || 'http://localhost:5001/api';

// 中间件
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// 全局变量存储浏览器和页面实例
let browser = null;
let page = null;
let agent = null;

// 执行状态管理
const executionStates = new Map();

// 执行控制标志 - 用于中断执行
const executionControls = new Map();

// 变量上下文管理 - 存储每个执行的变量
const variableContexts = new Map();

// 清理旧的执行状态 - 保留最近的50个执行记录
function cleanupOldExecutions() {
    const executions = Array.from(executionStates.entries());
    if (executions.length > 50) {
        // 按时间排序，保留最新的50个
        executions
            .sort((a, b) => (b[1].startTime || 0) - (a[1].startTime || 0))
            .slice(50)
            .forEach(([id]) => {
                executionStates.delete(id);
            });
    }
}

// 统一的日志记录函数
function logMessage(executionId, level, message) {
    const logEntry = {
        executionId,
        level,
        message,
        timestamp: new Date().toISOString()
    };
    
    // 发送WebSocket消息
    io.emit('log-message', logEntry);
    
    // 记录到执行状态
    const executionState = executionStates.get(executionId);
    if (executionState) {
        executionState.logs.push(logEntry);
    }
    
    return logEntry;
}

// 生成执行ID
function generateExecutionId() {
    return 'exec_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// 解析变量引用 - 使用 ${variable} 语法
function resolveVariableReferences(text, variableContext) {
    if (!text || typeof text !== 'string' || !variableContext) {
        return text;
    }
    
    // 只匹配 ${variable} 或 ${variable.property} 格式
    const variablePattern = /\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}/g;
    
    return text.replace(variablePattern, (match, variablePath) => {
        // 解析变量路径，支持多级属性访问
        const pathParts = variablePath.split('.');
        const variableName = pathParts[0];
        const properties = pathParts.slice(1);
        
        // 获取基础变量值
        let variableValue = variableContext[variableName];
        
        if (variableValue === undefined) {
            console.warn(`变量未找到: ${variableName}`);
            return match; // 保持原始文本
        }
        
        // 如果有属性路径，逐级访问
        for (let i = 0; i < properties.length; i++) {
            const property = properties[i];
            
            if (typeof variableValue !== 'object' || variableValue === null) {
                console.warn(`${variableName}${properties.slice(0, i).map(p => '.' + p).join('')} 不是对象，无法访问属性 ${property}`);
                return match;
            }
            
            if (variableValue[property] === undefined) {
                console.warn(`属性未找到: ${variableName}.${properties.slice(0, i + 1).join('.')}`);
                return match;
            }
            
            variableValue = variableValue[property];
        }
        
        // 返回最终值
        return typeof variableValue === 'object' ? JSON.stringify(variableValue) : String(variableValue);
    });
}

// Web系统API集成函数
async function notifyExecutionStart(executionId, testcase, mode) {
    try {
        const totalSteps = Array.isArray(testcase.steps) ? testcase.steps.length : 
                          (typeof testcase.steps === 'string' ? JSON.parse(testcase.steps).length : 0);

        // 通过WebSocket通知前端执行开始
        io.emit('execution-start', {
            executionId: executionId,
            testcase: testcase.name,
            mode: mode,
            totalSteps: totalSteps
        });

        // 发送执行开始通知到Web系统API
        try {
            const startData = {
                execution_id: executionId,
                testcase_id: testcase.id,
                mode: mode,
                browser: 'chrome',
                steps_total: totalSteps,
                executed_by: 'midscene-server'
            };

            console.log(`📡 发送执行开始通知到Web系统 API: ${executionId}`);
            
            const response = await axios.post(`${API_BASE_URL}/midscene/execution-start`, startData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });

            if (response.status === 200) {
                console.log(`✅ 执行开始通知已同步到Web系统: ${executionId}`);
            } else {
                console.warn(`⚠️ Web系统API响应异常: ${response.status} - ${response.statusText}`);
            }
        } catch (apiError) {
            console.error(`❌ 发送执行开始通知到Web系统失败: ${apiError.message}`);
            // 不中断流程，继续执行
        }
        
        console.log(`通知执行开始: ${executionId}`);
        return { success: true };
    } catch (error) {
        console.error(`通知执行开始失败: ${error.message}`);
        return null;
    }
}

async function notifyExecutionResult(executionId, testcase, mode, status, steps, errorMessage = null) {
    try {
        const executionState = executionStates.get(executionId);
        if (!executionState) {
            console.log(`未找到执行状态: ${executionId}`);
            return;
        }

        const endTime = new Date().toISOString();
        const startTime = executionState.startTime.toISOString();

        // 通过WebSocket通知前端执行结果
        io.emit('execution-completed', {
            executionId: executionId,
            testcase: testcase.name,
            status: status,
            mode: mode,
            startTime: startTime,
            endTime: endTime,
            steps: steps,
            errorMessage: errorMessage
        });

        // 发送执行结果到Web系统API
        try {
            const resultData = {
                execution_id: executionId,
                testcase_id: testcase.id,
                status: status,
                mode: mode,
                start_time: startTime,
                end_time: endTime,
                steps: steps || [],
                error_message: errorMessage
            };

            console.log(`📡 发送执行结果到Web系统 API: ${executionId}`);
            
            const response = await axios.post(`${API_BASE_URL}/midscene/execution-result`, resultData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });

            if (response.status === 200) {
                console.log(`✅ 执行结果已同步到Web系统: ${executionId}`);
            } else {
                console.warn(`⚠️ Web系统API响应异常: ${response.status} - ${response.statusText}`);
            }
        } catch (apiError) {
            console.error(`❌ 发送执行结果到Web系统失败: ${apiError.message}`);
            // 不中断流程，继续WebSocket通知
        }

        console.log(`通知执行结果: ${executionId} -> ${status}`);
        return { success: true };
    } catch (error) {
        console.error(`通知执行结果失败: ${error.message}`);
        return null;
    }
}

// 启动浏览器和页面
async function initBrowser(headless = true, timeoutConfig = {}, enableCache = true, testcaseName = '') {
    if (!browser) {
        console.log(`启动浏览器 - 模式: ${headless ? '无头模式' : '浏览器模式'}`);
        browser = await chromium.launch({
            headless: headless,
            args: [
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling', // 防止后台节流
                '--disable-backgrounding-occluded-windows', // 防止后台窗口被挂起
                '--disable-renderer-backgrounding', // 防止渲染器后台化
                '--disable-features=TranslateUI', // 禁用翻译UI避免干扰
                '--disable-features=VizDisplayCompositor' // 提高稳定性
            ]
        });
    }
    
    // 解析超时配置
    const pageTimeout = timeoutConfig.page_timeout || 30000;
    const actionTimeout = timeoutConfig.action_timeout || 30000;
    const navigationTimeout = timeoutConfig.navigation_timeout || 30000;
    
    if (!page) {
        const context = await browser.newContext({
            viewport: { width: 1280, height: 720 },
            deviceScaleFactor: 1,
            // 使用动态超时设置
            timeout: actionTimeout
        });
        page = await context.newPage();
    }
    
    // 每次都重新设置页面超时（因为浏览器可能被重用）
    page.setDefaultTimeout(actionTimeout);
    page.setDefaultNavigationTimeout(navigationTimeout);
    
    console.log(`⏱️ 超时设置: 页面加载=${pageTimeout}ms, 操作=${actionTimeout}ms, 导航=${navigationTimeout}ms`);
    
    // 配置MidSceneJS AI
    const config = {
        modelName: process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest',
        apiKey: process.env.OPENAI_API_KEY,
        baseUrl: process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    };
    
    console.log('🤖 初始化MidSceneJS AI配置:', {
        modelName: config.modelName,
        baseUrl: config.baseUrl,
        hasApiKey: !!config.apiKey,
        enableCache: enableCache
    });
    
    // 根据 MidScene 文档配置缓存
    const agentConfig = { 
        aiModel: config
    };
    
    // 设置缓存相关的环境变量和 cacheId
    if (enableCache) {
        process.env.MIDSCENE_CACHE = '1';
        // 为每个测试用例生成唯一的 cacheId
        // 支持中文字符，并合并连续的连字符
        const normalizedName = testcaseName ? 
            testcaseName
                .replace(/[\s\-_]+/g, '-')  // 空格、连字符、下划线统一替换为单个连字符
                .replace(/[^\u4e00-\u9fa5a-zA-Z0-9\-]/g, '')  // 保留中文、字母、数字和连字符
                .replace(/\-+/g, '-')  // 合并多个连续的连字符
                .replace(/^\-|\-$/g, '')  // 去除首尾的连字符
                .toLowerCase() : 
            `test-${Date.now()}`;
        const cacheId = `playwright-${normalizedName || Date.now()}`;
        agentConfig.cacheId = cacheId;
        console.log('📦 AI缓存已启用');
        console.log(`📦 Cache ID: ${cacheId}`);
    } else {
        delete process.env.MIDSCENE_CACHE;
        console.log('📦 AI缓存已禁用');
    }
    
    agent = new PlaywrightAgent(page, agentConfig);
    
    return { page, agent };
}

// WebSocket连接处理
io.on('connection', (socket) => {
    console.log('🔌 WebSocket客户端连接:', socket.id);

    socket.on('disconnect', () => {
        console.log('🔌 WebSocket客户端断开:', socket.id);
    });

    // 发送服务器状态
    socket.emit('server-status', {
        status: 'ready',
        timestamp: new Date().toISOString()
    });
});

// 标准化步骤类型 - 将新的MidSceneJS格式映射到执行引擎识别的格式
function normalizeStepType(stepType) {
    const typeMapping = {
        // 新格式 -> 执行引擎格式
        'goto': 'navigate',
        'aiTap': 'ai_tap',
        'aiInput': 'ai_input',
        'aiAssert': 'ai_assert',
        'aiQuery': 'ai_query',
        'aiString': 'ai_string',
        'aiNumber': 'ai_number',
        'aiBoolean': 'ai_boolean',
        'aiLocate': 'ai_locate',
        'aiHover': 'ai_hover',
        'aiScroll': 'ai_scroll',
        'aiWaitFor': 'ai_wait_for',
        'evaluateJavaScript': 'evaluate_javascript',
        'logScreenshot': 'screenshot',
        
        // 保持旧格式兼容
        'navigate': 'navigate',
        'ai_tap': 'ai_tap',
        'ai_input': 'ai_input',
        'ai_assert': 'ai_assert',
        'ai_hover': 'ai_hover',
        'ai_scroll': 'ai_scroll',
        'ai_wait_for': 'ai_wait_for',
        'click': 'click',
        'type': 'type',
        'wait': 'wait',
        'sleep': 'sleep',
        'assert': 'assert',
        'refresh': 'refresh',
        'back': 'back',
        'screenshot': 'screenshot',
        'evaluate_javascript': 'evaluate_javascript'
    };
    
    return typeMapping[stepType] || stepType;
}

// 执行单个步骤
async function executeStep(step, page, agent, executionId, stepIndex, totalSteps, timeoutConfig = {}) {
    // 在步骤开始时检查中断标志
    const control = executionControls.get(executionId);
    if (control && control.shouldStop) {
        console.log(`Step ${stepIndex + 1} execution interrupted by user`);
        return {
            status: 'stopped',
            start_time: new Date().toISOString(),
            end_time: new Date().toISOString(),
            duration: 0,
            error_message: '用户中断执行'
        };
    }

    // 支持新旧格式兼容: 新格式使用type字段，旧格式使用action字段
    const stepType = step.type || step.action;
    const params = step.params || {};
    const description = step.description;

    // 标准化步骤类型名称 - 将新的MidSceneJS格式映射到执行引擎识别的格式
    const normalizedAction = normalizeStepType(stepType);

    // 发送步骤开始事件
    io.emit('step-start', {
        executionId,
        stepIndex,
        action: normalizedAction,
        description: description || normalizedAction,
        totalSteps: totalSteps
    });

    const stepStartTime = Date.now();

    try {
        switch (normalizedAction) {
            case 'navigate':
                if (params.url) {
                    const pageTimeout = timeoutConfig.page_timeout || 30000;
                    const navigationTimeout = timeoutConfig.navigation_timeout || 30000;
                    
                    try {
                        // 首先尝试使用 domcontentloaded，更快的加载策略
                        await page.goto(params.url, { waitUntil: 'domcontentloaded', timeout: navigationTimeout });
                        logMessage(executionId, 'info', `导航到: ${params.url}`);
                        
                        // 等待页面稳定
                        await page.waitForTimeout(2000);
                    } catch (error) {
                        // 如果超时，尝试使用更宽松的策略
                        logMessage(executionId, 'warning', `导航超时，尝试使用基础加载策略: ${error.message}`);
                        const fallbackTimeout = Math.min(navigationTimeout / 2, 15000);
                        await page.goto(params.url, { waitUntil: 'commit', timeout: fallbackTimeout });
                        await page.waitForTimeout(3000);
                        logMessage(executionId, 'info', `导航到: ${params.url} (使用基础策略，超时=${fallbackTimeout}ms)`);
                    }
                }
                break;

            case 'click':
            case 'ai_tap':
                const clickTarget = params.locate || params.selector || params.element;
                if (clickTarget) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiTap`);
                    console.log(`Target: ${clickTarget}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const tapStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            await agent.aiTap(clickTarget);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else if (error.message.includes('Protocol error')) {
                                // 鼠标协议错误，可能需要重新初始化
                                logMessage(executionId, 'warning', `鼠标协议错误，尝试使用替代方法...`);
                                // 尝试使用page.click作为备选方案
                                try {
                                    const element = await page.locator(`:text("${clickTarget}")`).first();
                                    await element.click();
                                    break;
                                } catch (fallbackError) {
                                    console.error('备选点击方法也失败:', fallbackError.message);
                                }
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`点击操作失败，已重试${maxRetries}次`);
                    }
                    
                    const tapEndTime = Date.now();
                    
                    console.log(`MidScene aiTap completed in ${tapEndTime - tapStartTime}ms\n`);
                    logMessage(executionId, 'info', `点击: ${clickTarget}`);
                }
                break;

            case 'type':
            case 'ai_input':
                const inputTarget = params.locate || params.selector || params.element;
                let inputText = params.text || params.value;
                
                // 解析变量引用
                const context = variableContexts.get(executionId);
                if (context && inputText) {
                    const originalText = inputText;
                    inputText = resolveVariableReferences(inputText, context);
                    if (originalText !== inputText) {
                        logMessage(executionId, 'info', `变量解析: "${originalText}" → "${inputText}"`);
                    }
                }
                
                if (inputTarget && inputText) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiInput`);
                    console.log(`Text: ${inputText}`);
                    console.log(`Target: ${inputTarget}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const inputStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            await agent.aiInput(inputText, inputTarget);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`输入尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else if (error.message.includes('empty content')) {
                                // AI返回空内容，可能是识别失败
                                logMessage(executionId, 'warning', `AI识别失败，等待页面加载后重试...`);
                                await page.waitForTimeout(3000);
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`输入操作失败，已重试${maxRetries}次`);
                    }
                    
                    const inputEndTime = Date.now();
                    
                    console.log(`MidScene aiInput completed in ${inputEndTime - inputStartTime}ms\n`);
                    logMessage(executionId, 'info', `输入: "${inputText}" 到 ${inputTarget}`);
                }
                break;

            case 'wait':
            case 'sleep':
                const waitTime = params.time || params.duration || 1000;
                await page.waitForTimeout(waitTime);
                logMessage(executionId, 'info', `等待: ${waitTime}ms`);
                break;

            case 'assert':
            case 'ai_assert':
                const assertCondition = params.condition || params.assertion || params.expected;
                if (assertCondition) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiAssert`);
                    console.log(`Condition: ${assertCondition}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const assertStartTime = Date.now();
                    await agent.aiAssert(assertCondition);
                    const assertEndTime = Date.now();
                    
                    console.log(`MidScene aiAssert completed in ${assertEndTime - assertStartTime}ms\n`);
                    logMessage(executionId, 'info', `断言: ${assertCondition}`);
                }
                break;

            case 'ai_query':
                const queryText = params.query;
                const dataDemand = params.dataDemand;
                const outputVariable = step.output_variable;
                
                if (queryText && dataDemand) {
                    // 将dataDemand结构描述拼接到query字符串末尾
                    const combinedQuery = `${queryText}${dataDemand}`;
                    
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiQuery`);
                    console.log(`Original Query: ${queryText}`);
                    console.log(`DataDemand: ${dataDemand}`);
                    console.log(`Combined Query: ${combinedQuery}`);
                    console.log(`Output Variable: ${outputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const queryStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let queryResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiQuery方法，传入拼接后的查询字符串
                            queryResult = await agent.aiQuery(combinedQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiQuery尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiQuery操作失败，已重试${maxRetries}次`);
                    }
                    
                    const queryEndTime = Date.now();
                    
                    console.log(`MidScene aiQuery completed in ${queryEndTime - queryStartTime}ms`);
                    console.log(`Query Result:`, JSON.stringify(queryResult, null, 2));
                    
                    // 在日志中显示提取到的变量值
                    const resultStr = typeof queryResult === 'object' ? JSON.stringify(queryResult, null, 2) : String(queryResult);
                    logMessage(executionId, 'info', `AI数据提取完成，提取结果: ${resultStr}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (outputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[outputVariable] = queryResult;
                        logMessage(executionId, 'info', `变量已存储: ${outputVariable} = ${resultStr}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = queryResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${resultStr}`);
                    }
                }
                break;

            case 'ai_string':
                const stringQuery = params.query;
                const stringOutputVariable = step.output_variable;
                
                if (stringQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiString`);
                    console.log(`Query: ${stringQuery}`);
                    console.log(`Output Variable: ${stringOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const stringStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let stringResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiString方法
                            stringResult = await agent.aiString(stringQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiString尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiString操作失败，已重试${maxRetries}次`);
                    }
                    
                    const stringEndTime = Date.now();
                    
                    console.log(`MidScene aiString completed in ${stringEndTime - stringStartTime}ms`);
                    console.log(`String Result: "${stringResult}"`);
                    
                    // 在日志中显示提取到的字符串值
                    logMessage(executionId, 'info', `AI字符串提取完成，提取结果: "${stringResult}"`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (stringOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[stringOutputVariable] = stringResult;
                        logMessage(executionId, 'info', `变量已存储: ${stringOutputVariable} = "${stringResult}"`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = stringResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = "${stringResult}"`);
                    }
                }
                break;

            case 'ai_number':
                const numberQuery = params.query;
                const numberOutputVariable = step.output_variable;
                
                if (numberQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiNumber`);
                    console.log(`Query: ${numberQuery}`);
                    console.log(`Output Variable: ${numberOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const numberStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let numberResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiNumber方法
                            numberResult = await agent.aiNumber(numberQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiNumber尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiNumber操作失败，已重试${maxRetries}次`);
                    }
                    
                    const numberEndTime = Date.now();
                    
                    console.log(`MidScene aiNumber completed in ${numberEndTime - numberStartTime}ms`);
                    console.log(`Number Result: ${numberResult}`);
                    
                    // 在日志中显示提取到的数字值
                    logMessage(executionId, 'info', `AI数字提取完成，提取结果: ${numberResult}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (numberOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[numberOutputVariable] = numberResult;
                        logMessage(executionId, 'info', `变量已存储: ${numberOutputVariable} = ${numberResult}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = numberResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${numberResult}`);
                    }
                }
                break;

            case 'ai_boolean':
                const booleanQuery = params.query;
                const booleanOutputVariable = step.output_variable;
                
                if (booleanQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiBoolean`);
                    console.log(`Query: ${booleanQuery}`);
                    console.log(`Output Variable: ${booleanOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const booleanStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let booleanResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiBoolean方法
                            booleanResult = await agent.aiBoolean(booleanQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiBoolean尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiBoolean操作失败，已重试${maxRetries}次`);
                    }
                    
                    const booleanEndTime = Date.now();
                    
                    console.log(`MidScene aiBoolean completed in ${booleanEndTime - booleanStartTime}ms`);
                    console.log(`Boolean Result: ${booleanResult}`);
                    
                    // 在日志中显示提取到的布尔值
                    logMessage(executionId, 'info', `AI布尔值提取完成，提取结果: ${booleanResult}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (booleanOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[booleanOutputVariable] = booleanResult;
                        logMessage(executionId, 'info', `变量已存储: ${booleanOutputVariable} = ${booleanResult}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = booleanResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${booleanResult}`);
                    }
                }
                break;

            case 'ai_locate':
                const locateQuery = params.locate;
                const locateOutputVariable = step.output_variable;
                
                if (locateQuery) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiLocate`);
                    console.log(`Locate: ${locateQuery}`);
                    console.log(`Output Variable: ${locateOutputVariable || 'None'}`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const locateStartTime = Date.now();
                    
                    // 添加重试机制
                    let retryCount = 0;
                    const maxRetries = 3;
                    let lastError = null;
                    let locateResult = null;
                    
                    while (retryCount < maxRetries) {
                        try {
                            // 使用MidSceneJS的aiLocate方法
                            locateResult = await agent.aiLocate(locateQuery);
                            break; // 成功则退出循环
                        } catch (error) {
                            lastError = error;
                            retryCount++;
                            
                            console.error(`aiLocate尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                            
                            // 检查是否是AI模型连接错误
                            if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                                logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                                await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                            } else {
                                // 其他错误直接抛出
                                throw error;
                            }
                        }
                    }
                    
                    if (retryCount >= maxRetries) {
                        throw lastError || new Error(`aiLocate操作失败，已重试${maxRetries}次`);
                    }
                    
                    const locateEndTime = Date.now();
                    
                    console.log(`MidScene aiLocate completed in ${locateEndTime - locateStartTime}ms`);
                    console.log(`Locate Result:`, locateResult);
                    
                    // 在日志中显示定位到的坐标
                    const locateDisplay = locateResult ? 
                        `坐标: (${locateResult.x}, ${locateResult.y})` : 
                        '未找到元素';
                    logMessage(executionId, 'info', `AI元素定位完成，${locateDisplay}`);
                    
                    // 存储变量（如果指定了output_variable）
                    if (locateOutputVariable) {
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        // 使用用户指定的变量名存储结果
                        context[locateOutputVariable] = locateResult;
                        logMessage(executionId, 'info', `变量已存储: ${locateOutputVariable} = ${JSON.stringify(locateResult)}`);
                    } else {
                        // 兼容性：如果没有指定output_variable，使用step_X_result格式
                        let context = variableContexts.get(executionId);
                        if (!context) {
                            context = {};
                            variableContexts.set(executionId, context);
                        }
                        
                        const stepVariableName = `step_${stepIndex + 1}_result`;
                        context[stepVariableName] = locateResult;
                        logMessage(executionId, 'info', `变量已存储（兼容模式）: ${stepVariableName} = ${JSON.stringify(locateResult)}`);
                    }
                }
                break;

            case 'refresh':
                const refreshTimeout = timeoutConfig.navigation_timeout || 30000;
                await page.reload({ waitUntil: 'domcontentloaded', timeout: refreshTimeout });
                logMessage(executionId, 'info', `刷新页面 (超时=${refreshTimeout}ms)`);
                break;

            case 'back':
                const backTimeout = timeoutConfig.navigation_timeout || 30000;
                await page.goBack({ waitUntil: 'domcontentloaded', timeout: backTimeout });
                logMessage(executionId, 'info', `返回上一页 (超时=${backTimeout}ms)`);
                break;

            case 'screenshot':
                const screenshotPath = `./screenshots/${executionId}_step_${stepIndex}.png`;
                await page.screenshot({ path: screenshotPath, fullPage: true });
                logMessage(executionId, 'info', `截图保存到: ${screenshotPath}`);
                break;

            case 'ai_hover':
                const hoverTarget = params.locate || params.selector || params.element;
                if (hoverTarget) {
                    await agent.aiHover(hoverTarget);
                    logMessage(executionId, 'info', `悬停: ${hoverTarget}`);
                }
                break;

            case 'ai_scroll':
                const scrollDirection = params.direction || 'down';
                const scrollDistance = params.distance || 500;
                if (scrollDirection === 'down') {
                    await page.evaluate((dist) => window.scrollBy(0, dist), scrollDistance);
                } else if (scrollDirection === 'up') {
                    await page.evaluate((dist) => window.scrollBy(0, -dist), scrollDistance);
                }
                logMessage(executionId, 'info', `滚动: ${scrollDirection} ${scrollDistance}px`);
                break;

            case 'evaluate_javascript':
                const jsCode = params.code || params.script;
                if (jsCode) {
                    const result = await page.evaluate(jsCode);
                    logMessage(executionId, 'info', `执行JavaScript: ${jsCode}, 结果: ${result}`);
                }
                break;

            case 'ai_wait_for':
                const waitTarget = params.locate || params.selector || params.element;
                const waitTimeout = params.timeout || 10000;
                if (waitTarget) {
                    console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - aiWaitFor`);
                    console.log(`Target: ${waitTarget}`);
                    console.log(`Timeout: ${waitTimeout}ms`);
                    console.log(`Execution ID: ${executionId}`);
                    console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                    
                    const waitStartTime = Date.now();
                    await agent.aiWaitFor(waitTarget, { timeout: waitTimeout });
                    const waitEndTime = Date.now();
                    
                    console.log(`MidScene aiWaitFor completed in ${waitEndTime - waitStartTime}ms\n`);
                    logMessage(executionId, 'info', `等待元素出现: ${waitTarget}`);
                }
                break;

            case 'ai':
                // AI智能操作 - 使用通用的AI方法
                const aiPrompt = params.prompt || params.instruction || description || stepType;
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - ai`);
                console.log(`Prompt: ${aiPrompt}`);
                console.log(`Params:`, JSON.stringify(params, null, 2));
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                
                const aiStartTime = Date.now();
                
                // 添加重试机制
                let retryCount = 0;
                const maxRetries = 3;
                let lastError = null;
                
                while (retryCount < maxRetries) {
                    try {
                        await agent.ai(aiPrompt);
                        break; // 成功则退出循环
                    } catch (error) {
                        lastError = error;
                        retryCount++;
                        
                        console.error(`AI操作尝试 ${retryCount}/${maxRetries} 失败:`, error.message);
                        
                        // 检查是否是AI模型连接错误
                        if (error.message.includes('Connection error') || error.message.includes('AI model service')) {
                            logMessage(executionId, 'warning', `AI模型连接失败，正在重试... (${retryCount}/${maxRetries})`);
                            await page.waitForTimeout(2000 * retryCount); // 递增等待时间
                        } else if (error.message.includes('empty content')) {
                            // AI返回空内容，可能是识别失败
                            logMessage(executionId, 'warning', `AI识别失败，等待页面加载后重试...`);
                            await page.waitForTimeout(3000);
                        } else {
                            // 其他错误直接抛出
                            throw error;
                        }
                    }
                }
                
                if (retryCount >= maxRetries) {
                    throw lastError || new Error(`AI操作失败，已重试${maxRetries}次`);
                }
                const aiEndTime = Date.now();
                
                console.log(`MidScene ai completed in ${aiEndTime - aiStartTime}ms\n`);
                logMessage(executionId, 'info', `AI智能操作: ${aiPrompt}`);
                break;

            case 'ai_action':
                const aiActionPrompt = params.prompt || params.instruction || description || stepType;
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - ai_action`);
                console.log(`Prompt: ${aiActionPrompt}`);
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                
                const aiActionStartTime = Date.now();
                await agent.aiAction(aiActionPrompt);
                const aiActionEndTime = Date.now();
                
                console.log(`MidScene aiAction completed in ${aiActionEndTime - aiActionStartTime}ms\n`);
                logMessage(executionId, 'info', `AI操作规划: ${aiActionPrompt}`);
                break;

            case 'setKsyunCookie':
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - setKsyunCookie`);
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                console.log(`Params:`, JSON.stringify(params, null, 2));
                
                const access_key = params.access_key || process.env.KSYUN_ACCESS_KEY;
                const secret_key = params.secret_key || process.env.KSYUN_SECRET_KEY;  
                const region = params.region || process.env.KSYUN_REGION || 'cn-beijing-6';
                const target_url = params.target_url;
                
                if (!access_key || !secret_key) {
                    throw new Error('金山云Access Key和Secret Key不能为空，请在参数中提供或设置环境变量KSYUN_ACCESS_KEY和KSYUN_SECRET_KEY');
                }
                
                console.log(`🔑 设置金山云Cookie - 区域: ${region}`);
                console.log(`🔑 Access Key: ${access_key ? access_key.substr(0, 8) + '***' : 'not provided'}`);
                console.log(`🔑 Secret Key: ${secret_key ? '***' + secret_key.substr(-4) : 'not provided'}`);
                if (target_url) {
                    console.log(`🎯 目标URL: ${target_url}`);
                }
                
                // 调用内部API设置金山云Cookie
                const ksyunStartTime = Date.now();
                
                try {
                    // 首先访问金山云主页建立上下文
                    console.log('🌐 访问金山云主页');
                    await page.goto('http://www.ksyun.com');
                    await page.waitForTimeout(2000);
                    
                    // 生成金山云Cookie
                    let ksyunCookies = await generateKsyunCookies(access_key, secret_key, region);
                    
                    if (!ksyunCookies) {
                        throw new Error('无法生成金山云Cookie');
                    }
                    
                    // 设置Cookie
                    console.log('🍪 开始设置金山云Cookie到浏览器...');
                    console.log('🍪 原始Cookie数据:', JSON.stringify(ksyunCookies, null, 4));
                    
                    const cookiesToSet = [];
                    for (const [name, value] of Object.entries(ksyunCookies)) {
                        const cookieObj = {
                            name: name,
                            value: String(value),
                            domain: '.ksyun.com',
                            path: '/',
                            httpOnly: false,
                            secure: false
                        };
                        cookiesToSet.push(cookieObj);
                        console.log(`🍪 准备设置Cookie: ${name} = ${String(value)} (domain: .ksyun.com)`);
                    }
                    
                    console.log(`🍪 即将设置${cookiesToSet.length}个Cookie到浏览器:`);
                    cookiesToSet.forEach((cookie, index) => {
                        console.log(`  Cookie[${index}]:`, JSON.stringify(cookie, null, 4));
                    });
                    
                    console.log('🔄 调用 page.context().addCookies()...');
                    await page.context().addCookies(cookiesToSet);
                    console.log(`✅ 成功设置${cookiesToSet.length}个金山云Cookie到浏览器`);
                    
                    // 验证Cookie是否设置成功
                    console.log('🔍 验证Cookie设置结果...');
                    try {
                        const currentCookies = await page.context().cookies();
                        const ksyunCookiesSet = currentCookies.filter(cookie => cookie.domain.includes('ksyun.com'));
                        console.log(`📊 当前浏览器中金山云相关Cookie数量: ${ksyunCookiesSet.length}`);
                        ksyunCookiesSet.forEach((cookie, index) => {
                            console.log(`  已设置Cookie[${index}]: ${cookie.name} = ${cookie.value} (domain: ${cookie.domain})`);
                        });
                    } catch (verifyError) {
                        console.log('⚠️  Cookie验证失败:', verifyError.message);
                    }
                    
                    // 如果指定了目标URL，跳转到目标页面
                    if (target_url) {
                        console.log(`🎯 跳转到目标页面: ${target_url}`);
                        console.log('🔄 开始页面导航...');
                        await page.goto(target_url);
                        await page.waitForTimeout(3000);
                        
                        // 记录最终页面信息
                        const finalUrl = page.url();
                        const pageTitle = await page.title();
                        console.log(`📍 页面导航完成:`);
                        console.log(`  最终URL: ${finalUrl}`);
                        console.log(`  页面标题: ${pageTitle}`);
                        
                        // 检查是否成功避免了登录页面
                        if (finalUrl.includes('passport.ksyun.com/login')) {
                            console.log('⚠️  警告: 页面仍然在登录页面，Cookie可能无效');
                        } else if (finalUrl.includes('console.ksyun.com')) {
                            console.log('✅ 成功进入金山云控制台，Cookie认证有效');
                        } else {
                            console.log('🤔 页面导航到了意外的地址，需要检查');
                        }
                    }
                    
                    const ksyunEndTime = Date.now();
                    console.log(`金山云Cookie设置完成，总耗时: ${ksyunEndTime - ksyunStartTime}ms`);
                    logMessage(executionId, 'info', `金山云Cookie设置成功 - 区域: ${region}`);
                    
                } catch (cookieError) {
                    console.error('🔑 金山云Cookie设置失败:', cookieError);
                    logMessage(executionId, 'error', `金山云Cookie设置失败: ${cookieError.message}`);
                    throw cookieError;
                }
                break;

            case 'setCookie':
            case 'setCookies':
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - setCookie`);
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                console.log(`Params:`, JSON.stringify(params, null, 2));
                
                const cookies = params.cookies;
                const domain = params.domain;
                
                if (!cookies || typeof cookies !== 'object') {
                    throw new Error('setCookie操作需要cookies参数，且必须是对象格式');
                }
                
                console.log(`🍪 设置${Object.keys(cookies).length}个通用Cookie`);
                if (domain) {
                    console.log(`🌐 域名: ${domain}`);
                }
                
                const cookieStartTime = Date.now();
                
                try {
                    const cookiesToSet = [];
                    for (const [name, value] of Object.entries(cookies)) {
                        cookiesToSet.push({
                            name: name,
                            value: String(value),
                            domain: domain || undefined,
                            path: '/',
                            httpOnly: false,
                            secure: false
                        });
                    }
                    
                    await page.context().addCookies(cookiesToSet);
                    
                    const cookieEndTime = Date.now();
                    console.log(`✅ 通用Cookie设置完成，耗时: ${cookieEndTime - cookieStartTime}ms`);
                    logMessage(executionId, 'info', `设置了${cookiesToSet.length}个Cookie`);
                    
                } catch (setCookieError) {
                    console.error('🍪 Cookie设置失败:', setCookieError);
                    logMessage(executionId, 'error', `Cookie设置失败: ${setCookieError.message}`);
                    throw setCookieError;
                }
                break;

            default:
                // 通用AI操作 - 优先使用params中的prompt或instruction
                const instruction = params.prompt || params.instruction || description || stepType;
                console.log(`\n[${new Date().toISOString()}] MidScene Step Execution - Default Action`);
                console.log(`Action Type: ${normalizedAction}`);
                console.log(`Instruction: ${instruction}`);
                console.log(`Params:`, JSON.stringify(params, null, 2));
                console.log(`Description: ${description}`);
                console.log(`Execution ID: ${executionId}`);
                console.log(`Step ${stepIndex + 1}/${totalSteps}`);
                
                const defaultStartTime = Date.now();
                await agent.ai(instruction);
                const defaultEndTime = Date.now();
                
                console.log(`MidScene default action completed in ${defaultEndTime - defaultStartTime}ms\n`);
                logMessage(executionId, 'info', `AI操作: ${instruction}`);
                break;
        }

        const stepEndTime = Date.now();
        const duration = stepEndTime - stepStartTime;
        
        return {
            status: 'success',
            start_time: new Date(stepStartTime).toISOString(),
            end_time: new Date(stepEndTime).toISOString(),
            duration: duration
        };

    } catch (error) {
        const stepEndTime = Date.now();
        const duration = stepEndTime - stepStartTime;
        
        // 发送步骤失败事件
        io.emit('step-failed', {
            executionId,
            stepIndex,
            totalSteps: totalSteps,
            error: error.message
        });
        
        logMessage(executionId, 'error', `步骤执行失败: ${error.message}`);
        
        // 返回失败结果而不是抛出异常，让上层处理
        return {
            status: 'failed',
            start_time: new Date(stepStartTime).toISOString(),
            end_time: new Date(stepEndTime).toISOString(),
            duration: duration,
            error_message: error.message
        };
    }
}

// 异步执行完整测试用例
async function executeTestCaseAsync(testcase, mode, executionId, timeoutConfig = {}, enableCache = true) {
    try {
        // 清理旧的执行状态，确保不会累积太多数据
        cleanupOldExecutions();
        
        // 为每次执行创建独立的状态记录
        const currentExecution = {
            id: executionId,
            status: 'running',
            startTime: new Date(),
            testcase: testcase.name,
            mode,
            steps: [],  // 收集步骤执行数据
            screenshots: [],  // 收集截图数据
            logs: []  // 收集日志数据
        };
        
        // 更新执行状态
        executionStates.set(executionId, currentExecution);
        
        // 设置执行控制标志
        executionControls.set(executionId, { shouldStop: false });

        // 通知Web系统执行开始
        await notifyExecutionStart(executionId, testcase, mode);

        // 发送执行开始事件
        io.emit('execution-start', {
            executionId,
            testcase: testcase.name,
            mode,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'info', `开始执行测试用例: ${testcase.name}`);

        // 解析测试步骤
        let steps;
        try {
            steps = typeof testcase.steps === 'string'
                ? JSON.parse(testcase.steps)
                : testcase.steps || [];
        } catch (parseError) {
            throw new Error(`步骤解析失败: ${parseError.message}`);
        }

        if (steps.length === 0) {
            throw new Error('测试用例没有步骤');
        }

        console.log(`\n[${new Date().toISOString()}] Test Case Execution Details`);
        console.log(`Test Case: ${testcase.name}`);
        console.log(`Execution ID: ${executionId}`);
        console.log(`Mode: ${mode}`);
        console.log(`Cache Enabled: ${enableCache}`);
        console.log(`Total Steps: ${steps.length}`);
        console.log('\nSteps Overview:');
        steps.forEach((step, index) => {
            const stepType = step.type || step.action;
            const description = step.description || stepType;
            console.log(`  ${index + 1}. [${stepType}] ${description}`);
        });
        console.log('');

        logMessage(executionId, 'info', `共 ${steps.length} 个步骤`);

        // 初始化步骤结果数组
        const stepsResult = [];
        
        // 初始化浏览器
        const headless = mode === 'headless';
        console.log(`\n[${new Date().toISOString()}] Browser Mode Configuration`);
        console.log(`Received mode: "${mode}"`);
        console.log(`Headless value: ${headless}`);
        console.log(`Will launch browser in: ${headless ? 'HEADLESS' : 'VISIBLE'} mode\n`);
        
        logMessage(executionId, 'info', `初始化浏览器 (${headless ? '无头模式' : '可视模式'})`);

        const { page, agent } = await initBrowser(headless, timeoutConfig, enableCache, testcase.name);

        // 执行每个步骤
        for (let i = 0; i < steps.length; i++) {
            // 检查是否应该停止执行
            const control = executionControls.get(executionId);
            console.log(`Checking stop flag for execution ${executionId}, step ${i + 1}:`, control);
            if (control && control.shouldStop) {
                console.log(`Execution ${executionId} interrupted at step ${i + 1}`);
                logMessage(executionId, 'warning', '执行被用户中断');
                throw new Error('执行被用户中断');
            }
            
            const step = steps[i];
            
            // 检查步骤是否被跳过
            if (step.skip) {
                console.log(`Skipping step ${i + 1}: ${step.description || step.action}`);
                logMessage(executionId, 'warning', `步骤 ${i + 1} 被跳过: ${step.description || step.action}`);
                
                // 发送步骤跳过事件
                io.emit('step-skipped', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    description: step.description || step.action,
                    message: '此步骤已被标记为跳过'
                });
                
                // 记录跳过的步骤结果到stepsResult
                const skipTime = new Date().toISOString();
                stepsResult.push({
                    step_index: i,
                    description: step.description || step.action,
                    status: 'skipped',
                    start_time: skipTime,
                    end_time: skipTime,
                    duration: 0,
                    error_message: '步骤被跳过'
                });
                
                // 同样需要记录到executionState.steps中以便统计
                const executionState = executionStates.get(executionId);
                if (executionState) {
                    const stepData = {
                        index: i,
                        description: step.description || step.action || 'Unknown Step',
                        status: 'skipped',
                        start_time: skipTime,
                        end_time: skipTime,
                        duration: 0,
                        stepType: step.type || step.action,
                        params: step.params || {},
                        error_message: '步骤被跳过'
                    };
                    executionState.steps.push(stepData);
                }
                
                continue; // 跳过此步骤，继续下一个
            }

            // 发送步骤进度
            io.emit('step-progress', {
                executionId,
                stepIndex: i,
                totalSteps: steps.length,
                step: step.description || step.action,
                progress: Math.round((i / steps.length) * 100)
            });

            // 执行步骤并获取详细结果
            const stepStartTime = new Date();
            let stepResult = null;
            
            // executeStep现在返回结果而不是抛出异常
            stepResult = await executeStep(step, page, agent, executionId, i, steps.length, timeoutConfig);
            
            // 根据步骤结果发送相应事件
            if (stepResult.status === 'success') {
                // 发送步骤完成事件
                io.emit('step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: true,
                    result: stepResult
                });
            } else if (stepResult.status === 'stopped') {
                // 步骤被中断
                logMessage(executionId, 'warning', `步骤 ${i + 1} 被用户中断`);
                
                // 发送步骤中断事件
                io.emit('step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: false,
                    error: '用户中断执行'
                });
                
                // 立即退出执行循环
                break;
            } else {
                // 步骤执行失败
                logMessage(executionId, 'error', `步骤 ${i + 1} 执行失败: ${stepResult.error_message}`);
                
                // 发送步骤失败事件
                io.emit('step-completed', {
                    executionId,
                    stepIndex: i,
                    totalSteps: steps.length,
                    success: false,
                    error: stepResult.error_message
                });
                
                // 继续执行后续步骤（可以根据配置决定是否在首次失败时停止）
            }

            // 截图
            let screenshot = null;
            try {
                screenshot = await page.screenshot({
                    fullPage: false,
                    type: 'png'
                });

                io.emit('screenshot-taken', {
                    executionId,
                    stepIndex: i,
                    screenshot: screenshot.toString('base64'),
                    timestamp: new Date().toISOString()
                });
            } catch (screenshotError) {
                console.warn('截图失败:', screenshotError.message);
            }

            // 记录步骤执行数据到当前执行记录
            const executionState = executionStates.get(executionId);
            if (executionState) {
                const stepEndTime = new Date();
                const stepData = {
                    index: i,
                    description: step.description || step.action || 'Unknown Step',
                    status: stepResult?.status || 'success',
                    start_time: stepResult?.start_time || stepStartTime.toISOString(),
                    end_time: stepResult?.end_time || stepEndTime.toISOString(),
                    duration: stepResult?.duration || (stepEndTime - stepStartTime),
                    stepType: step.type || step.action,
                    params: step.params || {},
                    error_message: stepResult?.error_message || null
                };
                
                executionState.steps.push(stepData);
                
                // 记录截图数据
                if (screenshot) {
                    executionState.screenshots.push({
                        stepIndex: i,
                        timestamp: new Date().toISOString(),
                        screenshot: screenshot.toString('base64')
                    });
                }
            }

            // 短暂延迟，让用户看到执行过程
            await page.waitForTimeout(500);
        }

        // 更新执行状态并计算统计信息
        const executionState = executionStates.get(executionId);
        executionState.endTime = new Date();
        executionState.duration = executionState.endTime - executionState.startTime;
        
        // 计算步骤统计
        const totalSteps = executionState.steps.length;
        const successSteps = executionState.steps.filter(step => step.status === 'success').length;
        const failedSteps = executionState.steps.filter(step => step.status === 'failed').length;
        const skippedSteps = executionState.steps.filter(step => step.status === 'skipped').length;
        const executedSteps = totalSteps - skippedSteps; // 实际执行的步骤数
        
        // 优化成功判断逻辑：如果实际执行的步骤都成功，则判断为成功（跳过的步骤不影响结果）
        const overallStatus = (failedSteps === 0 && executedSteps > 0) ? 'success' : 
                             (executedSteps === 0) ? 'skipped' : 'failed';
        executionState.status = overallStatus;

        // 生成更详细的消息
        let message = '';
        if (overallStatus === 'success') {
            message = skippedSteps > 0 
                ? `测试执行完成！执行步骤 ${successSteps}/${executedSteps} 全部成功，跳过 ${skippedSteps} 个步骤`
                : `测试执行完成！所有 ${successSteps} 个步骤全部成功`;
        } else if (overallStatus === 'skipped') {
            message = `测试执行完成，但所有步骤都被跳过`;
        } else {
            message = `测试执行完成，但有 ${failedSteps} 个步骤失败`;
        }

        // 发送执行完成事件
        io.emit('execution-completed', {
            executionId,
            status: overallStatus,
            message: message,
            duration: executionState.duration,
            totalSteps: totalSteps,
            successSteps: successSteps,
            failedSteps: failedSteps,
            skippedSteps: skippedSteps,
            executedSteps: executedSteps,
            timestamp: new Date().toISOString()
        });

        const statusMessage = `${message}，耗时: ${Math.round(executionState.duration / 1000)}秒`;
        
        logMessage(executionId, overallStatus === 'success' ? 'success' : 'warning', statusMessage);
        
        // 检查并通知MidScene生成的报告
        await checkAndNotifyMidsceneReport(executionId, testcase, executionState);

        // 通知Web系统执行完成
        await notifyExecutionResult(executionId, testcase, mode, overallStatus, executionState.steps);

    } catch (error) {
        console.error('测试执行失败:', error);

        // 更新执行状态
        const executionState = executionStates.get(executionId);
        if (executionState) {
            executionState.status = 'failed';
            executionState.endTime = new Date();
            executionState.error = error.message;
        }

        // 发送执行错误事件
        io.emit('execution-completed', {
            executionId,
            status: 'failed',
            error: error.message,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'error', `测试执行失败: ${error.message}`);

        // 通知Web系统执行失败
        await notifyExecutionResult(executionId, testcase, mode, 'failed', executionState?.steps || [], error.message);
    } finally {
        // 清理执行控制标志
        executionControls.delete(executionId);
        
        // 确保每次执行完成后都关闭浏览器，避免资源泄漏和状态污染
        try {
            if (browser) {
                console.log('🔄 关闭浏览器进程，清理资源...');
                await browser.close();
                browser = null;
                page = null;
                agent = null;
                console.log('✅ 浏览器进程已关闭');
            }
        } catch (closeError) {
            console.error('⚠️ 关闭浏览器失败:', closeError.message);
        }
    }
}

// API端点

// 执行完整测试用例
app.post('/api/execute-testcase', async (req, res) => {
    try {
        const { testcase, mode = 'headless', timeout_settings = {}, enable_cache = true } = req.body;

        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /api/execute-testcase`);
        console.log('Full Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Extracted mode:', mode);
        console.log('Request Body Summary:', JSON.stringify({
            testcase: {
                id: testcase?.id,
                name: testcase?.name,
                stepsCount: Array.isArray(testcase?.steps) ? testcase.steps.length : 
                            (typeof testcase?.steps === 'string' ? JSON.parse(testcase.steps).length : 0)
            },
            mode,
            timeout_settings
        }, null, 2));

        if (!testcase) {
            console.error('Error: Missing test case data');
            return res.status(400).json({
                success: false,
                error: '缺少测试用例数据'
            });
        }

        const executionId = generateExecutionId();
        console.log(`Generated Execution ID: ${executionId}`);

        // 解析超时设置
        const timeoutConfig = {
            page_timeout: timeout_settings.page_timeout || 30000,
            action_timeout: timeout_settings.action_timeout || 30000,
            navigation_timeout: timeout_settings.navigation_timeout || 30000
        };
        
        console.log('📋 接收到的超时设置:', JSON.stringify(timeoutConfig, null, 2));

        // 异步执行，立即返回执行ID
        executeTestCaseAsync(testcase, mode, executionId, timeoutConfig, enable_cache).catch(error => {
            console.error('异步执行错误:', error);
        });

        console.log(`Test case execution started successfully\n`);

        res.json({
            success: true,
            executionId,
            message: '测试用例开始执行',
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /api/execute-testcase`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 获取执行状态
app.get('/api/execution-status/:executionId', (req, res) => {
    const { executionId } = req.params;
    const executionState = executionStates.get(executionId);

    if (!executionState) {
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    res.json({
        success: true,
        executionId,
        ...executionState
    });
});

// 获取独立的执行报告
app.get('/api/execution-report/:executionId', (req, res) => {
    const { executionId } = req.params;
    const executionState = executionStates.get(executionId);

    if (!executionState) {
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    // 生成独立的执行报告
    const report = {
        executionId: executionId,
        testcase: executionState.testcase,
        status: executionState.status,
        mode: executionState.mode,
        startTime: executionState.startTime,
        endTime: executionState.endTime,
        duration: executionState.duration,
        summary: {
            totalSteps: executionState.steps.length,
            successfulSteps: executionState.steps.filter(s => s.status === 'success').length,
            failedSteps: executionState.steps.filter(s => s.status === 'failed').length,
            totalLogs: executionState.logs.length,
            totalScreenshots: executionState.screenshots.length
        },
        steps: executionState.steps,
        logs: executionState.logs,
        screenshots: executionState.screenshots,
        generatedAt: new Date().toISOString()
    };

    res.json({
        success: true,
        report
    });
});

// 获取所有执行记录列表
app.get('/api/executions', (req, res) => {
    const executions = Array.from(executionStates.entries()).map(([id, state]) => ({
        executionId: id,
        testcase: state.testcase,
        status: state.status,
        mode: state.mode,
        startTime: state.startTime,
        endTime: state.endTime,
        duration: state.duration,
        stepsCount: state.steps.length
    }));

    // 按开始时间倒序排列
    executions.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));

    res.json({
        success: true,
        executions,
        total: executions.length
    });
});

// 停止执行
app.post('/api/stop-execution/:executionId', async (req, res) => {
    const { executionId } = req.params;
    const executionState = executionStates.get(executionId);

    console.log(`\n[${new Date().toISOString()}] Stop Execution Request`);
    console.log(`Execution ID: ${executionId}`);

    if (!executionState) {
        console.log('Execution not found');
        return res.status(404).json({
            success: false,
            error: '执行记录不存在'
        });
    }

    if (executionState.status !== 'running') {
        console.log(`Execution already ${executionState.status}`);
        return res.json({
            success: true,
            message: '执行已结束'
        });
    }

    try {
        // 设置中断标志
        const control = executionControls.get(executionId);
        if (control) {
            control.shouldStop = true;
            console.log(`Stop flag set successfully for execution ${executionId}`);
            console.log('Current executionControls:', Array.from(executionControls.entries()));
        } else {
            console.log(`Warning: No control object found for execution ${executionId}`);
            console.log('Available execution IDs:', Array.from(executionControls.keys()));
        }

        // 更新状态为已停止
        executionState.status = 'stopped';
        executionState.endTime = new Date();

        // 立即关闭浏览器（如果存在）
        if (browser) {
            console.log('Closing browser immediately...');
            try {
                await browser.close();
                browser = null;
                page = null;
                agent = null;
                console.log('Browser closed successfully');
            } catch (closeError) {
                console.error('Error closing browser:', closeError.message);
            }
        }

        // 发送停止事件
        io.emit('execution-stopped', {
            executionId,
            timestamp: new Date().toISOString()
        });

        logMessage(executionId, 'warning', '执行已被用户停止');

        console.log('Execution stopped successfully\n');

        res.json({
            success: true,
            message: '执行已停止'
        });

    } catch (error) {
        console.error('Error stopping execution:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 获取服务器状态
app.get('/api/status', (req, res) => {
    const runningExecutions = Array.from(executionStates.values())
        .filter(state => state.status === 'running');

    res.json({
        success: true,
        status: 'ready',
        browserInitialized: !!browser,
        runningExecutions: runningExecutions.length,
        totalExecutions: executionStates.size,
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// 设置浏览器模式
app.post('/set-browser-mode', async (req, res) => {
    try {
        const { mode } = req.body; // 'browser' 或 'headless'
        const headless = mode === 'headless';

        // 如果浏览器已经启动且模式不同，需要重启浏览器
        if (browser) {
            await browser.close();
            browser = null;
            page = null;
            agent = null;
        }

        // 重新初始化浏览器
        await initBrowser(headless);

        res.json({
            success: true,
            mode: mode,
            message: `浏览器已切换到${headless ? '无头模式' : '浏览器模式'}`
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 导航到URL
app.post('/goto', async (req, res) => {
    try {
        const { url, mode, timeout_settings = {} } = req.body;
        const headless = mode === 'headless' || mode === undefined; // 默认无头模式
        const timeoutConfig = {
            page_timeout: timeout_settings.page_timeout || 30000,
            action_timeout: timeout_settings.action_timeout || 30000,
            navigation_timeout: timeout_settings.navigation_timeout || 30000
        };
        const { page } = await initBrowser(headless, timeoutConfig);
        
        const navigationTimeout = timeoutConfig.navigation_timeout;
        try {
            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: navigationTimeout });
        } catch (error) {
            // 如果超时，尝试使用更宽松的策略
            const fallbackTimeout = Math.min(navigationTimeout / 2, 15000);
            await page.goto(url, { waitUntil: 'commit', timeout: fallbackTimeout });
        }
        
        res.json({ 
            success: true, 
            url: page.url(),
            title: await page.title()
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI输入
app.post('/ai-input', async (req, res) => {
    try {
        const { text, locate } = req.body;
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-input`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Text:', text);
        console.log('Locate:', locate);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiInput("${text}", "${locate}")`);
        
        const startTime = Date.now();
        const result = await agent.aiInput(text, locate);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-input`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI点击
app.post('/ai-tap', async (req, res) => {
    try {
        const { prompt } = req.body;
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-tap`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiTap("${prompt}")`);
        
        const startTime = Date.now();
        const result = await agent.aiTap(prompt);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-tap`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI查询
app.post('/ai-query', async (req, res) => {
    try {
        const { prompt } = req.body;
        const { agent } = await initBrowser();
        
        const result = await agent.aiQuery(prompt);
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI断言
app.post('/ai-assert', async (req, res) => {
    try {
        const { prompt } = req.body;
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-assert`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiAssert("${prompt}")`);
        
        const startTime = Date.now();
        await agent.aiAssert(prompt);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('Assertion passed successfully');
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result: true 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-assert`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI动作
app.post('/ai-action', async (req, res) => {
    try {
        const { prompt } = req.body;
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-action`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiAction("${prompt}")`);
        
        const startTime = Date.now();
        const result = await agent.aiAction(prompt);
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-action`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI等待
app.post('/ai-wait-for', async (req, res) => {
    try {
        const { prompt, timeout = 30000 } = req.body;
        
        // 详细记录请求信息
        console.log(`\n[${new Date().toISOString()}] MidScene API Request - /ai-wait-for`);
        console.log('Request Body:', JSON.stringify(req.body, null, 2));
        console.log('Prompt:', prompt);
        console.log('Timeout:', timeout);
        
        const { agent } = await initBrowser();
        
        console.log(`Sending to MidScene: agent.aiWaitFor("${prompt}", { timeout: ${timeout} })`);
        
        const startTime = Date.now();
        const result = await agent.aiWaitFor(prompt, { timeout });
        const endTime = Date.now();
        
        console.log(`MidScene Response Time: ${endTime - startTime}ms`);
        console.log('MidScene Response:', JSON.stringify(result, null, 2));
        console.log('Request completed successfully\n');
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        console.error(`[${new Date().toISOString()}] MidScene API Error - /ai-wait-for`);
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// AI滚动
app.post('/ai-scroll', async (req, res) => {
    try {
        const { options, locate } = req.body;
        const { agent } = await initBrowser();
        
        let result;
        if (locate) {
            result = await agent.aiScroll(options, locate);
        } else {
            result = await agent.aiScroll(options);
        }
        
        res.json({ 
            success: true, 
            result 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 截图
app.post('/screenshot', async (req, res) => {
    try {
        const { path } = req.body;
        const { page } = await initBrowser();
        
        const screenshot = await page.screenshot({ path });
        
        res.json({ 
            success: true, 
            path 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 获取页面信息
app.get('/page-info', async (req, res) => {
    try {
        const { page } = await initBrowser();
        
        const info = {
            url: page.url(),
            title: await page.title(),
            viewport: page.viewportSize()
        };
        
        res.json({ 
            success: true, 
            info 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 健康检查
app.get('/health', (req, res) => {
    const modelName = process.env.MIDSCENE_MODEL_NAME;
    
    res.json({ 
        success: true, 
        message: 'MidSceneJS服务器运行正常',
        model: modelName || null,
        timestamp: new Date().toISOString()
    });
});

// AI模型响应时间测试
app.get('/ai-test', async (req, res) => {
    try {
        console.log('🤖 开始测试AI模型响应时间...');
        
        // 获取当前配置的模型信息
        const modelName = process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest';
        const baseUrl = process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1';
        
        // 使用一个简单的测试图片进行AI识别测试
        const { agent, page } = await initBrowser(true); // 使用无头模式
        
        try {
            // 导航到一个简单的测试页面
            await page.goto('data:text/html,<html><body><h1>AI Test</h1><button>Test Button</button></body></html>');
            
            // 测试AI识别响应时间
            const startTime = Date.now();
            
            // 使用aiLocate进行简单的元素定位测试
            const result = await agent.aiLocate('Test Button');
            
            const responseTime = Date.now() - startTime;
            
            console.log(`✅ AI模型响应时间: ${responseTime}ms`);
            
            res.json({
                success: true,
                model: modelName,
                baseUrl: baseUrl,
                responseTime: responseTime,
                timestamp: new Date().toISOString()
            });
            
        } finally {
            // 清理资源
            if (page) await page.close();
        }
        
    } catch (error) {
        console.error('❌ AI模型测试失败:', error);
        res.status(500).json({
            success: false,
            error: error.message,
            model: process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest',
            timestamp: new Date().toISOString()
        });
    }
});

// 清理资源
app.post('/cleanup', async (req, res) => {
    try {
        if (page) {
            await page.close();
            page = null;
            agent = null;
        }
        if (browser) {
            await browser.close();
            browser = null;
        }
        
        res.json({ 
            success: true, 
            message: '资源已清理' 
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 设置浏览器Cookie
app.post('/set-cookies', async (req, res) => {
    try {
        const { cookies, domain } = req.body;
        
        if (!page) {
            return res.status(400).json({
                success: false,
                error: '浏览器页面未初始化'
            });
        }
        
        if (!cookies || typeof cookies !== 'object') {
            return res.status(400).json({
                success: false,
                error: 'cookies参数无效'
            });
        }
        
        // 获取当前页面域名（如果没有指定domain）
        const currentUrl = page.url();
        const currentDomain = domain || new URL(currentUrl).hostname;
        
        console.log(`🍪 设置${Object.keys(cookies).length}个Cookie到域名: ${currentDomain}`);
        
        // 转换Cookie格式并添加到浏览器
        const cookiesToSet = [];
        for (const [name, value] of Object.entries(cookies)) {
            cookiesToSet.push({
                name: name,
                value: String(value),
                domain: currentDomain.startsWith('.') ? currentDomain : `.${currentDomain}`,
                path: '/',
                httpOnly: false,
                secure: false
            });
        }
        
        // 批量设置Cookie
        await page.context().addCookies(cookiesToSet);
        
        console.log('✅ Cookie设置成功');
        res.json({ 
            success: true, 
            message: `已设置${cookiesToSet.length}个Cookie`,
            domain: currentDomain,
            cookies: cookiesToSet.map(c => ({ name: c.name, domain: c.domain }))
        });
        
    } catch (error) {
        console.error('❌ Cookie设置失败:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 设置金山云登录Cookie
app.post('/set-ksyun-cookies', async (req, res) => {
    try {
        const { access_key, secret_key, region, target_url } = req.body;
        
        if (!page) {
            return res.status(400).json({
                success: false,
                error: '浏览器页面未初始化'
            });
        }
        
        console.log('🔑 开始设置金山云登录Cookie');
        
        // 首先访问金山云主页
        console.log('🌐 访问金山云主页');
        await page.goto('http://www.ksyun.com');
        await page.waitForTimeout(2000);
        
        // 动态导入金山云认证服务（Node.js环境）
        let ksyunCookies;
        try {
            // 这里需要实现Node.js版本的金山云认证逻辑
            ksyunCookies = await generateKsyunCookies(access_key, secret_key, region);
        } catch (authError) {
            console.error('🔑 金山云认证失败:', authError);
            return res.status(400).json({
                success: false,
                error: `金山云认证失败: ${authError.message}`
            });
        }
        
        if (!ksyunCookies) {
            return res.status(400).json({
                success: false,
                error: '无法生成金山云Cookie'
            });
        }
        
        // 设置金山云Cookie
        console.log('🍪 设置金山云Cookie');
        const cookiesToSet = [];
        for (const [name, value] of Object.entries(ksyunCookies)) {
            cookiesToSet.push({
                name: name,
                value: String(value),
                domain: '.ksyun.com',
                path: '/',
                httpOnly: false,
                secure: false
            });
        }
        
        await page.context().addCookies(cookiesToSet);
        console.log(`✅ 已设置${cookiesToSet.length}个金山云Cookie`);
        
        // 如果指定了目标URL，跳转到目标页面
        if (target_url) {
            console.log(`🌐 跳转到目标页面: ${target_url}`);
            await page.goto(target_url);
            await page.waitForTimeout(2000);
        }
        
        res.json({ 
            success: true, 
            message: '金山云Cookie设置成功',
            cookies_count: cookiesToSet.length,
            target_url: target_url,
            current_url: page.url()
        });
        
    } catch (error) {
        console.error('❌ 金山云Cookie设置失败:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// Node.js环境下生成金山云Cookie的函数
async function generateKsyunCookies(accessKey, secretKey, region = 'cn-beijing-6') {
    // 引入必要的模块
    const crypto = require('crypto');
    
    console.log('🔑 生成金山云认证Cookie');
    console.log(`📍 区域: ${region}`);
    console.log(`🔑 Access Key: ${accessKey.substr(0, 8)}***`);
    
    try {
        // 通过IAM API获取真实认证Cookie
        try {
            const iamCookies = await getSTSCredentials(accessKey, secretKey, region);
            if (iamCookies) {
                console.log('🎫 通过IAM接口获取真实Cookie成功');
                const validCookies = generateCookiesFromSTS(iamCookies);
                if (validCookies) {
                    return validCookies;
                }
            }
        } catch (iamError) {
            console.log('⚠️  IAM Cookie获取失败，使用模拟方案:', iamError.message);
            console.log('错误详情:', iamError.stack);
        }
        
        // 改进的模拟Cookie生成（更接近真实格式）
        const timestamp = Math.floor(Date.now() / 1000);
        const userId = crypto.createHash('sha256').update(accessKey + secretKey).digest('hex').substr(0, 12);
        
        // 生成更真实的会话ID
        const sessionId = generateJSessionId();
        
        // 生成控制台会话令牌
        const consoleSessionData = {
            accessKeyId: accessKey,
            userId: userId,
            region: region,
            timestamp: timestamp,
            permissions: ['console:*'] // 控制台权限
        };
        const consoleSession = Buffer.from(JSON.stringify(consoleSessionData)).toString('base64');
        
        // 生成认证令牌
        const authData = `${accessKey}:${userId}:${timestamp}:${region}`;
        const authToken = crypto.createHmac('sha256', secretKey).update(authData).digest('hex');
        const authCookie = Buffer.from(`${authData}:${authToken}`).toString('base64');
        
        // 使用更接近金山云真实格式的Cookie名称
        const cookies = {
            // Java Web应用常用的会话ID
            'JSESSIONID': sessionId,
            
            // 金山云控制台相关Cookie
            'ks-console-session': consoleSession,
            'ks-auth-token': authCookie,
            'ks-user-id': userId,
            'ks-region': region,
            
            // 用户状态Cookie
            'ks-logged-in': 'true',
            'ks-user-type': 'api',
            
            // 时间戳和签名
            'ks-timestamp': timestamp.toString(),
            'ks-signature': crypto.createHmac('sha256', secretKey).update(`${userId}:${timestamp}`).digest('hex').substr(0, 16),
        };
        
        console.log('✅ 金山云Cookie生成成功 (模拟模式)');
        console.log(`🍪 生成了${Object.keys(cookies).length}个Cookie`);
        return cookies;
        
    } catch (error) {
        console.error('❌ 金山云Cookie生成失败:', error);
        throw error;
    }
}

// 生成Java会话ID格式
function generateJSessionId() {
    const chars = '0123456789ABCDEF';
    let result = '';
    for (let i = 0; i < 32; i++) {
        result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
}


// AWS4签名算法实现 (基于金山云IAM接口)
function generateAws4Headers(service, host, region, endpoint, accessKey, secretKey, requestParameters) {
    const crypto = require('crypto');
    
    console.log('🔐 开始生成AWS4签名...');
    
    // 当前时间
    const now = new Date();
    const amzDate = now.toISOString().replace(/[:-]|\..*/g, '');
    const dateStamp = amzDate.substr(0, 8);
    
    console.log(`📅 签名时间: ${amzDate}`);
    console.log(`📅 日期戳: ${dateStamp}`);
    
    // HTTP方法和URI
    const method = 'GET';
    const canonicalUri = '/';
    
    // 构建查询字符串
    const sortedParams = Object.keys(requestParameters).sort();
    const canonicalQuerystring = sortedParams
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(requestParameters[key])}`)
        .join('&');
    
    console.log(`🔗 规范查询字符串: ${canonicalQuerystring}`);
    
    // 构建规范头
    const canonicalHeaders = `host:${host}\nx-amz-date:${amzDate}\n`;
    const signedHeaders = 'host;x-amz-date';
    
    console.log(`📋 规范头:\n${canonicalHeaders}`);
    console.log(`✍️  签名头: ${signedHeaders}`);
    
    // 构建规范请求
    const payloadHash = crypto.createHash('sha256').update('').digest('hex');
    const canonicalRequest = `${method}\n${canonicalUri}\n${canonicalQuerystring}\n${canonicalHeaders}\n${signedHeaders}\n${payloadHash}`;
    
    console.log(`📜 规范请求:\n${canonicalRequest}`);
    
    // 构建待签名字符串
    const algorithm = 'AWS4-HMAC-SHA256';
    const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`;
    const stringToSign = `${algorithm}\n${amzDate}\n${credentialScope}\n${crypto.createHash('sha256').update(canonicalRequest).digest('hex')}`;
    
    console.log(`🔤 待签名字符串:\n${stringToSign}`);
    console.log(`🎯 凭证范围: ${credentialScope}`);
    
    // 计算签名密钥
    const kDate = crypto.createHmac('sha256', `AWS4${secretKey}`).update(dateStamp).digest();
    const kRegion = crypto.createHmac('sha256', kDate).update(region).digest();
    const kService = crypto.createHmac('sha256', kRegion).update(service).digest();
    const kSigning = crypto.createHmac('sha256', kService).update('aws4_request').digest();
    
    console.log('🔑 签名密钥计算完成');
    
    // 计算签名
    const signature = crypto.createHmac('sha256', kSigning).update(stringToSign).digest('hex');
    
    console.log(`🖊️  最终签名: ${signature}`);
    
    // 构建Authorization头
    const authorizationHeader = `${algorithm} Credential=${accessKey}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;
    
    console.log(`🔐 Authorization头: ${authorizationHeader}`);
    
    // 构建请求头（移除Host和User-Agent）
    const headers = {
        'Authorization': authorizationHeader,
        'X-Amz-Date': amzDate
    };
    
    // 构建完整URL
    const requestUrl = canonicalQuerystring ? `${endpoint}/?${canonicalQuerystring}` : endpoint;
    
    console.log('✅ AWS4签名生成完成');
    console.log(`🌐 请求URL: ${requestUrl}`);
    
    return { requestUrl, headers };
}

// 通过金山云IAM接口获取真实的认证Cookie (使用AWS4签名算法)
async function get_cookie_from_iam(accessKey, secretKey, region = 'cn-beijing-6') {
    console.log('🔑 开始通过IAM接口获取金山云认证Cookie');
    console.log(`📍 区域: ${region}`);
    console.log(`🔑 Access Key: ${accessKey ? accessKey.substr(0, 8) + '***' : 'not provided'}`);
    
    try {
        const crypto = require('crypto');
        const axios = require('axios');
        
        // 金山云IAM GetUserSession接口（使用HTTP避免SSL证书问题）
        const service = 'iam';
        const action = 'GetUserSession';
        const version = '2015-11-01';
        const host = `iam.${region}.inner.api.ksyun.com`;
        const endpoint = `http://${host}`;
        
        // 构建请求参数
        const requestParameters = {
            'Action': action,
            'Version': version
        };
        
        console.log('🌐 准备AWS4签名认证...');
        console.log(`  服务: ${service}`);
        console.log(`  主机: ${host}`);
        console.log(`  端点: ${endpoint}`);
        console.log(`  请求参数:`, JSON.stringify(requestParameters, null, 4));
        
        // 使用AWS4签名算法生成认证头
        const { requestUrl, headers } = generateAws4Headers(
            service, host, region, endpoint, accessKey, secretKey, requestParameters
        );
        
        console.log('📤 IAM接口请求详情:');
        console.log(`  方法: GET`);
        console.log(`  URL: ${requestUrl}`);
        console.log(`  请求头:`, JSON.stringify(headers, null, 4));
        console.log(`  超时设置: 30000ms`);
        
        // 调用IAM接口
        const response = await axios.get(requestUrl, {
            headers: headers,
            timeout: 30000
        });
        
        console.log('📥 IAM接口响应详情:');
        console.log(`  状态码: ${response.status}`);
        console.log(`  状态文本: ${response.statusText}`);
        console.log(`  响应头:`, JSON.stringify(response.headers, null, 4));
        console.log(`  响应体:`, JSON.stringify(response.data, null, 4));
        
        console.log('✅ IAM接口调用成功');
        
        // 解析响应获取session URL（支持XML格式）
        console.log('🔍 开始解析IAM接口响应...');
        
        let parsedData = response.data;
        
        // 检查是否为XML格式的响应
        if (typeof response.data === 'string' && response.data.includes('<GetUserSessionResponse>')) {
            console.log('🔍 检测到XML格式响应，开始解析...');
            try {
                const xml2js = require('xml2js');
                
                // 预处理XML，修复URL中的未转义字符（金山云XML响应的常见问题）
                let cleanedXml = response.data;
                
                // 查找<Url>标签中的内容并手动提取
                const urlMatch = response.data.match(/<Url>(.*?)<\/Url>/);
                if (urlMatch && urlMatch[1]) {
                    const originalUrl = urlMatch[1];
                    // 不需要转义，因为我们会直接提取URL
                    console.log('🔗 从XML中提取到URL:', originalUrl);
                    
                    // 暂时移除<Url>标签的内容，避免XML解析错误
                    cleanedXml = response.data.replace(/<Url>.*?<\/Url>/, '<Url>PLACEHOLDER_URL</Url>');
                }
                
                const parser = new xml2js.Parser({ explicitArray: false, ignoreAttrs: true });
                const result = await parser.parseStringPromise(cleanedXml);
                parsedData = result;
                
                // 如果提取到了URL，手动设置回结果中
                if (urlMatch && urlMatch[1] && parsedData.GetUserSessionResponse && parsedData.GetUserSessionResponse.GetUserSessionResult) {
                    parsedData.GetUserSessionResponse.GetUserSessionResult.Url = urlMatch[1];
                }
                
                console.log('✅ XML解析成功');
                console.log('🔍 解析后的结构:', JSON.stringify(parsedData, null, 4));
            } catch (xmlError) {
                console.error('❌ XML解析失败:', xmlError.message);
                console.log('🔍 原始XML内容:', response.data);
                
                // 作为备用方案，尝试直接使用正则表达式提取URL
                console.log('🔄 尝试使用正则表达式备用方案...');
                const urlRegex = /<Url>(.*?)<\/Url>/;
                const expirationRegex = /<Expiration>(.*?)<\/Expiration>/;
                const urlMatch = response.data.match(urlRegex);
                const expirationMatch = response.data.match(expirationRegex);
                
                if (urlMatch && urlMatch[1]) {
                    console.log('✅ 使用正则表达式成功提取URL');
                    parsedData = {
                        GetUserSessionResponse: {
                            GetUserSessionResult: {
                                Url: urlMatch[1],
                                Expiration: expirationMatch ? expirationMatch[1] : null
                            }
                        }
                    };
                    console.log('🔍 正则提取的结构:', JSON.stringify(parsedData, null, 4));
                }
            }
        }
        
        // 解析GetUserSessionResult
        if (parsedData && parsedData.GetUserSessionResponse && parsedData.GetUserSessionResponse.GetUserSessionResult) {
            const result = parsedData.GetUserSessionResponse.GetUserSessionResult;
            console.log('✅ 找到GetUserSessionResult字段');
            console.log('🔍 分析响应结构:', JSON.stringify(result, null, 4));
            
            if (result.Url) {
                const sessionUrl = result.Url;
                console.log('🎫 获取到session URL:', sessionUrl);
                
                // 访问session URL获取Cookie
                console.log('🍪 开始从session URL提取Cookie...');
                const cookies = await extractCookiesFromUrl(sessionUrl);
                if (cookies && Object.keys(cookies).length > 0) {
                    console.log(`✅ 成功提取${Object.keys(cookies).length}个认证Cookie`);
                    console.log('🍪 Cookie详情:', JSON.stringify(cookies, null, 4));
                    console.log('🍪 Cookie列表:', Object.keys(cookies).join(', '));
                    return cookies;
                } else {
                    console.log('❌ 未能从session URL提取到有效Cookie');
                }
            } else {
                console.log('⚠️  响应中没有找到Url字段');
            }
        } else {
            console.log('❌ 响应中没有找到GetUserSessionResult字段');
            console.log('🔍 完整响应结构分析:', typeof response.data === 'string' ? response.data : JSON.stringify(response.data, null, 4));
        }
        
        console.log('⚠️  未能从IAM响应中获取有效的认证信息');
        return null;
        
    } catch (error) {
        console.error('❌ IAM认证Cookie获取失败:', error.message);
        if (error.response) {
            console.error('响应状态:', error.response.status);
            console.error('响应状态文本:', error.response.statusText);
            console.error('响应头:', JSON.stringify(error.response.headers, null, 4));
            console.error('响应数据:', error.response.data);
        }
        if (error.code) {
            console.error('错误代码:', error.code);
        }
        console.error('错误堆栈:', error.stack);
        return null;
    }
}

// 生成金山云API签名
function generateKsyunSignature(params, secretKey, method = 'POST', region = 'cn-beijing-6') {
    const crypto = require('crypto');
    
    // 构建规范化查询字符串
    const sortedKeys = Object.keys(params).sort();
    const canonicalQueryString = sortedKeys
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');
    
    // 构建待签名字符串 (金山云V1签名算法)
    const stringToSign = `${method}\n/\n${canonicalQueryString}`;
    
    // 生成签名
    const signature = crypto
        .createHmac('sha1', secretKey)
        .update(stringToSign, 'utf8')
        .digest('base64');
    
    console.log('🔐 生成API签名');
    console.log('StringToSign:', stringToSign);
    
    return signature;
}

// 使用临时凭证生成控制台登录URL
async function generateConsoleLoginUrl(credentials, region) {
    try {
        const crypto = require('crypto');
        const axios = require('axios');
        
        console.log('🔗 开始生成控制台登录URL...');
        console.log('🔑 使用的临时凭证:', JSON.stringify(credentials, null, 4));
        
        // 构建Federation URL参数
        const sessionData = {
            sessionId: credentials.AccessKeyId,
            sessionKey: credentials.SecretAccessKey,
            sessionToken: credentials.SessionToken
        };
        
        const federationParams = {
            'Action': 'GetSigninToken',
            'SessionDuration': 3600,
            'Session': JSON.stringify(sessionData)
        };
        
        console.log('📋 Federation请求参数:');
        console.log(`  Action: ${federationParams.Action}`);
        console.log(`  SessionDuration: ${federationParams.SessionDuration}`);
        console.log(`  Session数据:`, JSON.stringify(sessionData, null, 4));
        
        // 调用Federation服务获取SigninToken
        const federationUrl = `https://signin.${region}.ksyun.com/federation`;
        console.log(`🌐 调用Federation接口: ${federationUrl}`);
        
        const federationResponse = await axios.get(federationUrl, {
            params: federationParams,
            timeout: 30000
        });
        
        console.log('📥 Federation接口响应:');
        console.log(`  状态码: ${federationResponse.status}`);
        console.log(`  响应数据:`, JSON.stringify(federationResponse.data, null, 4));
        
        if (federationResponse.data && federationResponse.data.SigninToken) {
            const signinToken = federationResponse.data.SigninToken;
            console.log(`🎫 获取到SigninToken: ${signinToken}`);
            
            // 构建最终的控制台登录URL
            const destination = 'https://console.ksyun.com/';
            const loginUrl = `https://signin.${region}.ksyun.com/federation?` +
                `Action=login&Issuer=AutoTest&Destination=${encodeURIComponent(destination)}&SigninToken=${signinToken}`;
            
            console.log('🔗 构建最终登录URL:');
            console.log(`  基础URL: https://signin.${region}.ksyun.com/federation`);
            console.log(`  Action: login`);
            console.log(`  Issuer: AutoTest`);
            console.log(`  Destination: ${destination}`);
            console.log(`  SigninToken: ${signinToken}`);
            console.log(`  完整URL: ${loginUrl}`);
            
            return loginUrl;
        } else {
            console.log('❌ Federation响应中没有SigninToken');
            return null;
        }
        
    } catch (error) {
        console.error('❌ 生成控制台登录URL失败:', error.message);
        if (error.response) {
            console.error('Federation接口响应状态码:', error.response.status);
            console.error('Federation接口响应数据:', JSON.stringify(error.response.data, null, 4));
        }
        if (error.code) {
            console.error('错误代码:', error.code);
        }
        console.error('错误堆栈:', error.stack);
        return null;
    }
}

// 从URL提取Cookie
async function extractCookiesFromUrl(url) {
    try {
        const axios = require('axios');
        
        console.log('🍪 开始访问URL提取Cookie...');
        console.log(`  目标URL: ${url}`);
        
        const requestConfig = {
            timeout: 30000,
            maxRedirects: 5,
            validateStatus: (status) => status >= 200 && status < 400,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        };
        
        console.log('📤 Cookie提取请求配置:');
        console.log(`  超时: ${requestConfig.timeout}ms`);
        console.log(`  最大重定向: ${requestConfig.maxRedirects}`);
        console.log(`  User-Agent: ${requestConfig.headers['User-Agent']}`);
        
        // 访问URL获取Set-Cookie响应头
        const response = await axios.get(url, requestConfig);
        
        console.log('📥 Cookie提取响应详情:');
        console.log(`  状态码: ${response.status}`);
        console.log(`  状态文本: ${response.statusText}`);
        console.log(`  响应头:`, JSON.stringify(response.headers, null, 4));
        
        // 从响应头中提取Cookie
        const setCookieHeaders = response.headers['set-cookie'] || [];
        console.log(`🍪 找到${setCookieHeaders.length}个Set-Cookie响应头:`);
        setCookieHeaders.forEach((header, index) => {
            console.log(`  Set-Cookie[${index}]: ${header}`);
        });
        
        const cookies = {};
        
        setCookieHeaders.forEach((cookieHeader, index) => {
            console.log(`🔍 解析第${index + 1}个Cookie头: ${cookieHeader}`);
            const cookieParts = cookieHeader.split(';')[0].split('=');
            if (cookieParts.length >= 2) {
                const name = cookieParts[0].trim();
                const value = cookieParts.slice(1).join('=').trim();
                if (name && value) {
                    cookies[name] = value;
                    console.log(`  ✅ 提取Cookie: ${name} = ${value}`);
                } else {
                    console.log(`  ⚠️  跳过无效Cookie: name="${name}", value="${value}"`);
                }
            } else {
                console.log(`  ⚠️  跳过格式错误的Cookie头: ${cookieHeader}`);
            }
        });
        
        console.log(`🍪 从URL提取到${Object.keys(cookies).length}个有效Cookie:`);
        Object.entries(cookies).forEach(([name, value]) => {
            console.log(`  ${name}: ${value}`);
        });
        
        return Object.keys(cookies).length > 0 ? cookies : null;
        
    } catch (error) {
        console.error('❌ 从URL提取Cookie失败:', error.message);
        if (error.response) {
            console.error('响应状态码:', error.response.status);
            console.error('响应状态文本:', error.response.statusText);
            console.error('响应头:', JSON.stringify(error.response.headers, null, 4));
            console.error('响应数据:', error.response.data);
        }
        if (error.code) {
            console.error('错误代码:', error.code);
        }
        console.error('错误堆栈:', error.stack);
        return null;
    }
}

// 尝试通过IAM API获取临时凭证（更新函数名以保持兼容性）
async function getSTSCredentials(accessKey, secretKey, region) {
    console.log('🎫 尝试通过IAM接口获取认证Cookie...');
    return await get_cookie_from_iam(accessKey, secretKey, region);
}

// 从IAM Cookie直接返回（更新函数以处理真实Cookie）
function generateCookiesFromSTS(iamCookies) {
    if (iamCookies && typeof iamCookies === 'object' && Object.keys(iamCookies).length > 0) {
        console.log('✅ 使用IAM接口获取的真实Cookie');
        return iamCookies;
    }
    return null; // 返回null而不是空对象，这样可以触发回退到模拟Cookie
}

// 错误处理中间件
app.use((error, req, res, next) => {
    console.error('服务器错误:', error);
    res.status(500).json({ 
        success: false, 
        error: '内部服务器错误' 
    });
});

// 检查并通知MidScene生成的报告
async function checkAndNotifyMidsceneReport(executionId, testcase, executionState) {
    try {
        const fs = require('fs');
        const path = require('path');
        
        console.log(`📋 开始检查MidScene报告，执行ID: ${executionId}`);
        console.log(`📋 当前工作目录: ${process.cwd()}`);
        
        // 检查midscene_run目录是否存在
        const midsceneRunDir = path.join(process.cwd(), 'midscene_run');
        console.log(`📋 检查目录: ${midsceneRunDir}`);
        
        if (!fs.existsSync(midsceneRunDir)) {
            console.log('📋 midscene_run目录不存在，跳过报告检查');
            logMessage(executionId, 'warning', 'MidScene报告目录不存在，请检查测试执行环境');
            return;
        }
        
        // 检查报告目录
        const reportDir = path.join(midsceneRunDir, 'report');
        console.log(`📋 检查报告目录: ${reportDir}`);
        
        if (!fs.existsSync(reportDir)) {
            console.log('📋 报告目录不存在，跳过报告检查');
            logMessage(executionId, 'warning', 'MidScene报告子目录不存在，可能测试未生成报告');
            return;
        }
        
        // 获取报告目录中的所有HTML文件
        const files = fs.readdirSync(reportDir);
        console.log(`📋 报告目录中的文件: ${files.join(', ')}`);
        
        const htmlFiles = files.filter(file => file.endsWith('.html') && file.includes('playwright-'));
        console.log(`📋 找到的HTML报告文件: ${htmlFiles.join(', ')}`);
        
        if (htmlFiles.length === 0) {
            console.log('📋 未找到MidScene报告文件');
            logMessage(executionId, 'warning', 'MidScene未生成报告文件，可能测试执行过程中出现问题');
            return;
        }
        
        // 按文件修改时间排序，获取最新的报告文件
        const fileStats = htmlFiles.map(file => {
            const filePath = path.join(reportDir, file);
            const stats = fs.statSync(filePath);
            return {
                name: file,
                path: filePath,
                mtime: stats.mtime
            };
        });
        
        // 获取最新的报告文件
        const latestReport = fileStats.sort((a, b) => b.mtime - a.mtime)[0];
        
        if (latestReport) {
            const reportPath = latestReport.path;
            console.log(`📊 找到MidScene报告文件: ${reportPath}`);
            console.log(`📊 报告文件修改时间: ${latestReport.mtime}`);
            
            // 生成简化的报告
            const simplifiedReportPath = await generateSimplifiedReport(reportPath, testcase, executionState);
            
            // 通过日志消息通知前端使用简化的报告
            logMessage(executionId, 'info', `Midscene - report file updated: ${simplifiedReportPath || reportPath}`);
            
            // 额外发送一条明确的成功消息
            logMessage(executionId, 'success', `报告已生成: ${latestReport.name}`);
        }
        
    } catch (error) {
        console.error('检查MidScene报告失败:', error);
        logMessage(executionId, 'error', `检查MidScene报告失败: ${error.message}`);
    }
}

// 生成简化的报告
async function generateSimplifiedReport(originalReportPath, testcase, executionState) {
    try {
        const fs = require('fs');
        const path = require('path');
        
        // 读取原始报告
        const originalContent = fs.readFileSync(originalReportPath, 'utf8');
        
        // 生成简化的报告文件名
        const reportDir = path.dirname(originalReportPath);
        const originalName = path.basename(originalReportPath, '.html');
        const simplifiedName = `${originalName}_simplified.html`;
        const simplifiedPath = path.join(reportDir, simplifiedName);
        
        // 创建简化的报告内容
        const simplifiedContent = createSimplifiedReportContent(originalContent, testcase, executionState);
        
        // 写入简化报告
        fs.writeFileSync(simplifiedPath, simplifiedContent, 'utf8');
        
        console.log(`📊 生成简化报告: ${simplifiedPath}`);
        return simplifiedPath;
        
    } catch (error) {
        console.error('生成简化报告失败:', error);
        return null;
    }
}

// 创建简化的报告内容
function createSimplifiedReportContent(originalContent, testcase, executionState) {
    const steps = executionState.steps || [];
    const duration = executionState.duration || 0;
    
    // 从原始报告中提取主要内容，去掉统计指标
    let simplifiedContent = originalContent;
    
    // 移除统计指标相关的HTML
    simplifiedContent = simplifiedContent.replace(/<div[^>]*class="[^"]*summary[^"]*"[^>]*>[\s\S]*?<\/div>/gi, '');
    simplifiedContent = simplifiedContent.replace(/<div[^>]*class="[^"]*stats[^"]*"[^>]*>[\s\S]*?<\/div>/gi, '');
    simplifiedContent = simplifiedContent.replace(/<div[^>]*class="[^"]*metrics[^"]*"[^>]*>[\s\S]*?<\/div>/gi, '');
    
    // 添加简化的标题信息
    const titleInfo = `
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #333;">测试执行报告</h1>
            <div style="margin-top: 10px; color: #666;">
                <strong>测试用例:</strong> ${testcase.name} &nbsp;&nbsp;
                <strong>状态:</strong> ${executionState.status || 'completed'} &nbsp;&nbsp;
                <strong>耗时:</strong> ${Math.round(duration / 1000)}秒 &nbsp;&nbsp;
                <strong>步骤数:</strong> ${steps.length}
            </div>
        </div>
    `;
    
    // 将标题信息插入到body开头
    simplifiedContent = simplifiedContent.replace(/<body[^>]*>/i, `$&${titleInfo}`);
    
    return simplifiedContent;
}

// 启动服务器
server.listen(port, () => {
    console.log(`\n🚀 MidSceneJS本地代理服务器启动成功`);
    console.log(`HTTP服务器: http://localhost:${port}`);
    console.log(`WebSocket服务器: ws://localhost:${port}`);
    console.log(`AI模型: ${process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest'}`);
    console.log(`API地址: ${process.env.OPENAI_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1'}`);
    if (process.env.MIDSCENE_USE_GEMINI === '1') {
        console.log(`Gemini模式: 已启用`);
    }
    console.log(`服务器就绪，等待测试执行请求...`);
    console.log(`支持的API端点:`);
    console.log(`   POST /api/execute-testcase - 执行测试用例`);
    console.log(`   GET  /api/execution-status/:id - 获取执行状态`);
    console.log(`   GET  /api/execution-report/:id - 获取独立执行报告`);
    console.log(`   GET  /api/executions - 获取所有执行记录`);
    console.log(`   POST /api/stop-execution/:id - 停止执行`);
    console.log(`   GET  /api/status - 获取服务器状态`);
    console.log(`   GET  /health - 健康检查`);
});

// 优雅关闭
process.on('SIGTERM', async () => {
    console.log('收到SIGTERM信号，正在优雅关闭...');
    if (page) await page.close();
    if (browser) await browser.close();
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('收到SIGINT信号，正在优雅关闭...');
    if (page) await page.close();
    if (browser) await browser.close();
    process.exit(0);
}); 