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

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)



def get_local_db_path():
    """获取本地SQLite数据库路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "instance", "intent_test_framework.db")
    
    # 确保instance目录存在
    instance_dir = os.path.dirname(db_path)
    os.makedirs(instance_dir, exist_ok=True)
    
    return db_path

def init_default_ai_config():
    """初始化默认AI配置 - 直接操作SQLite数据库"""
    
    db_path = get_local_db_path()
    print(f"🗄️ 使用本地数据库: {db_path}")
    
    # 默认配置
    default_config = {
        'config_name': 'Qwen',
        'api_key': 'sk-0b7ca376cfce4e2f82986eb5fea5124d',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model_name': 'qwen-plus',
        'is_default': True,
        'is_active': True
    }
    
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
        
        # 检查是否已存在Qwen配置
        cursor.execute("""
            SELECT id, config_name, is_default FROM requirements_ai_configs 
            WHERE config_name = ?
        """, (default_config['config_name'],))
        
        existing_qwen = cursor.fetchone()
        
        if existing_qwen:
            config_id, name, is_default = existing_qwen
            print(f"✅ 发现现有 {name} 配置 (ID: {config_id})")
            
            # 更新现有配置
            cursor.execute("""
                UPDATE requirements_ai_configs 
                SET api_key = ?, base_url = ?, model_name = ?, 
                    is_default = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                default_config['api_key'],
                default_config['base_url'], 
                default_config['model_name'],
                default_config['is_default'],
                default_config['is_active'],
                config_id
            ))
            print(f"🔄 已更新 {name} 配置")
        else:
            print("🆕 创建新的 Qwen 配置...")
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
        
        # 如果设置为默认，取消其他配置的默认状态
        if default_config['is_default']:
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
