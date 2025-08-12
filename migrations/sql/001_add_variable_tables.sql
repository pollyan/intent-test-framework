-- 变量管理表迁移脚本
-- 版本: 1.0
-- 日期: 2025-01-30
-- 作者: Dev Agent (Claude)

-- 开始事务
BEGIN TRANSACTION;

-- 1. 创建execution_variables表
CREATE TABLE IF NOT EXISTS execution_variables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id VARCHAR(50) NOT NULL,
    variable_name VARCHAR(255) NOT NULL,
    variable_value TEXT,
    data_type VARCHAR(50) NOT NULL CHECK (data_type IN ('string', 'number', 'boolean', 'object', 'array')),
    source_step_index INTEGER NOT NULL CHECK (source_step_index >= 0),
    source_api_method VARCHAR(100),
    source_api_params TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_encrypted BOOLEAN DEFAULT FALSE
);

-- 2. 创建variable_references表
CREATE TABLE IF NOT EXISTS variable_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id VARCHAR(50) NOT NULL,
    step_index INTEGER NOT NULL CHECK (step_index >= 0),
    variable_name VARCHAR(255) NOT NULL,
    reference_path VARCHAR(500),
    parameter_name VARCHAR(255),
    original_expression VARCHAR(500),
    resolved_value TEXT,
    resolution_status VARCHAR(20) DEFAULT 'success' CHECK (resolution_status IN ('success', 'failed', 'pending')),
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS idx_execution_variable ON execution_variables(execution_id, variable_name);
CREATE INDEX IF NOT EXISTS idx_execution_step ON execution_variables(execution_id, source_step_index);
CREATE INDEX IF NOT EXISTS idx_variable_type ON execution_variables(execution_id, data_type);

CREATE INDEX IF NOT EXISTS idx_reference_execution_step ON variable_references(execution_id, step_index);
CREATE INDEX IF NOT EXISTS idx_reference_variable ON variable_references(execution_id, variable_name);
CREATE INDEX IF NOT EXISTS idx_reference_status ON variable_references(execution_id, resolution_status);

-- 4. 添加唯一约束（同一执行中变量名唯一）
CREATE UNIQUE INDEX IF NOT EXISTS uk_execution_variable_name ON execution_variables(execution_id, variable_name);

-- 5. 添加外键约束（仅在execution_history表存在时）
-- 注意：SQLite中外键约束需要在表创建时定义，这里提供PostgreSQL版本的约束
-- 对于SQLite，外键关系通过应用层控制

-- 提交事务
COMMIT;

-- 输出成功信息
SELECT '✓ 变量管理表迁移完成' as status;