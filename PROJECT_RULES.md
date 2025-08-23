# Intent Test Framework - 项目开发规范

> 本文档定义了Intent Test Framework项目的开发规范和最佳实践。

## 🎯 项目概述

Intent Test Framework是一个AI驱动的Web自动化测试平台，专注于：
- 自然语言测试描述
- AI视觉测试执行
- 完整的WebUI管理界面
- 测试结果分析和报告

## 📋 代码质量标准

### Python代码规范

- **编码风格**: 严格遵循PEP 8标准
- **行长度**: 最大88字符（Black格式化工具标准）
- **导入规范**: 按标准库、第三方库、本地导入的顺序排列
- **类型提示**: 公共函数和方法必须包含类型提示
- **文档字符串**: 所有公共类、函数必须有完整的docstring

#### 必需工具
```bash
pip install black flake8 mypy
```

### JavaScript代码规范

- **缩进**: 使用4个空格，不使用Tab
- **分号**: 语句结尾必须使用分号
- **命名**: 使用camelCase命名约定
- **函数**: 尽量使用箭头函数

### 文档注释要求

#### Python文档字符串格式
```python
def function_name(param1: str, param2: int = 0) -> bool:
    """简短的一行描述。
    
    详细描述（如果需要）。
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述，默认值0
    
    Returns:
        返回值的描述
    
    Raises:
        ExceptionType: 异常情况的描述
    """
```

## 🏗️ 架构设计原则

### 单一职责原则 (SRP)
- 每个模块、类、函数应该只有一个明确的职责
- 避免创建过于庞大的"万能"类

### 依赖注入和抽象
- 使用服务层抽象数据访问逻辑
- 避免在控制器中直接编写数据库操作代码
- 通过依赖注入提高代码可测试性

### 错误处理统一化
- 使用统一的异常处理机制
- 自定义异常类型，提供有意义的错误信息
- 记录详细的错误日志

### 安全最佳实践
- 永远不要在代码中硬编码密钥、密码等敏感信息
- 使用环境变量管理配置
- 防范SQL注入、XSS等常见安全问题

## 🧪 测试策略

### 测试驱动开发(TDD)
- **Red-Green-Refactor**循环必须严格遵循
- 先编写测试，再实现功能
- 重构时确保测试始终通过

### 双层测试架构
1. **单元测试** (`tests/unit/`)
   - 测试业务逻辑和数据模型方法
   - 使用工厂模式创建测试数据
   - 覆盖率要求 ≥ 80%

2. **API集成测试** (`tests/api/`)
   - 测试HTTP API端点完整流程
   - 100%API端点覆盖率
   - 包括错误处理和边界情况

### 测试命令规范
```bash
# 运行所有测试
pytest tests/ -v --cov=web_gui --cov-report=html

# 运行单元测试
pytest tests/unit/ -v

# 运行API测试
pytest tests/api/ -v
```

## 📁 项目结构

```
intent-test-framework/
├── web_gui/                    # 主应用目录
│   ├── api/                   # API蓝图模块
│   ├── models.py              # 数据库模型
│   ├── services/              # 业务逻辑服务层
│   ├── templates/             # HTML模板
│   ├── static/                # 静态资源
│   └── core/                  # 应用核心组件
├── tests/                     # 测试目录
│   ├── unit/                  # 单元测试
│   ├── api/                   # API集成测试
│   └── conftest.py            # 测试配置
├── scripts/                   # 开发工具脚本
├── PRD/                       # 产品需求文档
├── TASK/                      # 任务和开发计划
└── docs/                      # 项目文档
```

## 🔧 开发工具链

### 必需工具
- **Python**: 3.9+
- **Node.js**: 16+
- **数据库**: PostgreSQL (生产) / SQLite (开发)

### 推荐工具
- **IDE**: VS Code + Python/JavaScript扩展
- **版本控制**: Git
- **包管理**: pip (Python) + npm (JavaScript)

### 代码质量工具
```bash
# Python
pip install black flake8 mypy pytest pytest-cov

# 运行质量检查
python scripts/quality_check.py --fix
```

## 🚀 开发流程

### Git工作流
1. **分支命名**:
   - `feature/功能名称`
   - `bugfix/问题描述`  
   - `hotfix/紧急修复`

2. **提交信息格式**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型说明:
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建工具、辅助工具变动

### 开发检查清单
- [ ] 代码通过所有测试
- [ ] 代码覆盖率达到要求
- [ ] 通过代码质量检查
- [ ] 更新相关文档
- [ ] 遵循安全最佳实践

## 📊 性能要求

### API性能标准
- 健康检查接口: < 100ms
- 数据查询接口: < 500ms
- 复杂业务逻辑: < 2s

### 数据库优化
- 合理使用索引
- 避免N+1查询问题
- 使用连接池管理连接
- 定期分析查询性能

## 🔒 安全要求

### 输入验证
- 所有用户输入必须验证和消毒
- 使用参数化查询防止SQL注入
- 限制文件上传大小和类型

### 访问控制
- 实现适当的身份认证和授权
- 遵循最小权限原则
- 定期审查访问权限

### 数据保护
- 敏感数据加密存储
- 使用HTTPS传输
- 定期安全漏洞扫描

## 🌍 国际化和本地化

- 所有用户界面文本支持中文
- API错误消息使用中文
- 日志记录使用中文
- 文档优先使用中文

## 📈 监控和日志

### 应用监控
- 系统资源使用监控
- API性能监控
- 错误率追踪
- 用户行为分析

### 日志规范
- 使用结构化日志格式
- 包含请求ID进行链路追踪
- 分级记录（DEBUG/INFO/WARN/ERROR）
- 敏感信息脱敏

## 🔄 持续改进

### 定期Review
- 每月进行代码质量review
- 季度进行架构设计review
- 持续优化性能瓶颈

### 技术债务管理
- 记录和跟踪技术债务
- 制定还债计划
- 平衡功能开发和技术改进

## 📞 支持和反馈

- 开发问题: 通过GitHub Issues报告
- 紧急问题: 联系项目维护者
- 功能建议: 通过RFC流程提出

---

**最后更新**: 2025年8月
**版本**: 1.0
**维护者**: Intent Test Framework团队