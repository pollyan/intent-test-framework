# 本地代理包修复指南

## 🔧 问题描述
用户下载的本地代理包可能存在依赖缺失问题，导致启动时出现 `Cannot find module '@playwright/test'` 错误。

## 🛠️ 修复方案

### 方案1：使用自动修复脚本（推荐）
1. 在项目根目录运行：
   ```bash
   ./scripts/fix-any-proxy.sh
   ```

2. 选择要修复的代理包目录（通常选择最新的）

3. 等待修复完成

### 方案2：手动修复
1. 进入代理包目录：
   ```bash
   cd "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy 3"
   ```

2. 运行修复脚本：
   ```bash
   /Users/huian@thoughtworks.com/intent-test-framework/scripts/fix-existing-proxy.sh
   ```

### 方案3：使用内置修复功能
1. 进入代理包目录：
   ```bash
   cd "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy 3"
   ```

2. 运行修复脚本：
   ```bash
   ./fix-local-proxy.sh
   ```

## 🚀 使用步骤

### 1. 配置AI API密钥
首次运行会自动创建 `.env` 文件，需要编辑并添加API密钥：

```env
# 阿里云DashScope (推荐)
OPENAI_API_KEY=sk-your-dashscope-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
```

### 2. 启动服务器
```bash
./start.sh
```

### 3. 验证启动成功
看到以下信息表示启动成功：
```
🚀 MidSceneJS本地代理服务器启动成功
🌐 HTTP服务器: http://localhost:3001
🔌 WebSocket服务器: ws://localhost:3001
✨ 服务器就绪，等待测试执行请求...
```

## 🔍 修复内容

### 修复的依赖问题
- ✅ 添加缺失的 `@playwright/test` 依赖
- ✅ 添加缺失的 `axios` 依赖
- ✅ 修复 Express 版本兼容性问题（5.1.0 → 4.18.2）
- ✅ 更新启动脚本依赖检查逻辑

### 增强的功能
- 🔧 自动检测关键依赖是否存在
- 🧹 自动清理损坏的 node_modules
- 📦 智能重新安装依赖
- 🔍 验证依赖完整性
- 🧪 测试服务器启动

## 📋 故障排除

### 常见错误
1. **Cannot find module '@playwright/test'**
   - 原因：旧版本代理包缺少依赖
   - 解决：运行修复脚本

2. **端口被占用**
   - 原因：3001端口已被使用
   - 解决：在 `.env` 文件中设置 `PORT=3002`

3. **依赖安装失败**
   - 原因：网络问题或npm缓存问题
   - 解决：清理缓存后重试
   ```bash
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```

### 支持的代理包版本
- ✅ intent-test-proxy
- ✅ intent-test-proxy 2
- ✅ intent-test-proxy 3
- ✅ intent-test-proxy 4
- ✅ intent-test-proxy 5

## 📞 技术支持

如果修复脚本无法解决问题，请：
1. 检查Node.js版本（需要16.x或更高）
2. 确保网络连接正常
3. 查看完整的错误日志
4. 联系技术支持

---

**修复成功后，即可正常使用本地代理模式进行AI测试！** 🎉