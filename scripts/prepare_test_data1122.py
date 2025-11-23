#!/usr/bin/env python3
"""
准备API测试数据脚本

此脚本用于准备API烟测所需的测试数据：
1. 发送注册验证码并获取验证码
2. 发送重置密码验证码并获取验证码（需要已注册用户）
3. 创建待审核的人设卡

使用方法:
    python scripts/prepare_test_data.py \\
        --base-url http://localhost:9278 \\
        --username existing-user \\
        --password existing-pass \\
        --email test@example.com \\
        --registration-email newuser@example.com
"""

import argparse
import os
import sys
import textwrap
import time
import uuid
from typing import Optional

import requests

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database_models import sqlite_db_manager, EmailVerification
from datetime import datetime


def get_latest_verification_code(email: str) -> Optional[str]:
    """从数据库获取指定邮箱的最新验证码（未使用且未过期）"""
    try:
        session = sqlite_db_manager.get_session()
        try:
            record = session.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.is_used == False,
                EmailVerification.expires_at > datetime.now()
            ).order_by(EmailVerification.created_at.desc()).first()
            
            if record:
                return record.code
            return None
        finally:
            session.close()
    except Exception as e:
        print(f"获取验证码失败: {str(e)}")
        return None


def send_verification_code(base_url: str, email: str) -> bool:
    """发送注册验证码"""
    try:
        url = f"{base_url}/api/send_verification_code"
        response = requests.post(url, data={"email": email}, timeout=10)
        if response.ok:
            print(f"✓ 已发送注册验证码到 {email}")
            return True
        else:
            print(f"✗ 发送注册验证码失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ 发送注册验证码异常: {str(e)}")
        return False


def send_reset_password_code(base_url: str, email: str) -> bool:
    """发送重置密码验证码"""
    try:
        url = f"{base_url}/api/send_reset_password_code"
        response = requests.post(url, data={"email": email}, timeout=10)
        if response.ok:
            print(f"✓ 已发送重置密码验证码到 {email}")
            return True
        else:
            print(f"✗ 发送重置密码验证码失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ 发送重置密码验证码异常: {str(e)}")
        return False


def login(base_url: str, username: str, password: str) -> Optional[str]:
    """登录并获取token"""
    try:
        url = f"{base_url}/api/token"
        response = requests.post(
            url,
            json={"username": username, "password": password},
            timeout=10
        )
        if response.ok:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"✗ 登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ 登录异常: {str(e)}")
        return None


def create_pending_persona(base_url: str, token: str) -> Optional[str]:
    """创建待审核的人设卡"""
    try:
        url = f"{base_url}/api/persona/upload"
        name = f"test-persona-{int(time.time())}"
        description = "测试用待审核人设卡"
        toml_content = textwrap.dedent(
            f"""
            [profile]
            name = "{name}"
            description = "{description}"
            """
        ).strip()
        
        files = {
            "files": (f"{name}.toml", toml_content, "application/toml")
        }
        data = {
            "name": name,
            "description": description,
            "copyright_owner": "test-owner",
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            url,
            headers=headers,
            data=data,
            files=files,
            timeout=30
        )
        
        if response.ok:
            result = response.json()
            persona_id = result.get("id")
            print(f"✓ 已创建待审核人设卡: {name} (ID: {persona_id})")
            return persona_id
        else:
            print(f"✗ 创建人设卡失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ 创建人设卡异常: {str(e)}")
        return None


def main():
    parser = argparse.ArgumentParser(description="准备API测试数据")
    parser.add_argument("--base-url", default=os.getenv("MAIMNP_BASE_URL", "http://0.0.0.0:9278"))
    parser.add_argument("--username", default=os.getenv("MAIMNP_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MAIMNP_PASSWORD"))
    parser.add_argument("--email", default=os.getenv("MAIMNP_EMAIL"), 
                       help="用于重置密码的已注册用户邮箱")
    parser.add_argument("--registration-email", 
                       help="用于注册的新用户邮箱（如果未提供，将使用 --email）")
    
    args = parser.parse_args()
    
    base_url = args.base_url.rstrip("/")
    registration_email = args.registration_email or args.email
    
    # 保存验证码
    reg_code = None
    reset_code = None
    persona_id = None
    
    print("=" * 60)
    print("准备API测试数据")
    print("=" * 60)
    print()
    
    # 1. 发送注册验证码
    if registration_email:
        print(f"[1/4] 发送注册验证码到 {registration_email}...")
        if send_verification_code(base_url, registration_email):
            time.sleep(1)  # 等待数据库写入
            reg_code = get_latest_verification_code(registration_email)
            if reg_code:
                print(f"    → 注册验证码: {reg_code}")
                print(f"    → 使用参数: --registration-code {reg_code}")
            else:
                print(f"    ⚠ 无法从数据库获取验证码")
        print()
    else:
        print("[1/4] 跳过注册验证码（未提供邮箱）")
        print()
    
    # 2. 发送重置密码验证码（需要已注册用户）
    if args.email and args.username and args.password:
        print(f"[2/4] 发送重置密码验证码到 {args.email}...")
        if send_reset_password_code(base_url, args.email):
            time.sleep(1)  # 等待数据库写入
            reset_code = get_latest_verification_code(args.email)
            if reset_code:
                print(f"    → 重置密码验证码: {reset_code}")
                print(f"    → 使用参数: --reset-code {reset_code}")
            else:
                print(f"    ⚠ 无法从数据库获取验证码")
        print()
    else:
        print("[2/4] 跳过重置密码验证码（需要 --email, --username, --password）")
        print()
    
    # 3. 创建待审核的人设卡
    if args.username and args.password:
        print(f"[3/4] 登录并创建待审核人设卡...")
        token = login(base_url, args.username, args.password)
        if token:
            persona_id = create_pending_persona(base_url, token)
            if persona_id:
                print(f"    → 人设卡ID: {persona_id}")
            else:
                print(f"    ⚠ 创建人设卡失败")
        else:
            print(f"    ⚠ 登录失败，无法创建人设卡")
        print()
    else:
        print("[3/4] 跳过创建人设卡（需要 --username, --password）")
        print()
    
    # 4. 生成测试命令
    print("[4/4] 生成测试命令...")
    print()
    print("=" * 60)
    print("测试命令示例:")
    print("=" * 60)
    print()
    
    cmd_parts = [
        "python scripts/api_smoke_test.py",
        f"--base-url {base_url}",
    ]
    
    if args.username:
        cmd_parts.append(f"--username {args.username}")
    if args.password:
        cmd_parts.append(f"--password {args.password}")
    if args.email:
        cmd_parts.append(f"--email {args.email}")
    
    # 注册相关参数
    if registration_email and reg_code:
        cmd_parts.extend([
            "--run-registration",
            f"--registration-username testuser{int(time.time())}",
            "--registration-password testpass123",
            f"--registration-email {registration_email}",
            f"--registration-code {reg_code}",
        ])
    
    # 重置密码相关参数
    if args.email and reset_code:
        cmd_parts.extend([
            "--run-password-reset",
            f"--reset-code {reset_code}",
            "--new-password newpass123",
        ])
    
    cmd_parts.append("--verbose")
    
    print(" ".join(cmd_parts))
    print()
    print("=" * 60)
    print("完成！")
    print("=" * 60)
    
    # 显示总结
    print()
    print("准备的数据:")
    if reg_code:
        print(f"  ✓ 注册验证码: {reg_code} (邮箱: {registration_email})")
    if reset_code:
        print(f"  ✓ 重置密码验证码: {reset_code} (邮箱: {args.email})")
    if persona_id:
        print(f"  ✓ 待审核人设卡ID: {persona_id}")
    print()


if __name__ == "__main__":
    main()

