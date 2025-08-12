"""Add variable management tables

Revision ID: 001_add_variable_tables
Revises: 
Create Date: 2025-01-30 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '001_add_variable_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """添加变量管理相关表"""
    
    # 检查表是否已存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'execution_variables' not in existing_tables:
        # 创建execution_variables表
        op.create_table(
            'execution_variables',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('execution_id', sa.String(50), nullable=False),
            sa.Column('variable_name', sa.String(255), nullable=False),
            sa.Column('variable_value', sa.Text()),
            sa.Column('data_type', sa.String(50), nullable=False),
            sa.Column('source_step_index', sa.Integer(), nullable=False),
            sa.Column('source_api_method', sa.String(100)),
            sa.Column('source_api_params', sa.Text()),
            sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
            sa.Column('is_encrypted', sa.Boolean(), default=False),
            sa.PrimaryKeyConstraint('id')
        )
        print("✓ 创建execution_variables表成功")
    else:
        print("ⓘ execution_variables表已存在，跳过创建")
    
    if 'variable_references' not in existing_tables:
        # 创建variable_references表
        op.create_table(
            'variable_references',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('execution_id', sa.String(50), nullable=False),
            sa.Column('step_index', sa.Integer(), nullable=False),
            sa.Column('variable_name', sa.String(255), nullable=False),
            sa.Column('reference_path', sa.String(500)),
            sa.Column('parameter_name', sa.String(255)),
            sa.Column('original_expression', sa.String(500)),
            sa.Column('resolved_value', sa.Text()),
            sa.Column('resolution_status', sa.String(20), default='success'),
            sa.Column('error_message', sa.Text()),
            sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
            sa.PrimaryKeyConstraint('id')
        )
        print("✓ 创建variable_references表成功")
    else:
        print("ⓘ variable_references表已存在，跳过创建")
    
    # 创建索引
    _create_indexes_safe()
    
    # 添加外键约束
    _add_foreign_keys_safe()
    
    print("✓ 数据库迁移完成")

def downgrade():
    """回滚迁移"""
    # 检查表中是否有数据
    conn = op.get_bind()
    
    try:
        # 检查execution_variables表数据
        result = conn.execute(sa.text("SELECT COUNT(*) FROM execution_variables"))
        var_count = result.scalar()
        
        if var_count > 0:
            print(f"⚠️  警告: execution_variables表中有 {var_count} 条数据")
            response = input("确定要删除这些数据吗? (yes/no): ")
            if response.lower() != 'yes':
                print("取消回滚操作")
                return
        
        # 检查variable_references表数据
        result = conn.execute(sa.text("SELECT COUNT(*) FROM variable_references"))
        ref_count = result.scalar()
        
        if ref_count > 0:
            print(f"⚠️  警告: variable_references表中有 {ref_count} 条数据")
            response = input("确定要删除这些数据吗? (yes/no): ")
            if response.lower() != 'yes':
                print("取消回滚操作")
                return
        
    except Exception as e:
        print(f"检查数据时出错: {e}")
    
    # 删除外键约束
    try:
        op.drop_constraint('fk_execution_variables_execution_id', 'execution_variables', type_='foreignkey')
        op.drop_constraint('fk_variable_references_execution_id', 'variable_references', type_='foreignkey')
        op.drop_constraint('uk_execution_variable_name', 'execution_variables', type_='unique')
        print("✓ 删除约束成功")
    except Exception as e:
        print(f"删除约束时出错: {e}")
    
    # 删除表
    op.drop_table('variable_references')
    op.drop_table('execution_variables')
    print("✓ 回滚完成")

def _create_indexes_safe():
    """安全创建索引"""
    indexes = [
        ('idx_execution_variable', 'execution_variables', ['execution_id', 'variable_name']),
        ('idx_execution_step', 'execution_variables', ['execution_id', 'source_step_index']),
        ('idx_variable_type', 'execution_variables', ['execution_id', 'data_type']),
        ('idx_reference_execution_step', 'variable_references', ['execution_id', 'step_index']),
        ('idx_reference_variable', 'variable_references', ['execution_id', 'variable_name']),
        ('idx_reference_status', 'variable_references', ['execution_id', 'resolution_status']),
    ]
    
    for index_name, table_name, columns in indexes:
        try:
            op.create_index(index_name, table_name, columns)
            print(f"✓ 创建索引 {index_name} 成功")
        except Exception as e:
            print(f"创建索引 {index_name} 失败: {e}")

def _add_foreign_keys_safe():
    """安全添加外键约束"""
    try:
        # 检查execution_history表是否存在
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_tables = inspector.get_table_names()
        
        if 'execution_history' not in existing_tables:
            print("⚠️  警告: execution_history表不存在，跳过外键约束创建")
            return
        
        # 添加外键约束
        op.create_foreign_key(
            'fk_execution_variables_execution_id',
            'execution_variables', 'execution_history',
            ['execution_id'], ['execution_id'],
            ondelete='CASCADE'
        )
        
        op.create_foreign_key(
            'fk_variable_references_execution_id',
            'variable_references', 'execution_history',
            ['execution_id'], ['execution_id'],
            ondelete='CASCADE'
        )
        
        # 添加唯一约束
        op.create_unique_constraint(
            'uk_execution_variable_name',
            'execution_variables',
            ['execution_id', 'variable_name']
        )
        
        print("✓ 外键约束创建成功")
        
    except Exception as e:
        print(f"创建外键约束失败: {e}")