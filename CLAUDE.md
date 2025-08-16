# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Guidelines

**Language**: Always respond in Chinese (中文) when working with this project. All communication, explanations, and documentation should be in Chinese unless specifically requested otherwise.

## Overview

This is the Intent Test Framework - an AI-driven web automation testing platform that provides complete WebUI interface for test case management, execution monitoring, and result analysis. The system uses MidSceneJS for AI-powered visual testing and supports natural language test descriptions.

## Design System

### Minimal Design Reference
The target design system is stored in `/Users/huian@thoughtworks.com/intent-test-framework/minimal-preview` directory. When implementing new features or modifying existing ones, **ALWAYS** reference these design files:

- `minimal-preview/assets/css/minimal-style.css` - Core CSS framework
- `minimal-preview/dashboard.html` - Dashboard page design
- `minimal-preview/testcases.html` - Test cases management page design
- `minimal-preview/execution.html` - Execution console design
- `minimal-preview/reports.html` - Reports page design
- `minimal-preview/index.html` - Main entry page design

### Design Principles
1. **Extreme Minimalism**: Clean, focused interfaces without unnecessary elements
2. **No Icons**: Text-only buttons and interfaces, no emoji or symbol icons
3. **Consistent Typography**: System fonts with specific weight and spacing
4. **Neutral Colors**: Primary palette uses grays and whites
5. **Grid Layouts**: Consistent grid systems for content organization
6. **Status Indicators**: Simple colored dots for status representation
7. **Unified Components**: Consistent button styles, form elements, and list items

## Development Commands

### Setup and Installation
```bash
# Setup development environment
python scripts/setup_dev_env.py

# Install Python dependencies
pip install -r requirements.txt
pip install -r web_gui/requirements.txt

# Install Node.js dependencies  
npm install

# Setup environment variables
cp .env.example .env
# Edit .env with your AI API keys
```

### Running the Application
```bash
# Start MidScene server (AI engine)
node midscene_server.js

# Start Web GUI application
python web_gui/run_enhanced.py

# Alternative: Start enhanced web app
python web_gui/app_enhanced.py
```

### Development Tools
```bash
# Run code quality check
python scripts/quality_check.py

# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_models.py -v

# Run Node.js related tests
npm test
```

### Local Proxy Server
```bash
# Start local proxy server for AI testing
python start_midscene_server.py
```

## Architecture

### Core Components

1. **Web GUI Layer** (`web_gui/`)
   - `app.py` / `app_enhanced.py`: Main Flask application
   - `api_routes.py`: API endpoints
   - `models.py`: SQLAlchemy database models
   - `templates/`: HTML templates
   - `services/ai_enhanced_parser.py`: Natural language parsing

2. **AI Engine Layer**
   - `midscene_python.py`: Python wrapper for MidSceneJS
   - `midscene_server.js`: Node.js server for AI operations
   - Integrates with MidSceneJS library for visual AI testing

3. **Database Layer**
   - PostgreSQL for production (Supabase)
   - SQLite for development
   - Models: TestCase, ExecutionHistory, Template, StepExecution

4. **Cloud Deployment**
   - `api/index.py`: Vercel serverless entry point
   - `vercel.json`: Vercel deployment configuration
   - Generates downloadable local proxy packages

### Data Flow

1. **Test Creation**: User creates test cases via WebUI → Stored in database
2. **Natural Language Processing**: AI parses natural language descriptions into structured steps
3. **Test Execution**: MidSceneJS AI engine executes tests in browser
4. **Real-time Updates**: WebSocket connections provide live execution status
5. **Results Storage**: Execution results, screenshots, and logs stored in database

### Key Architectural Patterns

- **Microservices**: Flask web app + Node.js AI server
- **Event-driven**: WebSocket for real-time communication
- **AI-first**: All element interactions use AI vision models
- **Hybrid deployment**: Local development + cloud distribution

## Test Structure

Test cases are structured as JSON with steps containing:
- `action`: Type of action (navigate, ai_input, ai_tap, ai_assert, etc.)
- `params`: Action-specific parameters
- `description`: Human-readable step description

### Variable References

The framework supports dynamic variable references using `${variable}` syntax:

- **Basic variable**: `${product_name}`
- **Object property**: `${product_info.name}`
- **Multi-level property**: `${step_1_result.data.items.price}`
- **Mixed text**: `"商品名称：${product_info.name}，价格：${product_info.price}元"`

Variables are automatically resolved during test execution. If a variable is not found, the original text is preserved and a warning is logged.

Example test case with variables:
```json
{
  "name": "Product Search Test",
  "steps": [
    {
      "action": "navigate",
      "params": {"url": "https://example.com"},
      "description": "Navigate to example.com"
    },
    {
      "action": "aiQuery",
      "params": {
        "query": "提取商品信息",
        "dataDemand": "{name: string, price: number, stock: number}"
      },
      "output_variable": "product_info",
      "description": "Extract product information"
    },
    {
      "action": "ai_input", 
      "params": {
        "text": "${product_info.name}",
        "locate": "search box"
      },
      "description": "Enter product name from extracted data"
    },
    {
      "action": "ai_assert",
      "params": {
        "condition": "商品价格显示为${product_info.price}元"
      },
      "description": "Verify product price matches extracted data"
    }
  ]
}
```

## Database Schema

### Core Tables
- `test_cases`: Test case definitions and metadata
- `execution_history`: Test execution records
- `step_executions`: Individual step execution details
- `templates`: Reusable test templates

### Key Relationships
- TestCase → ExecutionHistory (1:N)
- ExecutionHistory → StepExecution (1:N)
- Template → TestCase (1:N)

## Environment Configuration

### Required Environment Variables
```env
# AI Service Configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# Database Configuration  
DATABASE_URL=postgresql://user:pass@host:port/db

# Application Settings
DEBUG=false
SECRET_KEY=your_secret_key
```

### AI Model Support
- Primary: Qwen VL (Alibaba Cloud DashScope)
- Alternative: GPT-4V (OpenAI)
- Configured via `MIDSCENE_MODEL_NAME` and `OPENAI_BASE_URL`

## Cloud Deployment

### Vercel Deployment
- Entry point: `api/index.py`
- Serverless function generates local proxy packages
- Automatic deployment from GitHub pushes

### Local Proxy Distribution
- Users download proxy packages from cloud interface
- Packages include MidSceneJS server + dependencies
- Self-contained for local AI testing execution

## Development Guidelines

### Code Quality
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Comprehensive docstrings for all public functions
- Error handling with custom exception classes

### Testing
- Unit tests in `tests/` directory
- Integration tests for API endpoints
- AI functionality tests with mock responses

### Commit Standards
```
<type>(<scope>): <subject>

Examples:
feat(webui): add screenshot history feature
fix(api): resolve test case deletion error
docs(readme): update installation instructions
```

### File Organization
- Python files: `snake_case`
- JavaScript files: `camelCase`
- HTML templates: `template_name.html`
- Configuration: Environment variables over hardcoded values

## Local Proxy Package Management

The system generates downloadable local proxy packages containing:
- `midscene_server.js`: AI testing server
- `package.json`: Dependencies including @playwright/test, axios
- `start.sh/.bat`: Smart startup scripts with dependency checking
- Enhanced error handling and auto-repair functionality

Users download from https://intent-test-framework.vercel.app/local-proxy for the latest version.

## UI/UX Implementation Guidelines

### Template Structure
All templates should follow the minimal design pattern:
1. Use `base_layout.html` as parent template
2. Reference `minimal-preview/` designs for layout structure
3. Apply consistent spacing and typography
4. Use grid layouts for content organization

### Component Standards
- **Buttons**: Use `btn`, `btn-primary`, `btn-ghost`, `btn-small` classes
- **Forms**: Use `form-group`, `form-label`, `form-input`, `form-select` classes
- **Lists**: Use `list`, `list-item`, `list-item-content` structure
- **Cards**: Use `card`, `card-title`, `card-subtitle` hierarchy
- **Status**: Use `status` with color variants (`status-success`, `status-warning`, `status-error`)

### List Item Design Standards
Based on the testcases management page implementation, all list items should follow these design patterns:

#### HTML Structure
```html
<div class="list-item" title="点击进入编辑模式" onclick="editItem(id)">
    <div class="list-item-content">
        <div class="list-item-title">主标题</div>
        <div class="list-item-subtitle">副标题或描述</div>
        <div class="list-item-meta">
            <span class="text-gray-600">元数据1</span>
            <span class="text-gray-400">•</span>
            <span class="text-gray-600">元数据2</span>
            <!-- 更多元数据... -->
        </div>
    </div>
    <div class="flex items-center gap-1">
        <button class="btn btn-small btn-ghost" onclick="event.stopPropagation(); action1()">操作1</button>
        <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); action2()">操作2</button>
        <button class="btn btn-small btn-ghost" onclick="event.stopPropagation(); action3()">操作3</button>
        <div class="status status-success" title="状态描述"></div>
    </div>
</div>
```

#### CSS Styling
```css
/* 列表项目点击效果样式 */
.list-item {
    cursor: pointer;
    transition: background-color 0.2s ease, transform 0.1s ease;
}

.list-item:hover {
    background-color: #f8f9fa;
    transform: translateY(-1px);
}

.list-item:active {
    transform: translateY(0);
}

/* 状态指示器增强效果 */
.status {
    cursor: help;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.status:hover {
    transform: scale(1.3);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
```

#### JavaScript Interaction
```javascript
// 创建列表项目
function createListItem(item) {
    const listItem = document.createElement('div');
    listItem.className = 'list-item';
    listItem.title = '点击进入编辑模式';  // 适当的提示文本
    listItem.onclick = () => editItem(item.id);
    
    // 设置HTML内容...
    
    return listItem;
}

// 按钮事件处理必须包含 event.stopPropagation()
function handleButtonClick(event, action) {
    event.stopPropagation();
    action();
}
```

#### Design Principles
1. **可点击性**: 整个列表项目都应该可以点击进入主要操作（通常是编辑）
2. **视觉反馈**: 悬停时有背景色变化和轻微上移效果
3. **事件隔离**: 按钮区域使用 `event.stopPropagation()` 防止冒泡
4. **一致的布局**: 左侧内容区域 + 右侧操作区域
5. **状态指示**: 使用彩色圆点表示状态，支持悬停放大效果
6. **元数据展示**: 使用灰色文本和分隔符展示次要信息

### Interactive Features
- Implement real-time filtering and search
- Use debouncing for search inputs (500ms)
- Provide immediate feedback for user actions
- Maintain consistent pagination patterns
- All list items should be clickable with hover effects
- Use consistent button layouts and event handling

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
ALWAYS reference the minimal-preview directory designs when implementing or modifying UI components.
NEVER add icons or emoji symbols to interfaces - use text-only approach.
ALWAYS maintain the extreme minimalist design philosophy.
永远不要做假功能，真实实现所有功能，如果有问题及时反馈，不能骗人。

## 🏗️ 架构设计原则

### 核心架构原则

**🔴 架构优先原则**：在实现任何功能时，必须优先考虑架构的合理性和代码质量，不能为了快速实现功能而忽视架构设计的基本原则。

### 关键设计原则

1. **单一职责原则（SRP）**
   - 每个类和函数应该只有一个改变的理由
   - 避免创建过于庞大的类或函数

2. **DRY原则（Don't Repeat Yourself）**
   - 避免重复代码，特别是数据库连接、错误处理等通用逻辑
   - 创建可复用的服务层和工具函数
   - 统一的配置管理和资源管理

3. **依赖倒置原则**
   - 高层模块不应该依赖低层模块，两者都应该依赖抽象
   - 使用服务层抽象数据访问逻辑
   - 避免在控制器中直接编写SQL或复杂业务逻辑

4. **关注点分离**
   - 数据访问层：统一的数据库操作服务
   - 业务逻辑层：核心业务规则和流程
   - 控制器层：HTTP请求处理和响应格式化
   - 表示层：用户界面和交互逻辑

### 具体实施要求

#### 数据访问层设计
- **禁止**在API控制器中直接编写psycopg2连接代码
- **禁止**在多个地方重复相同的数据库连接逻辑
- **必须**使用统一的数据库服务层（DatabaseService）
- **必须**正确使用SQLAlchemy ORM和Flask应用上下文
- **必须**统一处理数据库事务和错误

#### 代码质量要求
- **重构优于修补**：当发现架构问题时，优先进行重构而不是局部修补
- **服务层抽象**：将复杂的业务逻辑抽象为服务层，避免在控制器中堆积代码
- **错误处理统一**：使用统一的错误处理机制，避免散落的try-catch块
- **资源管理**：使用上下文管理器和连接池管理数据库连接

#### 架构决策记录
- 当遇到SQLAlchemy上下文问题时，正确的解决方案是修复应用上下文，而不是绕过ORM
- 当发现重复代码时，立即进行抽象和重构，而不是继续复制
- 在添加新功能时，首先评估对现有架构的影响，必要时先改善架构再添加功能

### 架构评审清单

在提交代码前，必须确认：
- [ ] 是否遵循了单一职责原则？
- [ ] 是否存在重复代码？
- [ ] 是否正确使用了服务层抽象？
- [ ] 是否有适当的错误处理和资源管理？
- [ ] 数据库操作是否使用了统一的服务接口？
- [ ] 是否符合项目的整体架构风格？

## 🚫 严格禁止事项

**绝对禁止添加模拟数据或假数据**：
- 永远不要在API中返回模拟数据、示例数据或假数据
- 永远不要创建mock响应来"临时解决"问题
- 所有API必须返回真实的数据库数据或明确的错误信息
- 如果数据库查询有问题，必须真正修复查询问题，而不是返回假数据
- 如果功能暂时无法实现，必须明确告知用户，不能用假数据欺骗
- 用户要求看到真实数据时，必须确保连接的是真实的数据库并返回真实数据

## 🧪 测试驱动开发（TDD）原则

### 核心TDD理念

**🔴 测试优先原则**：任何新功能开发必须严格遵循TDD流程，先编写测试，再实现功能，确保代码质量和功能正确性。

### TDD开发流程

#### 标准TDD循环（Red-Green-Refactor）

1. **🔴 Red（编写失败的测试）**
   ```bash
   # 1. 编写测试用例，描述期望的功能行为
   # 2. 运行测试，确认测试失败（因为功能还未实现）
   pytest tests/unit/test_new_feature.py -v
   ```

2. **🟢 Green（实现最小可工作代码）**
   ```bash
   # 1. 编写最少的代码让测试通过
   # 2. 运行测试确认通过
   pytest tests/unit/test_new_feature.py -v
   ```

3. **🔵 Refactor（重构优化代码）**
   ```bash
   # 1. 优化代码结构，提升代码质量
   # 2. 运行所有测试确保无破坏性变更
   pytest tests/ -v
   ```

### 双层测试策略

#### 1. 单元测试（Unit Tests）
**目标**：测试单个函数、类方法的业务逻辑正确性

**覆盖范围**：
- 数据模型方法（`models.py`中的业务逻辑）
- 服务层函数（`services/`目录下的业务服务）
- 工具函数（`utils/`目录下的通用函数）
- 数据验证逻辑

**测试位置**：`tests/unit/`
```python
# 示例：tests/unit/test_testcase_model.py
def test_testcase_to_dict_with_stats():
    """测试TestCase.to_dict方法包含统计信息"""
    testcase = TestCase(name="测试用例", steps="[]")
    result = testcase.to_dict(include_stats=True)
    assert 'execution_count' in result
    assert 'success_rate' in result
```

#### 2. API集成测试（API Tests）
**目标**：测试HTTP API端点的完整请求-响应流程

**覆盖范围**：
- API端点的HTTP状态码
- 请求参数验证
- 响应数据格式
- 错误处理机制
- 数据库事务完整性

**测试位置**：`tests/api/`
```python
# 示例：tests/api/test_testcase_api.py
def test_create_testcase_success(client):
    """测试创建测试用例API成功场景"""
    data = {
        "name": "新测试用例",
        "description": "测试描述",
        "steps": [{"action": "navigate", "params": {"url": "https://example.com"}}]
    }
    response = client.post('/api/testcases', json=data)
    assert response.status_code == 201
    assert response.json['code'] == 201
    assert response.json['data']['name'] == "新测试用例"
```

### TDD实施规范

#### 新功能开发流程

1. **需求分析和测试规划**
   ```bash
   # 1. 分析功能需求，确定测试场景
   # 2. 创建测试文件和测试用例框架
   touch tests/unit/test_new_service.py
   touch tests/api/test_new_api.py
   ```

2. **编写单元测试**
   ```python
   # 先编写单元测试，覆盖核心业务逻辑
   def test_new_service_basic_functionality():
       # 测试服务层基础功能
       pass
   
   def test_new_service_error_handling():
       # 测试异常情况处理
       pass
   ```

3. **编写API测试**
   ```python
   # 编写API级别的集成测试
   def test_new_api_endpoint_success():
       # 测试API成功场景
       pass
   
   def test_new_api_endpoint_validation():
       # 测试API参数验证
       pass
   ```

4. **实现功能代码**
   ```python
   # 按照测试期望实现最小可工作代码
   # 先让单元测试通过，再让API测试通过
   ```

5. **运行回归测试**
   ```bash
   # 确保新功能不破坏现有功能
   pytest tests/ -v --cov=web_gui --cov-report=html
   ```

#### 修改现有功能流程

1. **先增加测试覆盖**
   ```bash
   # 为现有功能补充测试用例
   pytest tests/unit/test_existing_feature.py -v
   ```

2. **修改实现代码**
   ```python
   # 在测试保护下进行修改
   ```

3. **验证测试通过**
   ```bash
   # 确保所有相关测试通过
   pytest tests/ -k "existing_feature" -v
   ```

### 测试命令规范

#### 日常开发测试命令
```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行所有API测试  
pytest tests/api/ -v

# 运行特定功能的测试
pytest tests/ -k "testcase" -v

# 运行测试并生成覆盖率报告
pytest tests/ -v --cov=web_gui --cov-report=html --cov-report=term

# 运行测试并显示缺失的覆盖行
pytest tests/ -v --cov=web_gui --cov-report=term-missing
```

#### CI/CD测试命令
```bash
# 完整的测试套件运行（提交前必须运行）
pytest tests/ -v --cov=web_gui --cov-report=html --cov-fail-under=80

# 快速冒烟测试
pytest tests/unit/ tests/api/ -v --maxfail=5
```

### 测试质量标准

#### 覆盖率要求
- **单元测试覆盖率**：≥ 80%
- **API测试覆盖率**：100%（所有API端点必须有测试）
- **关键业务逻辑覆盖率**：≥ 95%

#### 测试质量检查清单
- [ ] 测试名称清晰描述测试场景
- [ ] 测试用例包含正常场景和边界情况
- [ ] 测试数据使用工厂模式或fixture
- [ ] 测试相互独立，可以单独运行
- [ ] 测试执行速度快（单元测试 < 1s，API测试 < 5s）
- [ ] 测试失败时提供清晰的错误信息

### 测试数据管理

#### 测试数据原则
- **隔离性**：每个测试使用独立的测试数据
- **可重复性**：测试结果必须可重现
- **清理性**：测试后自动清理测试数据

#### 测试工具和库
```python
# 推荐测试工具栈
pytest              # 测试框架
pytest-cov          # 覆盖率插件
pytest-mock         # Mock对象支持
pytest-flask        # Flask测试支持
factory-boy         # 测试数据工厂
responses           # HTTP请求Mock
```

### TDD实施检查清单

#### 开发新功能前检查
- [ ] 是否已创建对应的单元测试文件？
- [ ] 是否已创建对应的API测试文件？
- [ ] 测试用例是否覆盖主要场景和边界情况？
- [ ] 测试是否运行失败（Red阶段）？

#### 功能实现后检查
- [ ] 所有新增测试是否通过（Green阶段）？
- [ ] 是否对代码进行了重构优化（Refactor阶段）？
- [ ] 现有测试是否全部通过？
- [ ] 代码覆盖率是否达到标准？

#### 提交代码前检查
- [ ] 运行完整测试套件无报错？
- [ ] 测试覆盖率报告符合要求？
- [ ] 新增的API端点都有对应测试？
- [ ] 测试执行时间在可接受范围内？

### 持续改进

#### 测试债务管理
- 定期识别缺失测试的代码区域
- 优先为关键业务逻辑补充测试
- 逐步提升整体测试覆盖率

#### 测试效率优化
- 使用并行测试执行提升速度
- 优化测试数据库操作减少I/O时间
- 合理使用Mock减少外部依赖

通过严格遵循TDD原则，确保每一行代码都经过测试验证，从根本上提升代码质量和系统稳定性。