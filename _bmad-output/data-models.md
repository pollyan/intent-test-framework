# 数据模型文档

## 概述

本文档描述 AI4SE Toolbox 的数据库模型定义，使用 Flask-SQLAlchemy ORM。

## ER 图

```
┌─────────────────┐       ┌─────────────────────┐       ┌──────────────────┐
│   test_cases    │       │  execution_history  │       │  step_executions │
├─────────────────┤       ├─────────────────────┤       ├──────────────────┤
│ id (PK)         │◄──────│ test_case_id (FK)   │◄──────│ execution_id(FK) │
│ name            │   1:N │ id (PK)             │   1:N │ id (PK)          │
│ description     │       │ execution_id        │       │ step_index       │
│ steps (JSON)    │       │ status              │       │ status           │
│ category        │       │ mode                │       │ screenshot_path  │
│ priority        │       │ browser             │       │ ai_confidence    │
│ tags            │       │ start_time          │       │ ai_decision      │
│ created_by      │       │ end_time            │       │ error_message    │
│ created_at      │       │ duration            │       │ created_at       │
│ updated_at      │       │ steps_total/passed  │       └──────────────────┘
│ is_active       │       │ error_message       │
└─────────────────┘       └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │ 1:N            │ 1:N            │
                    ▼                ▼                ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │execution_variable│ │variable_reference│ │    templates    │
          ├─────────────────┤ ├─────────────────┤ ├─────────────────┤
          │ id (PK)         │ │ id (PK)         │ │ id (PK)         │
          │ execution_id    │ │ execution_id    │ │ name            │
          │ variable_name   │ │ step_index      │ │ description     │
          │ variable_value  │ │ variable_name   │ │ category        │
          │ data_type       │ │ reference_path  │ │ steps_template  │
          │ source_step_idx │ │ resolved_value  │ │ parameters      │
          │ is_encrypted    │ │ resolution_stat │ │ usage_count     │
          └─────────────────┘ └─────────────────┘ └─────────────────┘


┌─────────────────────┐       ┌─────────────────────┐
│requirements_sessions│       │requirements_messages│
├─────────────────────┤       ├─────────────────────┤
│ id (PK, UUID)       │◄──────│ session_id (FK)     │
│ project_name        │   1:N │ id (PK)             │
│ session_status      │       │ message_type        │
│ current_stage       │       │ content             │
│ user_context (JSON) │       │ message_metadata    │
│ ai_context (JSON)   │       │ attached_files      │
│ consensus_content   │       │ created_at          │
│ created_at          │       └─────────────────────┘
│ updated_at          │
└─────────────────────┘

┌─────────────────────┐
│requirements_ai_cfg  │
├─────────────────────┤
│ id (PK)             │
│ config_name         │
│ api_key             │
│ base_url            │
│ model_name          │
│ is_default          │
│ is_active           │
│ created_at          │
│ updated_at          │
└─────────────────────┘
```

## 模型定义

### TestCase (测试用例)

```python
class TestCase(db.Model):
    __tablename__ = "test_cases"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text, nullable=False)  # JSON 字符串
    tags = db.Column(db.String(500))            # 逗号分隔
    category = db.Column(db.String(100))
    priority = db.Column(db.Integer, default=3)  # 1-5
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
```

**Steps JSON 结构：**
```json
[
  {
    "type": "goto",
    "params": {"url": "https://example.com"},
    "description": "打开首页"
  },
  {
    "type": "aiInput",
    "params": {"text": "${username}", "locate": "用户名输入框"},
    "description": "输入用户名",
    "output_variable": "input_result"
  },
  {
    "type": "aiAssert",
    "params": {"condition": "页面显示欢迎信息"},
    "description": "验证登录成功"
  }
]
```

### ExecutionHistory (执行历史)

```python
class ExecutionHistory(db.Model):
    __tablename__ = "execution_history"
    
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(50), unique=True, nullable=False)
    test_case_id = db.Column(db.Integer, db.ForeignKey("test_cases.id"))
    status = db.Column(db.String(50))  # running, success, failed, stopped
    mode = db.Column(db.String(20), default="headless")  # browser, headless
    browser = db.Column(db.String(50), default="chrome")
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # 毫秒
    steps_total = db.Column(db.Integer)
    steps_passed = db.Column(db.Integer)
    steps_failed = db.Column(db.Integer)
    result_summary = db.Column(db.Text)  # JSON
    error_message = db.Column(db.Text)
    error_stack = db.Column(db.Text)
    executed_by = db.Column(db.String(100))
```

### StepExecution (步骤执行)

```python
class StepExecution(db.Model):
    __tablename__ = "step_executions"
    
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(50), db.ForeignKey("execution_history.execution_id"))
    step_index = db.Column(db.Integer, nullable=False)
    step_description = db.Column(db.Text)
    status = db.Column(db.String(20))  # success, failed, skipped
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)
    screenshot_path = db.Column(db.Text)
    ai_confidence = db.Column(db.Float)  # AI 置信度
    ai_decision = db.Column(db.Text)     # JSON - AI 决策详情
    error_message = db.Column(db.Text)
```

### ExecutionVariable (执行变量)

用于跨步骤数据传递：

```python
class ExecutionVariable(db.Model):
    __tablename__ = "execution_variables"
    
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(50), db.ForeignKey("execution_history.execution_id"))
    variable_name = db.Column(db.String(255), nullable=False)
    variable_value = db.Column(db.Text)  # JSON
    data_type = db.Column(db.String(50))  # string, number, boolean, object, array
    source_step_index = db.Column(db.Integer)
    source_api_method = db.Column(db.String(100))  # aiQuery, aiString 等
    source_api_params = db.Column(db.Text)  # JSON
    is_encrypted = db.Column(db.Boolean, default=False)
```

### VariableReference (变量引用)

追踪变量的使用情况：

```python
class VariableReference(db.Model):
    __tablename__ = "variable_references"
    
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(50), db.ForeignKey("execution_history.execution_id"))
    step_index = db.Column(db.Integer)
    variable_name = db.Column(db.String(255))
    reference_path = db.Column(db.String(500))  # product_info.price
    original_expression = db.Column(db.String(500))  # ${product_info.price}
    resolved_value = db.Column(db.Text)
    resolution_status = db.Column(db.String(20))  # success, failed, pending
    error_message = db.Column(db.Text)
```

### Template (测试模板)

```python
class Template(db.Model):
    __tablename__ = "templates"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    steps_template = db.Column(db.Text)  # JSON
    parameters = db.Column(db.Text)       # JSON - 参数定义
    usage_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.String(100))
    is_public = db.Column(db.Boolean, default=False)
```

### RequirementsSession (需求分析会话)

```python
class RequirementsSession(db.Model):
    __tablename__ = "requirements_sessions"
    
    id = db.Column(db.String(50), primary_key=True)  # UUID
    project_name = db.Column(db.String(255))
    session_status = db.Column(db.String(50), default="active")
    current_stage = db.Column(db.String(50), default="initial")
    user_context = db.Column(db.Text)      # JSON
    ai_context = db.Column(db.Text)        # JSON
    consensus_content = db.Column(db.Text)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

**会话状态流转：**
```
active → paused → completed → archived
```

**分析阶段：**
```
initial → clarification → consensus → documentation
```

### RequirementsMessage (需求消息)

```python
class RequirementsMessage(db.Model):
    __tablename__ = "requirements_messages"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), db.ForeignKey("requirements_sessions.id"))
    message_type = db.Column(db.String(20))  # user, assistant, system
    content = db.Column(db.Text)
    message_metadata = db.Column(db.Text)  # JSON
    attached_files = db.Column(db.Text)    # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### RequirementsAIConfig (AI 配置)

```python
class RequirementsAIConfig(db.Model):
    __tablename__ = "requirements_ai_configs"
    
    id = db.Column(db.Integer, primary_key=True)
    config_name = db.Column(db.String(255), nullable=False)
    api_key = db.Column(db.Text, nullable=False)  # 加密存储
    base_url = db.Column(db.String(500), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

## 索引优化

```python
# TestCase 索引
db.Index("idx_testcase_active", "is_active")
db.Index("idx_testcase_category", "category", "is_active")
db.Index("idx_testcase_created", "created_at")
db.Index("idx_testcase_priority", "priority", "is_active")

# ExecutionHistory 索引
db.Index("idx_execution_testcase_status", "test_case_id", "status")
db.Index("idx_execution_start_time", "start_time")
db.Index("idx_execution_status", "status")

# StepExecution 索引
db.Index("idx_step_execution_id_index", "execution_id", "step_index")
db.Index("idx_step_status", "execution_id", "status")

# ExecutionVariable 索引 + 唯一约束
db.Index("idx_execution_variable", "execution_id", "variable_name")
db.UniqueConstraint("execution_id", "variable_name", name="uk_execution_variable_name")

# RequirementsMessage 索引
db.Index("idx_requirements_message_session", "session_id", "created_at")
```

## 数据迁移

使用 Alembic 管理：

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

迁移文件位置：`migrations/versions/`

