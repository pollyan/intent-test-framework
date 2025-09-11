#!/usr/bin/env python3
"""
数据库迁移脚本 - 为 RequirementsMessage 表添加文件附件字段
执行: python web_gui/migrations/add_file_attachments_field.py
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from web_gui.app_enhanced import create_app
    from web_gui.models import db, RequirementsMessage
except ImportError:
    import web_gui.app_enhanced as app_module
    from web_gui.models import db, RequirementsMessage
    create_app = app_module.create_app


def add_attached_files_column():
    """为 RequirementsMessage 表添加 attached_files 字段"""
    print("🔧 开始添加文件附件字段...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 检查字段是否已存在
            inspector = db.inspect(db.engine)
            columns = inspector.get_columns('requirements_messages')
            column_names = [col['name'] for col in columns]
            
            if 'attached_files' in column_names:
                print("✅ attached_files 字段已存在，无需添加")
                return True
            
            print("📋 需要添加 attached_files 字段")
            
            # 添加字段的SQL语句
            sql_add_column = """
            ALTER TABLE requirements_messages 
            ADD COLUMN attached_files TEXT
            """
            
            # 执行SQL
            db.session.execute(db.text(sql_add_column))
            db.session.commit()
            
            # 验证字段添加成功
            inspector = db.inspect(db.engine)
            new_columns = inspector.get_columns('requirements_messages')
            new_column_names = [col['name'] for col in new_columns]
            
            if 'attached_files' in new_column_names:
                print("✅ attached_files 字段添加成功")
                
                # 显示字段信息
                attached_files_col = next(col for col in new_columns if col['name'] == 'attached_files')
                print(f"📊 字段详情: {attached_files_col}")
                
                return True
            else:
                print("❌ attached_files 字段添加失败")
                return False
            
        except Exception as e:
            print(f"❌ 添加字段失败: {str(e)}")
            db.session.rollback()
            return False


def update_model_to_dict_method():
    """更新 RequirementsMessage 模型的 to_dict 方法"""
    print("🔧 检查模型 to_dict 方法...")
    
    model_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'models.py'
    )
    
    try:
        with open(model_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查 to_dict 方法是否已包含 attached_files
        if 'attached_files' in content and '"attached_files":' in content:
            print("✅ to_dict 方法已包含 attached_files 字段")
            return True
        
        print("⚠️ 请手动更新 RequirementsMessage.to_dict() 方法")
        print("需要在 to_dict 方法中添加：")
        print('    "attached_files": json.loads(self.attached_files) if self.attached_files else None,')
        
        return False
        
    except Exception as e:
        print(f"⚠️ 检查模型文件失败: {str(e)}")
        return False


def test_new_field():
    """测试新字段功能"""
    print("🧪 测试新字段功能...")
    
    app = create_app()
    
    with app.app_context():
        try:
            import json
            import uuid
            from web_gui.models import RequirementsSession
            
            # 创建测试会话
            test_session = RequirementsSession(
                id=str(uuid.uuid4()),
                project_name="文件上传功能测试",
                session_status="active",
                current_stage="testing",
                user_context=json.dumps({}),
                ai_context=json.dumps({}),
                consensus_content=json.dumps({})
            )
            
            db.session.add(test_session)
            db.session.flush()  # 获取会话ID
            
            # 创建带文件附件的测试消息
            test_files = [
                {
                    "filename": "test.txt",
                    "content": "这是测试文件内容",
                    "size": 24,
                    "encoding": "utf-8"
                },
                {
                    "filename": "README.md", 
                    "content": "# 测试文档\n\n这是一个测试Markdown文档。",
                    "size": 45,
                    "encoding": "utf-8"
                }
            ]
            
            test_message = RequirementsMessage(
                session_id=test_session.id,
                message_type="user",
                content="测试上传文件功能",
                attached_files=json.dumps(test_files)
            )
            
            db.session.add(test_message)
            db.session.commit()
            
            # 查询并验证
            saved_message = RequirementsMessage.query.filter_by(
                session_id=test_session.id
            ).first()
            
            if saved_message and saved_message.attached_files:
                parsed_files = json.loads(saved_message.attached_files)
                print(f"✅ 测试成功！保存了 {len(parsed_files)} 个文件:")
                for file_info in parsed_files:
                    print(f"   - {file_info['filename']} ({file_info['size']} bytes)")
                
                # 清理测试数据
                db.session.delete(saved_message)
                db.session.delete(test_session)
                db.session.commit()
                
                return True
            else:
                print("❌ 测试失败：无法保存或读取文件附件")
                return False
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            db.session.rollback()
            return False


def main():
    """主函数"""
    print("=" * 50)
    print("Requirements Message 文件附件字段迁移")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    success = True
    
    try:
        # 1. 添加数据库字段
        if not add_attached_files_column():
            success = False
        
        # 2. 检查模型方法
        if not update_model_to_dict_method():
            print("⚠️ 需要手动更新模型，但这不影响数据库字段的使用")
        
        # 3. 测试新字段
        if success and not test_new_field():
            success = False
        
        if success:
            print("\n🎉 文件附件字段迁移完成!")
            print("📌 现在可以在消息中存储文件附件信息了")
            print("📋 下一步：实施 API 扩展")
        else:
            print("\n❌ 迁移过程中遇到问题")
            print("请检查错误信息并手动处理")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
