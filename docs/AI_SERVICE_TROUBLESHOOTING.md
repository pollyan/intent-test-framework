# AI服务启动失败问题排查与修复手册

## 🚨 问题描述

线上环境启动AI助手时出现500内部服务器错误，错误信息如下：
```
AxiosError: Request failed with status code 500
```

## 🔍 诊断步骤

### 1. 运行诊断脚本

首先运行AI服务诊断脚本：
```bash
cd /path/to/intent-test-framework
python3 scripts/diagnose_ai_service.py
```

### 2. 检查后端日志

查看Flask应用的错误日志：
```bash
# 如果使用我们的dev脚本
./dev.sh logs

# 或者直接查看日志文件
tail -f /tmp/ai4se_flask.log
```

### 3. 检查数据库配置

访问配置管理页面：`http://your-domain/config-management`
确认有默认的AI配置且配置完整。

## 🛠️ 常见问题及解决方案

### 问题1：AI配置缺失或不完整

**症状：**
- 诊断脚本显示"数据库中没有AI配置"
- 或"默认配置缺少字段"

**解决方案：**
1. 访问配置管理页面添加AI配置
2. 或运行初始化脚本：
   ```bash
   python3 scripts/init_default_config.py
   ```

### 问题2：API密钥无效或过期

**症状：**
- 错误信息包含"unauthorized"或"401"
- 诊断脚本显示"AI API身份验证失败"

**解决方案：**
1. 检查API密钥是否有效
2. 确认API密钥有足够的额度
3. 更新配置管理页面中的API密钥

### 问题3：API端点配置错误

**症状：**
- 错误信息包含"404"或"not found"
- 诊断脚本显示"AI API端点不存在"

**解决方案：**
1. 检查`base_url`配置是否正确
2. 常用的端点：
   - OpenAI: `https://api.openai.com/v1`
   - 阿里云通义千问: `https://dashscope.aliyuncs.com/compatible-mode/v1`
   - 其他兼容OpenAI的API端点

### 问题4：消息内容过长

**症状：**
- 错误信息包含"500"或"internal server error"
- 特别是在发送bundle激活消息时

**解决方案：**
1. **已修复** - 我们添加了消息长度检查和截断逻辑
2. 如果仍有问题，可以尝试减少bundle文件的大小

### 问题5：网络连接问题

**症状：**
- 错误信息包含"connection"或"timeout"
- 诊断脚本显示连接失败

**解决方案：**
1. 检查服务器的网络连接
2. 确认防火墙允许对外连接
3. 如果在内网环境，检查代理设置

### 问题6：Bundle文件缺失

**症状：**
- 诊断脚本显示"Bundle文件不存在"
- 启动助手时立即失败

**解决方案：**
1. 确认以下文件存在：
   - `intelligent-requirements-analyzer/dist/intelligent-requirements-analyst-bundle.txt`
   - `intelligent-requirements-analyzer/dist/testmaster-song-bundle.txt`
2. 如果文件缺失，从版本控制系统恢复

## 🔧 修复后的改进

我们已经对代码进行了以下改进：

### 1. 增强错误处理
- 添加了详细的错误分类和用户友好的错误信息
- 改进了AI服务初始化的配置验证
- 增加了消息长度检查和自动截断

### 2. 配置验证
- 在获取AI服务时验证配置完整性
- 添加了更好的ImportError处理

### 3. 诊断工具
- 创建了全面的AI服务诊断脚本
- 可以快速识别配置问题

### 4. API错误分析
- 详细分析HTTP错误码，提供针对性的解决建议
- 区分不同类型的错误（认证、网络、服务端等）

## 🚀 部署检查清单

在部署到线上环境之前，请检查：

- [ ] 运行诊断脚本确认所有检查通过
- [ ] 确认数据库中有有效的默认AI配置
- [ ] 测试AI API连接成功
- [ ] 确认bundle文件完整
- [ ] 检查服务器日志没有错误

## 📞 如果问题仍然存在

1. 收集详细的错误日志
2. 运行诊断脚本并保存输出
3. 检查网络连接和API服务状态
4. 考虑是否是API服务提供商的问题

## 🎯 预防措施

1. **定期检查** - 设置监控告警，定期检查AI服务状态
2. **备份配置** - 定期备份数据库配置
3. **API额度监控** - 监控API使用量和剩余额度
4. **健康检查** - 在应用启动时进行AI服务健康检查

---

*本手册基于实际问题分析和修复经验编写，旨在快速解决线上AI服务问题。*
