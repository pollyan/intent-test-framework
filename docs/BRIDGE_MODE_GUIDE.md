# 🌉 Chrome桥接模式使用指南

## 🎯 什么是桥接模式？

桥接模式是MidSceneJS提供的一种特殊执行方式，它允许您在**本地环境**中运行自动化脚本，通过Chrome扩展连接到您的桌面Chrome浏览器。

### 🔥 核心优势

- ✅ **真正的可视化执行**：在您的Chrome浏览器中看到真实的自动化过程
- ✅ **利用本地环境**：使用您的cookies、插件、登录状态等
- ✅ **无网络延迟**：完全本地执行，响应迅速
- ✅ **便于调试**：可以随时暂停、检查、修改
- ✅ **人机协作**：支持"man-in-the-loop"模式

## 🚀 快速开始

### 步骤1：安装MidSceneJS Chrome扩展

1. **访问Chrome网上应用店**
   ```
   https://chromewebstore.google.com/detail/midscene/gbldofcpkknbggpkmbdaefngejllnief
   ```

2. **安装扩展**
   - 点击"添加至Chrome"
   - 确认安装

3. **启用扩展**
   - 确保扩展已启用
   - 可以在工具栏看到MidSceneJS图标

### 步骤2：准备本地环境

1. **创建项目目录**
   ```bash
   mkdir midscene-bridge
   cd midscene-bridge
   ```

2. **初始化项目**
   ```bash
   npm init -y
   ```

3. **安装MidSceneJS**
   ```bash
   npm install @midscene/web
   ```

4. **配置AI API密钥**
   ```bash
   # 设置环境变量（根据您使用的AI服务）
   export OPENAI_API_KEY="your-api-key"
   # 或
   export ANTHROPIC_API_KEY="your-api-key"
   ```

### 步骤3：使用Intent Test Framework生成脚本

1. **访问WebUI**
   ```
   https://intent-test-framework.vercel.app/execution
   ```

2. **选择桥接模式**
   - 选择"🌉 Chrome桥接"执行类型
   - 选择要执行的测试用例
   - 点击"🚀 开始执行"

3. **下载脚本**
   - 系统会自动生成MidSceneJS脚本
   - 脚本会自动下载到您的电脑

### 步骤4：执行脚本

1. **将脚本移动到项目目录**
   ```bash
   mv ~/Downloads/测试用例名-bridge.mjs ./
   ```

2. **启动Chrome扩展桥接模式**
   - 点击Chrome工具栏中的MidSceneJS图标
   - 切换到"Bridge Mode"标签
   - 点击"Allow connection"按钮

3. **运行脚本**
   ```bash
   node 测试用例名-bridge.mjs
   ```

4. **观察执行过程**
   - 脚本会在您的Chrome浏览器中执行
   - 您可以看到每个步骤的实时执行
   - 控制台会显示详细的执行日志

## 📋 脚本示例

以下是一个典型的桥接模式脚本：

```javascript
// MidSceneJS桥接模式脚本
// 测试用例: 百度搜索测试
// 生成时间: 2024-01-15 10:30:00

import { AgentOverChromeBridge } from '@midscene/web/bridge-mode';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

Promise.resolve(
  (async () => {
    const agent = new AgentOverChromeBridge();
    
    try {
      console.log('🌉 开始桥接模式执行: 百度搜索测试');
      
      // 连接到新标签页并导航
      await agent.connectNewTabWithUrl('https://www.baidu.com');
      console.log('✅ 已连接到新标签页: https://www.baidu.com');
      
      // 步骤 1: 搜索AI相关内容
      await agent.ai('type "人工智能" in search box');
      console.log('⌨️ 输入文本: 人工智能 到 搜索框');
      
      // 步骤 2: 点击搜索按钮
      await agent.ai('click search button');
      console.log('👆 点击: 搜索按钮');
      
      // 步骤 3: 等待结果加载
      await sleep(2000);
      console.log('⏱️ 等待 2000ms');
      
      // 步骤 4: 验证搜索结果
      await agent.aiAssert('search results are displayed');
      console.log('✅ 断言: 搜索结果已显示');
      
      console.log('🎉 测试执行完成！');
      await agent.destroy();
      
    } catch (error) {
      console.error('❌ 测试执行失败:', error.message);
      await agent.destroy();
      process.exit(1);
    }
  })()
);
```

## 🔧 高级配置

### 连接选项

```javascript
// 连接到当前标签页
await agent.connectCurrentTab();

// 连接到新标签页
await agent.connectNewTabWithUrl('https://example.com');

// 连接时的选项
await agent.connectCurrentTab({
  forceSameTabNavigation: true  // 强制在同一标签页导航
});
```

### 执行选项

```javascript
// 创建代理时的选项
const agent = new AgentOverChromeBridge({
  closeNewTabsAfterDisconnect: true  // 断开连接后关闭新标签页
});
```

## 🛠️ 故障排除

### 常见问题

#### 1. 连接超时
```
错误: Connection timeout
解决: 确保Chrome扩展已启用并点击"Allow connection"
```

#### 2. API密钥未配置
```
错误: API key not found
解决: 设置正确的环境变量
export OPENAI_API_KEY="your-key"
```

#### 3. 扩展未安装
```
错误: Extension not found
解决: 安装官方MidSceneJS Chrome扩展
```

#### 4. 脚本执行失败
```
错误: Script execution failed
解决: 检查元素定位器是否正确，页面是否已加载
```

### 调试技巧

1. **查看详细日志**
   ```bash
   DEBUG=midscene* node script.mjs
   ```

2. **使用浏览器开发者工具**
   - 按F12打开开发者工具
   - 查看Console和Network标签

3. **分步执行**
   - 在脚本中添加更多的`console.log`
   - 使用`await sleep()`增加等待时间

## 🎯 最佳实践

### 1. 脚本编写
- 使用清晰的步骤描述
- 添加适当的等待时间
- 使用具体的元素定位器

### 2. 环境准备
- 确保Chrome浏览器是最新版本
- 定期更新MidSceneJS扩展
- 保持稳定的网络连接

### 3. 调试优化
- 先在小范围测试脚本
- 逐步增加复杂度
- 记录常见问题的解决方案

## 📊 与其他模式对比

| 特性 | 桥接模式 | 云端模式 | 本地模式 |
|------|----------|----------|----------|
| 执行位置 | 客户端 | 服务器 | 客户端 |
| 可视化 | ✅ | ❌ | ✅ |
| 环境依赖 | Chrome扩展 | 无 | Playwright |
| 网络要求 | 低 | 高 | 无 |
| 调试友好 | ✅ | ❌ | ✅ |
| 设置复杂度 | 中等 | 低 | 高 |

## 🔮 进阶用法

### YAML脚本支持

您也可以使用YAML格式编写桥接模式脚本：

```yaml
target:
  url: https://www.baidu.com
  bridgeMode: newTabWithUrl
  closeNewTabsAfterDisconnect: true

tasks:
  - ai: type "人工智能" in search box
  - ai: click search button
  - sleep: 2000
  - aiAssert: search results are displayed
```

运行YAML脚本：
```bash
midscene ./test.yaml
```

### 环境变量配置

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# 其他配置
export MIDSCENE_DEBUG=true
export MIDSCENE_TIMEOUT=30000
```

## 📞 获取帮助

- **官方文档**: https://midscenejs.com/bridge-mode-by-chrome-extension
- **GitHub仓库**: https://github.com/web-infra-dev/midscene
- **示例项目**: https://github.com/web-infra-dev/midscene-example/tree/main/bridge-mode-demo

---

**开始您的桥接模式之旅，体验真正的可视化AI自动化测试！** 🚀
