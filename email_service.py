import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def send_email(receiver: str, subject: str, content: str):
    mail_host = os.getenv("MAIL_HOST", "smtp.qq.com")
    mail_user = os.getenv("MAIL_USER", "1710537557@qq.com")
    mail_port = int(os.getenv("MAIL_PORT", "465"))
    mail_pwd = os.getenv("MAIL_PWD", "qduqfkqjndujdeed")
    mail_timeout = int(os.getenv("MAIL_TIMEOUT", "30"))  # 默认30秒超时

    message = MIMEText(content, "plain", "utf-8")
    message["From"] = mail_user
    message["To"] = receiver
    message["Subject"] = subject

    smtp = None
    try:
        # 创建SMTP连接，设置超时
        smtp = smtplib.SMTP_SSL(mail_host, mail_port, timeout=mail_timeout)
        # 启用调试模式（可选，生产环境可以关闭）
        # smtp.set_debuglevel(1)
        
        # 登录
        smtp.login(mail_user, mail_pwd)
        
        # 发送邮件
        smtp.sendmail(mail_user, receiver, message.as_string())
        
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError(f"邮件发送失败: 邮箱认证失败 - {str(e)}")
    except smtplib.SMTPConnectError as e:
        raise RuntimeError(f"邮件发送失败: 无法连接到SMTP服务器 {mail_host}:{mail_port} - {str(e)}")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"邮件发送失败: SMTP错误 - {str(e)}")
    except Exception as e:
        raise RuntimeError(f"邮件发送失败: {str(e)}")
    finally:
        # 确保连接正确关闭
        if smtp:
            try:
                smtp.quit()
            except:
                try:
                    smtp.close()
                except:
                    pass
