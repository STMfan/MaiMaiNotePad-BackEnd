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

    message = MIMEText(content, "plain", "utf-8")
    message["From"] = mail_user
    message["To"] = receiver
    message["Subject"] = subject

    try:
        smtp = smtplib.SMTP_SSL(mail_host, mail_port)
        smtp.login(mail_user, mail_pwd)
        smtp.sendmail(mail_user, receiver, message.as_string())
        smtp.quit()
    except Exception as e:
        raise RuntimeError(f"邮件发送失败: {str(e)}")
