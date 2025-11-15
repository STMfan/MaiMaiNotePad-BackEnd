import smtplib
from email.mime.text import MIMEText

def send_email(receiver: str, subject: str, content: str):
    mail_host = "smtp.qq.com"
    mail_user = "1710537557@qq.com"
    mail_port = 465
    # QQ邮箱授权码
    mail_pwd = "qduqfkqjndujdeed"

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
