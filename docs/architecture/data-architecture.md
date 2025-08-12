# 🗄️ 数据架构设计

## 数据模型扩展

### 核心表结构变更
```sql
-- 1. 扩展StepExecution表支持输出数据
ALTER TABLE step_executions 
ADD COLUMN output_data TEXT COMMENT '步骤输出数据(JSON格式)',
ADD COLUMN output_variable VARCHAR(255) COMMENT '输出变量名',
ADD COLUMN output_type VARCHAR(50) COMMENT '输出数据类型',
ADD COLUMN extraction_query TEXT COMMENT '数据提取查询',
ADD COLUMN extraction_schema TEXT COMMENT '数据提取Schema',
ADD INDEX idx_output_variable (output_variable),
ADD INDEX idx_execution_variable (execution_id, output_variable);

-- 2. 新增ExecutionContext表管理变量上下文
CREATE TABLE execution_contexts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    execution_id VARCHAR(50) NOT NULL COMMENT '执行ID',
    variable_name VARCHAR(255) NOT NULL COMMENT '变量名',
    variable_value TEXT NOT NULL COMMENT '变量值(JSON格式)',
    variable_type ENUM('string', 'number', 'boolean', 'object', 'array') NOT NULL,
    source_step_index INT NOT NULL COMMENT '来源步骤索引',
    extraction_query TEXT COMMENT '数据提取查询',
    extraction_schema TEXT COMMENT '数据提取Schema',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (execution_id) REFERENCES execution_history(execution_id) ON DELETE CASCADE,
    UNIQUE KEY uk_execution_variable (execution_id, variable_name),
    INDEX idx_execution_id (execution_id),
    INDEX idx_variable_name (variable_name),
    INDEX idx_variable_type (variable_type),
    INDEX idx_source_step (source_step_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行上下文变量表';

-- 3. 新增ActionDefinitions表管理Action元数据  
CREATE TABLE action_definitions (
    id VARCHAR(100) PRIMARY KEY COMMENT 'Action ID',
    display_name VARCHAR(255) NOT NULL COMMENT '显示名称',
    icon VARCHAR(50) COMMENT '图标',
    category ENUM('navigation', 'interaction', 'assertion', 'data', 'control') NOT NULL,
    description TEXT COMMENT '描述',
    required_params JSON NOT NULL COMMENT '必需参数列表',
    optional_params JSON COMMENT '可选参数列表',
    param_templates JSON NOT NULL COMMENT '参数模板定义',
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_category (category),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Action定义表';

-- 4. 新增VariableSchemas表管理数据Schema
CREATE TABLE variable_schemas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    schema_name VARCHAR(255) NOT NULL COMMENT 'Schema名称',
    schema_definition JSON NOT NULL COMMENT 'Schema定义',
    description TEXT COMMENT '描述',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    created_by VARCHAR(100) COMMENT '创建者',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_schema_name (schema_name),
    INDEX idx_public (is_public),
    INDEX idx_usage (usage_count DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='变量Schema定义表';
```

### 数据模型类设计
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()

class ExecutionContext(Base):
    """执行上下文变量模型"""
    __tablename__ = 'execution_contexts'
    
    id = Column(Integer, primary_key=True)
    execution_id = Column(String(50), nullable=False)
    variable_name = Column(String(255), nullable=False)
    variable_value = Column(Text, nullable=False)
    variable_type = Column(Enum('string', 'number', 'boolean', 'object', 'array'), nullable=False)
    source_step_index = Column(Integer, nullable=False)
    extraction_query = Column(Text)
    extraction_schema = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'variable_name': self.variable_name,
            'variable_value': json.loads(self.variable_value),
            'variable_type': self.variable_type,
            'source_step_index': self.source_step_index,
            'extraction_query': self.extraction_query,
            'extraction_schema': self.extraction_schema,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            execution_id=data['execution_id'],
            variable_name=data['variable_name'],
            variable_value=json.dumps(data['variable_value']),
            variable_type=data['variable_type'],
            source_step_index=data['source_step_index'],
            extraction_query=data.get('extraction_query'),
            extraction_schema=data.get('extraction_schema')
        )

class ActionDefinition(Base):
    """Action定义模型"""
    __tablename__ = 'action_definitions'
    
    id = Column(String(100), primary_key=True)
    display_name = Column(String(255), nullable=False)
    icon = Column(String(50))
    category = Column(Enum('navigation', 'interaction', 'assertion', 'data', 'control'), nullable=False)
    description = Column(Text)
    required_params = Column(JSON, nullable=False)
    optional_params = Column(JSON)
    param_templates = Column(JSON, nullable=False)
    version = Column(String(20), default='1.0.0')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'display_name': self.display_name,
            'icon': self.icon,
            'category': self.category,
            'description': self.description,
            'required_params': self.required_params,
            'optional_params': self.optional_params,
            'param_templates': self.param_templates,
            'version': self.version,
            'is_active': self.is_active
        }

class VariableSchema(Base):
    """变量Schema定义模型"""
    __tablename__ = 'variable_schemas'
    
    id = Column(Integer, primary_key=True)
    schema_name = Column(String(255), nullable=False, unique=True)
    schema_definition = Column(JSON, nullable=False)
    description = Column(Text)
    usage_count = Column(Integer, default=0)
    created_by = Column(String(100))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'schema_name': self.schema_name,
            'schema_definition': self.schema_definition,
            'description': self.description,
            'usage_count': self.usage_count,
            'created_by': self.created_by,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

## 数据访问层设计

### Repository模式实现
```python
class ExecutionContextRepository:
    """执行上下文数据访问层"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_variable(self, variable_data: dict) -> ExecutionContext:
        """创建变量记录"""
        context = ExecutionContext.from_dict(variable_data)
        self.db.add(context)
        self.db.commit()
        return context
    
    def get_variable(self, execution_id: str, variable_name: str) -> Optional[ExecutionContext]:
        """获取指定变量"""
        return self.db.query(ExecutionContext).filter(
            ExecutionContext.execution_id == execution_id,
            ExecutionContext.variable_name == variable_name
        ).first()
    
    def get_all_variables(self, execution_id: str) -> List[ExecutionContext]:
        """获取执行上下文中的所有变量"""
        return self.db.query(ExecutionContext).filter(
            ExecutionContext.execution_id == execution_id
        ).order_by(ExecutionContext.source_step_index).all()
    
    def update_variable(self, execution_id: str, variable_name: str, new_value: any) -> bool:
        """更新变量值"""
        context = self.get_variable(execution_id, variable_name)
        if context:
            context.variable_value = json.dumps(new_value)
            context.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def delete_variable(self, execution_id: str, variable_name: str) -> bool:
        """删除变量"""
        deleted_count = self.db.query(ExecutionContext).filter(
            ExecutionContext.execution_id == execution_id,
            ExecutionContext.variable_name == variable_name
        ).delete()
        self.db.commit()
        return deleted_count > 0
    
    def cleanup_execution_context(self, execution_id: str) -> int:
        """清理执行上下文(执行完成后调用)"""
        deleted_count = self.db.query(ExecutionContext).filter(
            ExecutionContext.execution_id == execution_id
        ).delete()
        self.db.commit()
        return deleted_count
```

## 数据迁移策略

### 数据库迁移脚本
```python
"""
数据流功能数据库迁移脚本
Migration: add_dataflow_support
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # 1. 扩展step_executions表
    op.add_column('step_executions', 
        sa.Column('output_data', sa.Text(), nullable=True, comment='步骤输出数据'))
    op.add_column('step_executions', 
        sa.Column('output_variable', sa.String(255), nullable=True, comment='输出变量名'))
    op.add_column('step_executions', 
        sa.Column('output_type', sa.String(50), nullable=True, comment='输出数据类型'))
    op.add_column('step_executions', 
        sa.Column('extraction_query', sa.Text(), nullable=True, comment='数据提取查询'))
    op.add_column('step_executions', 
        sa.Column('extraction_schema', sa.Text(), nullable=True, comment='数据提取Schema'))
    
    # 添加索引
    op.create_index('idx_output_variable', 'step_executions', ['output_variable'])
    op.create_index('idx_execution_variable', 'step_executions', ['execution_id', 'output_variable'])
    
    # 2. 创建execution_contexts表
    op.create_table('execution_contexts',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('execution_id', sa.String(50), nullable=False),
        sa.Column('variable_name', sa.String(255), nullable=False),
        sa.Column('variable_value', sa.Text(), nullable=False),
        sa.Column('variable_type', sa.Enum('string', 'number', 'boolean', 'object', 'array'), nullable=False),
        sa.Column('source_step_index', sa.Integer(), nullable=False),
        sa.Column('extraction_query', sa.Text(), nullable=True),
        sa.Column('extraction_schema', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['execution_id'], ['execution_history.execution_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('execution_id', 'variable_name', name='uk_execution_variable'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_comment='执行上下文变量表'
    )
    
    # 创建索引
    op.create_index('idx_execution_id', 'execution_contexts', ['execution_id'])
    op.create_index('idx_variable_name', 'execution_contexts', ['variable_name'])
    op.create_index('idx_variable_type', 'execution_contexts', ['variable_type'])
    op.create_index('idx_source_step', 'execution_contexts', ['source_step_index'])

    # 3. 创建action_definitions表
    op.create_table('action_definitions',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('category', sa.Enum('navigation', 'interaction', 'assertion', 'data', 'control'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required_params', sa.JSON(), nullable=False),
        sa.Column('optional_params', sa.JSON(), nullable=True),
        sa.Column('param_templates', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(20), server_default='1.0.0'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_comment='Action定义表'
    )
    
    op.create_index('idx_category', 'action_definitions', ['category'])
    op.create_index('idx_active', 'action_definitions', ['is_active'])

    # 4. 插入默认Action定义数据
    insert_default_action_definitions()

def downgrade():
    # 删除新增的表
    op.drop_table('execution_contexts')
    op.drop_table('action_definitions')
    
    # 删除step_executions表的新增列
    op.drop_index('idx_execution_variable', 'step_executions')
    op.drop_index('idx_output_variable', 'step_executions')
    op.drop_column('step_executions', 'extraction_schema')
    op.drop_column('step_executions', 'extraction_query')
    op.drop_column('step_executions', 'output_type')
    op.drop_column('step_executions', 'output_variable')
    op.drop_column('step_executions', 'output_data')

def insert_default_action_definitions():
    """插入默认的Action定义数据"""
    from sqlalchemy import text
    
    default_actions = [
        {
            'id': 'ai_extract_string',
            'display_name': '提取字符串',
            'icon': '📝',
            'category': 'data',
            'description': '从页面中提取字符串数据',
            'required_params': ['query', 'output_variable'],
            'optional_params': ['timeout'],
            'param_templates': {
                'query': {
                    'type': 'string',
                    'placeholder': '描述要提取的字符串数据',
                    'support_variables': False,
                    'validation': ['required']
                },
                'output_variable': {
                    'type': 'variable_name',
                    'placeholder': '变量名（如：product_name）',
                    'pattern': '^[a-zA-Z_][a-zA-Z0-9_]*$',
                    'validation': ['required', 'variable_name']
                },
                'timeout': {
                    'type': 'number',
                    'default': 10000,
                    'min': 1000,
                    'max': 60000,
                    'unit': '毫秒'
                }
            }
        },
        # ... 更多默认Action定义
    ]
    
    # 执行插入操作
    # ... 实现数据插入逻辑
```

---
