#!/usr/bin/env python3
"""
测试用户凭据验证的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from user_management import get_user_by_credentials

def test_user_credentials():
    """测试用户凭据验证"""
    try:
        # 测试正确的用户名和密码
        username = "STMfan"
        password = "@Stickmanfans0805INMMNP"
        
        print(f"测试用户名: {username}")
        print(f"测试密码: {password}")
        
        user = get_user_by_credentials(username, password)
        
        if user:
            print(f"验证成功!")
            print(f"用户ID: {user.userID}")
            print(f"用户名: {user.username}")
            print(f"邮箱: {user.email}")
            print(f"角色: {user.role}")
        else:
            print("验证失败!")
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_credentials()