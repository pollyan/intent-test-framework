-- 变量管理表回滚脚本
-- 版本: 1.0
-- 日期: 2025-01-30
-- 作用: 安全删除变量管理相关表和索引

-- 开始事务
BEGIN TRANSACTION;

-- 1. 检查数据存在情况（仅显示信息）
SELECT 
    '⚠️ 准备删除execution_variables表，当前记录数: ' || COUNT(*) as warning_variables
FROM execution_variables;

SELECT 
    '⚠️ 准备删除variable_references表，当前记录数: ' || COUNT(*) as warning_references  
FROM variable_references;

-- 2. 删除索引（如果存在）
DROP INDEX IF EXISTS idx_execution_variable;
DROP INDEX IF EXISTS idx_execution_step;
DROP INDEX IF EXISTS idx_variable_type;
DROP INDEX IF EXISTS idx_reference_execution_step;
DROP INDEX IF EXISTS idx_reference_variable;
DROP INDEX IF EXISTS idx_reference_status;
DROP INDEX IF EXISTS uk_execution_variable_name;

-- 3. 删除表
DROP TABLE IF EXISTS variable_references;
DROP TABLE IF EXISTS execution_variables;

-- 提交事务
COMMIT;

-- 输出完成信息
SELECT '✓ 变量管理表回滚完成' as status;