# 金山云Cookie自动登录功能使用指南

## 功能概述

Intent Test Framework 现已支持金山云的自动登录功能，通过设置Cookie的方式实现免账号密码登录，提高测试自动化效率。

## 配置步骤

### 1. 环境变量配置

在项目根目录的 `.env` 文件中配置金山云认证信息：

```bash
# 金山云认证配置
KSYUN_ACCESS_KEY=your-ksyun-access-key
KSYUN_SECRET_KEY=your-ksyun-secret-key
KSYUN_REGION=cn-beijing-6
```

**可用区域选项：**
- `cn-beijing-6`: 华北1(北京)
- `cn-shanghai-3`: 华东1(上海)  
- `cn-guangzhou-1`: 华南1(广州)
- `cn-hongkong-2`: 香港
- `ap-singapore-1`: 亚太1(新加坡)
- `eu-east-1`: 欧洲东部1
- `us-east-1`: 美国东部1

### 2. 获取金山云API密钥

1. 登录金山云控制台
2. 访问 [API密钥管理页面](https://console.ksyun.com/iam#/key)
3. 创建新的API密钥或使用现有密钥
4. 复制 Access Key 和 Secret Key

## 使用方法

### 在测试步骤中使用

在测试用例编辑页面，添加"设置金山云Cookie"步骤：

#### 基本用法（使用环境变量）

```json
{
  "action": "setKsyunCookie",
  "params": {
    "target_url": "https://console.ksyun.com"
  },
  "description": "使用环境变量设置金山云Cookie并跳转到控制台"
}
```

#### 完整配置（覆盖环境变量）

```json
{
  "action": "setKsyunCookie",
  "params": {
    "access_key": "your-specific-access-key",
    "secret_key": "your-specific-secret-key",
    "region": "cn-shanghai-3",
    "target_url": "https://console.ksyun.com/compute/instance"
  },
  "description": "使用指定参数设置金山云Cookie"
}
```

### 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `access_key` | string | 否 | 金山云Access Key，如不提供则使用环境变量 |
| `secret_key` | string | 否 | 金山云Secret Key，如不提供则使用环境变量 |
| `region` | string | 否 | 金山云区域，默认为环境变量或 cn-beijing-6 |
| `target_url` | string | 否 | 设置Cookie后要跳转的目标页面 |

## 完整测试示例

以下是一个完整的金山云自动登录测试用例：

```json
{
  "name": "金山云ECS管理测试",
  "description": "自动登录金山云并管理ECS实例",
  "steps": [
    {
      "action": "setKsyunCookie",
      "params": {
        "target_url": "https://console.ksyun.com/compute/instance"
      },
      "description": "自动登录并跳转到ECS管理页面"
    },
    {
      "action": "ai_assert",
      "params": {
        "prompt": "页面显示ECS实例列表，用户已成功登录"
      },
      "description": "验证登录成功"
    },
    {
      "action": "ai_tap",
      "params": {
        "locate": "创建实例按钮"
      },
      "description": "点击创建实例"
    },
    {
      "action": "ai_wait_for",
      "params": {
        "prompt": "创建ECS实例页面加载完成"
      },
      "description": "等待创建页面加载"
    }
  ]
}
```

## 通用Cookie设置功能

除了金山云专用的Cookie设置，框架还提供了通用的Cookie设置功能：

```json
{
  "action": "setCookie",
  "params": {
    "cookies": {
      "session_id": "abc123456",
      "user_token": "xyz789",
      "preferences": "theme=dark&lang=zh"
    },
    "domain": ".example.com"
  },
  "description": "设置通用Cookie"
}
```

## 安全注意事项

1. **密钥保护**: 切勿在代码中硬编码API密钥，始终使用环境变量
2. **权限最小化**: API密钥应只授予测试所需的最小权限
3. **定期轮换**: 定期更新API密钥以提高安全性
4. **日志脱敏**: 确保日志中不会记录完整的密钥信息

## 故障排除

### 常见错误

1. **认证失败**
   - 检查 Access Key 和 Secret Key 是否正确
   - 确认密钥对应的用户有足够权限
   - 检查区域配置是否匹配

2. **Cookie设置失败**
   - 确认浏览器已正确初始化
   - 检查目标域名是否正确
   - 验证网络连接是否正常

3. **环境变量未加载**
   - 确认 `.env` 文件存在且格式正确
   - 重启应用以加载新的环境变量
   - 检查环境变量名是否拼写正确

### 调试模式

在测试执行过程中，可以在控制台查看详细的日志信息：

```javascript
// 浏览器控制台
console.log('金山云Cookie设置状态:', execution_logs);
```

## 更新日志

- **v1.0.0**: 初始版本，支持基本的金山云Cookie设置功能
- 支持环境变量配置和参数覆盖
- 支持多区域配置
- 提供通用Cookie设置功能

## 技术支持

如遇到问题，请：

1. 查看执行日志中的错误信息
2. 检查金山云控制台中的API调用记录  
3. 确认测试环境网络连接正常
4. 联系开发团队获取技术支持