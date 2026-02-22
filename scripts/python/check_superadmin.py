#!/usr/bin/env python3
"""
超级管理员诊断脚本

用于检查超级管理员账户状态和配置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# 加载环境变量
load_dotenv()

from app.models.database import User  # noqa: E402
from app.core.security import verify_password, get_password_hash  # noqa: E402


def check_superadmin():
    """检查超级管理员账户"""

    print("=" * 60)
    print("超级管理员诊断工具")
    print("=" * 60)
    print()

    # 1. 检查环境变量
    print("1. 检查环境变量配置")
    print("-" * 60)

    superadmin_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
    superadmin_pwd = os.getenv("SUPERADMIN_PWD", "admin123456")
    external_domain = os.getenv("EXTERNAL_DOMAIN", "example.com")
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/mainnp.db")

    print(f"SUPERADMIN_USERNAME: {superadmin_username}")
    print(f"SUPERADMIN_PWD: {'*' * len(superadmin_pwd)} (长度: {len(superadmin_pwd)})")
    print(f"EXTERNAL_DOMAIN: {external_domain}")
    print(f"DATABASE_URL: {database_url}")
    print()

    # 2. 连接数据库
    print("2. 连接数据库")
    print("-" * 60)

    try:
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        print("✅ 数据库连接成功")
        print()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    # 3. 查询超级管理员
    print("3. 查询超级管理员账户")
    print("-" * 60)

    try:
        super_admin = db.query(User).filter(User.is_super_admin.is_(True)).first()

        if not super_admin:
            print("❌ 数据库中没有超级管理员账户")
            print()
            print("建议操作:")
            print("1. 重启应用，系统会自动创建超级管理员")
            print(
                "2. 或运行: python -c 'from app.services.user_service import UserService; from app.core.database import SessionLocal; db = SessionLocal(); UserService(db).ensure_super_admin_exists()'"
            )
            return

        print("✅ 找到超级管理员账户")
        print(f"   用户ID: {super_admin.id}")
        print(f"   用户名: {super_admin.username}")
        print(f"   邮箱: {super_admin.email}")
        print(f"   是否激活: {super_admin.is_active}")
        print(f"   是否超级管理员: {super_admin.is_super_admin}")
        print(f"   密码版本: {super_admin.password_version}")
        print(f"   创建时间: {super_admin.created_at}")
        print()

        # 4. 验证密码
        print("4. 验证密码")
        print("-" * 60)

        # 检查用户名是否匹配
        if super_admin.username != superadmin_username:
            print(f"⚠️  警告: 数据库中的用户名 ({super_admin.username}) 与环境变量不匹配 ({superadmin_username})")
            print()

        # 验证密码
        # bcrypt 限制密码长度为 72 字节
        pwd_to_verify = superadmin_pwd[:72]

        if verify_password(pwd_to_verify, super_admin.hashed_password):
            print("✅ 密码验证成功")
            print()
            print("登录信息:")
            print(f"   用户名: {super_admin.username}")
            print(f"   密码: {superadmin_pwd}")
            print(f"   (实际验证密码: {pwd_to_verify})")
        else:
            print("❌ 密码验证失败")
            print()
            print("可能的原因:")
            print("1. .env 中的 SUPERADMIN_PWD 与数据库中的密码不匹配")
            print("2. 数据库是旧的，密码已经改变")
            print("3. 密码被截断（bcrypt 限制 72 字节）")
            print()
            print("解决方案:")
            print("1. 删除数据库文件重新初始化:")
            print(f"   rm {database_url.replace('sqlite:///', '')}")
            print("   python -m uvicorn app.main:app")
            print()
            print("2. 或使用清档脚本:")
            print("   python scripts/python/reset_security_env.py")
            print()
            print("3. 或手动更新密码:")
            print("   python scripts/python/update_superadmin_password.py")

        # 5. 测试密码哈希
        print()
        print("5. 测试密码哈希")
        print("-" * 60)

        test_hash = get_password_hash(pwd_to_verify)
        print(f"当前密码的新哈希: {test_hash[:50]}...")
        print(f"数据库中的哈希: {super_admin.hashed_password[:50]}...")

        if test_hash == super_admin.hashed_password:
            print("⚠️  注意: 两次哈希相同（不应该发生，bcrypt 每次都不同）")
        else:
            print("✅ 哈希不同（正常，bcrypt 每次生成不同的盐）")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()

    print()
    print("=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    check_superadmin()
