#!/usr/bin/env python3
"""
测试清档脚本的各个功能（不实际执行清档）
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("测试清档脚本功能")
print("=" * 60)
print()

# 测试导入
print("1. 测试模块导入...")
try:
    from dotenv import load_dotenv
    print("   ✅ dotenv")
    
    from app.core.database import SessionLocal
    print("   ✅ SessionLocal")
    
    from app.services.user_service import UserService
    print("   ✅ UserService")
    
    from app.models.database import User
    print("   ✅ User")
    
    from app.core.security import verify_password
    print("   ✅ verify_password")
    
    print("   所有模块导入成功")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

print()
print("2. 测试环境变量读取...")
load_dotenv()

import os
superadmin_username = os.getenv('SUPERADMIN_USERNAME', 'superadmin')
superadmin_pwd = os.getenv('SUPERADMIN_PWD', 'admin123456')
database_url = os.getenv('DATABASE_URL', 'sqlite:///data/mainnp.db')

print(f"   SUPERADMIN_USERNAME: {superadmin_username}")
print(f"   SUPERADMIN_PWD: {'*' * len(superadmin_pwd)} (长度: {len(superadmin_pwd)})")
print(f"   DATABASE_URL: {database_url}")

print()
print("3. 测试数据库连接...")
try:
    db = SessionLocal()
    print("   ✅ 数据库连接成功")
    db.close()
except Exception as e:
    print(f"   ❌ 数据库连接失败: {e}")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
