#!/usr/bin/env python3
"""
初始化超级管理员脚本

用于手动创建或重置超级管理员账户
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

# 加载环境变量
load_dotenv()

from app.core.database import SessionLocal  # noqa: E402
from app.services.user_service import UserService  # noqa: E402


def init_superadmin():
    """初始化超级管理员"""

    print("=" * 60)
    print("初始化超级管理员")
    print("=" * 60)
    print()

    # 读取配置
    superadmin_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
    superadmin_pwd = os.getenv("SUPERADMIN_PWD", "admin123456")
    external_domain = os.getenv("EXTERNAL_DOMAIN", "example.com")

    print(f"用户名: {superadmin_username}")
    print(f"密码: {'*' * len(superadmin_pwd)}")
    print(f"邮箱: {superadmin_username}@{external_domain}")
    print()

    # 确认
    confirm = input("确认创建超级管理员? (yes/no): ")
    if confirm.lower() != "yes":
        print("已取消")
        return

    print()
    print("正在创建超级管理员...")

    try:
        # 创建数据库会话
        db = SessionLocal()

        # 创建用户服务
        user_service = UserService(db)

        # 确保超级管理员存在
        user_service.ensure_super_admin_exists()

        print("✅ 超级管理员创建成功")
        print()
        print("登录信息:")
        print(f"   用户名: {superadmin_username}")
        print(f"   密码: {superadmin_pwd}")
        print()

    except Exception as e:
        print(f"❌ 创建失败: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()

    print("=" * 60)


if __name__ == "__main__":
    init_superadmin()
