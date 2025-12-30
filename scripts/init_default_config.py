#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
默认AI配置初始化脚本
在本地开发环境启动时自动创建和更新默认AI配置
直接操作本地SQLite数据库，确保与Flask应用使用相同数据源
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载环境变量（如果存在.env文件）
try:
    from dotenv import load_dotenv
    env_path = Path(project_root) / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📝 已加载环境变量: {env_path}")
except ImportError:
    print("⚠️ python-dotenv未安装，跳过.env文件加载")



def get_local_db_path():
    """获取本地SQLite数据库路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "instance", "intent_test_framework.db")
    
    # 确保instance目录存在
    instance_dir = os.path.dirname(db_path)
    os.makedirs(instance_dir, exist_ok=True)
    
    return db_path

def get_default_config():
    """从环境变量获取默认配置，避免硬编码"""
    config = {
        'config_name': os.getenv('DEFAULT_AI_CONFIG_NAME', 'Qwen'),
        'api_key': os.getenv('OPENAI_API_KEY', ''),
        'base_url': os.getenv('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
        'model_name': os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest'),
        'is_default': True,
        'is_active': True
    }
    
    # 验证必需的配置
    if not config['api_key']:
        print("⚠️ 未设置OPENAI_API_KEY环境变量")
        return None
        
    return config

def check_existing_config(cursor):
    """检查现有配置，如果已有配置则不覆盖"""
    cursor.execute("""
        SELECT id, config_name, model_name, is_default, is_active 
        FROM requirements_ai_configs 
        WHERE is_default = TRUE AND is_active = TRUE
    """)
    
    existing_config = cursor.fetchone()
    if existing_config:
        config_id, name, model, is_default, is_active = existing_config
        print(f"✅ 发现现有默认配置: {name} ({model}) - ID: {config_id}")
        print(f"🔒 保持现有配置不变，跳过初始化")
        return True
    return False

def init_default_ai_config():
    """初始化默认AI配置 - 优先使用现有配置，避免覆盖用户自定义设置"""
    
    db_path = get_local_db_path()
    print(f"🗄️ 使用本地数据库: {db_path}")
    
    # 从环境变量获取默认配置
    default_config = get_default_config()
    if not default_config:
        print("❌ 无法获取默认配置（缺少必需的环境变量）")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='requirements_ai_configs'
        """)
        
        if not cursor.fetchone():
            print("⚠️ requirements_ai_configs 表不存在，将创建表...")
            
            # 创建表
            cursor.execute("""
                CREATE TABLE requirements_ai_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_name VARCHAR(255) NOT NULL,
                    api_key TEXT NOT NULL,
                    base_url VARCHAR(500) NOT NULL,
                    model_name VARCHAR(100) NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ requirements_ai_configs 表创建成功")
        
        # 检查是否已有默认激活的配置
        if check_existing_config(cursor):
            conn.close()
            print("✅ AI配置检查完成")
            return True
        
        print("🆕 未发现默认配置，开始创建...")
        
        # 检查是否已存在相同名称的配置
        cursor.execute("""
            SELECT id, config_name, is_default FROM requirements_ai_configs 
            WHERE config_name = ?
        """, (default_config['config_name'],))
        
        existing_config = cursor.fetchone()
        
        if existing_config:
            config_id, name, is_default = existing_config
            print(f"✅ 发现现有 {name} 配置 (ID: {config_id})")
            
            # 仅在没有默认配置时才更新
            if not is_default:
                cursor.execute("""
                    UPDATE requirements_ai_configs 
                    SET is_default = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    default_config['is_default'],
                    default_config['is_active'],
                    config_id
                ))
                print(f"🔄 已将 {name} 设置为默认配置")
            else:
                print(f"📌 {name} 已经是默认配置")
        else:
            print(f"🆕 创建新的 {default_config['config_name']} 配置...")
            # 插入新配置
            cursor.execute("""
                INSERT INTO requirements_ai_configs 
                (config_name, api_key, base_url, model_name, is_default, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                default_config['config_name'],
                default_config['api_key'],
                default_config['base_url'],
                default_config['model_name'],
                default_config['is_default'],
                default_config['is_active']
            ))
            print(f"✅ 已创建 {default_config['config_name']} 配置")
            
            # 取消其他配置的默认状态
            cursor.execute("""
                UPDATE requirements_ai_configs 
                SET is_default = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE config_name != ?
            """, (default_config['config_name'],))
        
        # 提交更改
        conn.commit()
        
        # 验证配置
        cursor.execute("""
            SELECT config_name, model_name, is_default, is_active 
            FROM requirements_ai_configs 
            WHERE is_default = TRUE
        """)
        
        default_cfg = cursor.fetchone()
        if default_cfg:
            name, model, is_default, is_active = default_cfg
            print(f"🎯 默认配置已设置: {name} ({model}) - 默认: {bool(is_default)}, 激活: {bool(is_active)}")
        else:
            print("⚠️ 未找到默认配置")
        
        conn.close()
        print("✅ AI配置初始化完成")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ 数据库操作失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 初始化默认AI配置...")
    success = init_default_ai_config()
    if success:
        print("🎉 默认AI配置初始化成功！")
        sys.exit(0)
    else:
        print("💥 默认AI配置初始化失败！")
        sys.exit(1)
