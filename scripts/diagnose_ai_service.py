#!/usr/bin/env python3
"""
AI服务诊断脚本
用于检查AI服务配置和连接状态
"""

import os
import sys
import requests
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_environment():
    """检查环境变量配置"""
    print("🔍 检查环境变量配置...")
    
    env_vars = [
        ("OPENAI_API_KEY", "API密钥"),
        ("OPENAI_BASE_URL", "API基础URL"),
        ("MIDSCENE_MODEL_NAME", "模型名称")
    ]
    
    missing_vars = []
    for var_name, description in env_vars:
        value = os.getenv(var_name)
        if value:
            # 隐藏API密钥的部分内容
            if "api_key" in var_name.lower():
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"✅ {description}: {display_value}")
        else:
            print(f"❌ {description}: 未设置")
            missing_vars.append(var_name)
    
    return len(missing_vars) == 0

def check_database_config():
    """检查数据库中的AI配置"""
    print("\n🔍 检查数据库中的AI配置...")
    
    try:
        from web_gui.models import RequirementsAIConfig
        from web_gui.app_enhanced import create_app
        
        app = create_app()
        with app.app_context():
            configs = RequirementsAIConfig.query.all()
            
            if not configs:
                print("❌ 数据库中没有AI配置")
                return False
            
            print(f"✅ 找到 {len(configs)} 个AI配置:")
            for config in configs:
                status = "✅ 默认" if config.is_default else "⚪ 非默认"
                print(f"  {status} {config.config_name} ({config.model_name})")
            
            # 检查默认配置
            default_config = RequirementsAIConfig.get_default_config()
            if default_config:
                print(f"✅ 默认配置: {default_config.config_name}")
                config_data = default_config.get_config_for_ai_service()
                
                # 验证配置完整性
                required_fields = ['api_key', 'base_url', 'model_name']
                missing_fields = [field for field in required_fields if not config_data.get(field)]
                
                if missing_fields:
                    print(f"❌ 默认配置缺少字段: {missing_fields}")
                    return False
                else:
                    print("✅ 默认配置字段完整")
                    return True
            else:
                print("❌ 没有设置默认配置")
                return False
                
    except ImportError as e:
        print(f"❌ 无法导入模型: {e}")
        return False
    except Exception as e:
        print(f"❌ 检查数据库配置失败: {e}")
        return False

def test_ai_api_connection():
    """测试AI API连接"""
    print("\n🔍 测试AI API连接...")
    
    try:
        from web_gui.models import RequirementsAIConfig
        from web_gui.app_enhanced import create_app
        
        app = create_app()
        with app.app_context():
            default_config = RequirementsAIConfig.get_default_config()
            if not default_config:
                print("❌ 没有默认AI配置，无法测试连接")
                return False
            
            config_data = default_config.get_config_for_ai_service()
            
            # 构建测试请求
            headers = {
                "Authorization": f"Bearer {config_data['api_key']}",
                "Content-Type": "application/json"
            }
            
            test_data = {
                "model": config_data['model_name'],
                "messages": [
                    {"role": "user", "content": "Hello, this is a connection test."}
                ],
                "max_tokens": 10
            }
            
            base_url = config_data['base_url'].rstrip('/')
            api_url = f"{base_url}/chat/completions"
            
            print(f"📡 测试连接: {api_url}")
            print(f"🤖 使用模型: {config_data['model_name']}")
            
            response = requests.post(
                api_url,
                headers=headers,
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ AI API连接成功")
                result = response.json()
                if 'choices' in result and result['choices']:
                    print("✅ AI响应格式正确")
                    return True
                else:
                    print("⚠️ AI响应格式异常，可能影响正常功能")
                    print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    return False
            else:
                print(f"❌ AI API连接失败: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
                except:
                    print(f"错误详情: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 测试连接失败: {e}")
        return False

def check_bundle_files():
    """检查助手bundle文件"""
    print("\n🔍 检查助手bundle文件...")
    
    try:
        from web_gui.services.requirements_ai_service import IntelligentAssistantService
        
        bundle_dir = project_root / "intelligent-requirements-analyzer" / "dist"
        
        if not bundle_dir.exists():
            print(f"❌ Bundle目录不存在: {bundle_dir}")
            return False
        
        all_exists = True
        for assistant_id, info in IntelligentAssistantService.SUPPORTED_ASSISTANTS.items():
            bundle_file = info["bundle_file"]
            bundle_path = bundle_dir / bundle_file
            
            if bundle_path.exists():
                file_size = bundle_path.stat().st_size
                print(f"✅ {info['title']} {info['name']}: {bundle_file} ({file_size:,} bytes)")
            else:
                print(f"❌ {info['title']} {info['name']}: {bundle_file} 不存在")
                all_exists = False
        
        return all_exists
        
    except Exception as e:
        print(f"❌ 检查bundle文件失败: {e}")
        return False

def main():
    """主诊断函数"""
    print("🔧 AI服务诊断工具")
    print("=" * 50)
    
    results = []
    
    # 检查环境变量
    results.append(("环境变量", check_environment()))
    
    # 检查数据库配置
    results.append(("数据库配置", check_database_config()))
    
    # 检查bundle文件
    results.append(("Bundle文件", check_bundle_files()))
    
    # 测试API连接
    results.append(("API连接", test_ai_api_connection()))
    
    # 总结
    print("\n📊 诊断结果总结:")
    print("=" * 50)
    
    all_passed = True
    for check_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 所有检查都通过了！AI服务应该可以正常工作。")
    else:
        print("⚠️ 发现问题，请根据上述检查结果进行修复。")
        print("\n💡 常见解决方案:")
        print("1. 配置环境变量或在配置管理页面设置AI配置")
        print("2. 确保API密钥有效且有足够的额度")
        print("3. 检查网络连接和防火墙设置")
        print("4. 确认API基础URL正确")
        print("5. 检查bundle文件是否完整")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
