#!/usr/bin/env python3
"""
创建代理包 ZIP 文件的脚本
不依赖 Node.js 或 zip 命令，只需要 Python 3
"""

import zipfile
import os
import sys
from pathlib import Path

def create_proxy_zip():
    """创建 intent-test-proxy.zip 文件"""
    
    dist_dir = Path("dist")
    source_dir = dist_dir / "intent-test-proxy"
    zip_path = dist_dir / "intent-test-proxy.zip"
    
    # 检查源目录是否存在
    if not source_dir.exists():
        print(f"❌ 错误：{source_dir} 目录不存在")
        return False
    
    # 删除旧的 ZIP 文件
    if zip_path.exists():
        zip_path.unlink()
        print(f"删除旧的 ZIP 文件: {zip_path}")
    
    # 创建 ZIP 文件
    print(f"创建 ZIP 文件: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(dist_dir)
                    zipf.write(file_path, arcname)
                    print(f"  添加: {arcname}")
        
        # 验证文件
        if zip_path.exists():
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"✅ ZIP 文件创建成功: {zip_path} ({size_mb:.2f} MB)")
            os.chmod(zip_path, 0o644)
            return True
        else:
            print("❌ ZIP 文件创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 创建 ZIP 时出错: {e}")
        return False

if __name__ == "__main__":
    success = create_proxy_zip()
    sys.exit(0 if success else 1)
