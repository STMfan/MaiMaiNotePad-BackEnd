#!/usr/bin/env python3
"""
检查用户密码哈希值的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_models import sqlite_db_manager

def check_user_password():
    """检查用户密码哈希值"""
    try:
        # 获取所有用户
        users = sqlite_db_manager.get_all_users()
        
        print(f"数据库中共有 {len(users)} 个用户")
        
        for user in users:
            print(f"\n用户名: {user.username}")
            print(f"用户ID: {user.id}")
            print(f"邮箱: {user.email}")
            print(f"角色: {'管理员' if user.is_admin else '普通用户'}")
            print(f"密码哈希: {user.hashed_password}")
            
            # 尝试验证不同的密码
            test_passwords = ["admin", "admin123", "@Stickmanfans0805INMMNP"]
            
            for pwd in test_passwords:
                is_valid = user.verify_password(pwd)
                print(f"密码 '{pwd}' 验证结果: {'✓ 正确' if is_valid else '✗ 错误'}")
                
                if is_valid:
                    print(f"找到正确密码: {pwd}")
                    break
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_user_password()