#!/usr/bin/env python3
"""
邮件配置测试脚本

用于测试邮件服务器配置是否正确
"""

import os
import sys
import smtplib
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def test_email_config():
    """测试邮件配置"""

    print("=" * 60)
    print("邮件配置测试工具")
    print("=" * 60)
    print()

    # 读取配置
    mail_host = os.getenv("MAIL_HOST", "")
    mail_user = os.getenv("MAIL_USER", "")
    mail_pwd = os.getenv("MAIL_PWD", "")
    mail_port = int(os.getenv("MAIL_PORT", "25"))
    mail_timeout = int(os.getenv("MAIL_TIMEOUT", "30"))

    print("当前配置:")
    print(f"  MAIL_HOST: {mail_host}")
    print(f"  MAIL_USER: {mail_user}")
    print(f"  MAIL_PWD: {'*' * len(mail_pwd)} (长度: {len(mail_pwd)})")
    print(f"  MAIL_PORT: {mail_port}")
    print(f"  MAIL_TIMEOUT: {mail_timeout}")
    print()

    # 验证配置
    if not mail_host or not mail_user or not mail_pwd:
        print("❌ 配置不完整，请检查 .env 文件")
        return

    # 测试连接
    print("=" * 60)
    print("测试 1: 连接到邮件服务器")
    print("=" * 60)

    smtp = None
    try:
        if mail_port == 465:
            print(f"使用 SMTP_SSL 连接到 {mail_host}:{mail_port}...")
            smtp = smtplib.SMTP_SSL(mail_host, mail_port, timeout=mail_timeout)
        else:
            print(f"使用 SMTP 连接到 {mail_host}:{mail_port}...")
            smtp = smtplib.SMTP(mail_host, mail_port, timeout=mail_timeout)

            if mail_port == 587:
                print("尝试 STARTTLS...")
                smtp.starttls()

        print("✅ 连接成功")
        print()

        # 测试登录
        print("=" * 60)
        print("测试 2: 邮箱认证")
        print("=" * 60)

        print(f"尝试登录: {mail_user}")
        smtp.login(mail_user, mail_pwd)
        print("✅ 认证成功")
        print()

        # 测试发送
        print("=" * 60)
        print("测试 3: 发送测试邮件")
        print("=" * 60)

        test_receiver = input("请输入测试收件人邮箱（留空跳过发送测试）: ").strip()

        if test_receiver:
            from email.mime.text import MIMEText

            message = MIMEText("这是一封测试邮件，用于验证邮件服务配置。", "plain", "utf-8")
            message["From"] = mail_user
            message["To"] = test_receiver
            message["Subject"] = "邮件配置测试"

            print(f"发送测试邮件到 {test_receiver}...")
            smtp.sendmail(mail_user, test_receiver, message.as_string())
            print("✅ 邮件发送成功")
            print()
        else:
            print("⏭️  跳过发送测试")
            print()

        print("=" * 60)
        print("✅ 所有测试通过！邮件配置正确")
        print("=" * 60)

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 认证失败: {e}")
        print()
        print("可能的原因:")
        print("1. 邮箱密码错误")
        print("2. 需要使用授权码而不是密码")
        print("3. 用户名格式错误（可能需要完整邮箱地址）")
        print()
        print("建议:")
        print(f"- 检查 MAIL_USER 是否需要完整邮箱地址（如 {mail_user}@{mail_host.replace('mail.', '')}）")
        print("- 检查是否需要在邮箱后台开启 SMTP 服务并生成授权码")
        print("- 确认 MAIL_PWD 是否正确")

    except smtplib.SMTPConnectError as e:
        print(f"❌ 连接失败: {e}")
        print()
        print("可能的原因:")
        print("1. 邮件服务器地址或端口错误")
        print("2. 网络连接问题")
        print("3. 防火墙阻止")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if smtp:
            try:
                smtp.quit()
            except:
                pass

    print()


if __name__ == "__main__":
    test_email_config()
