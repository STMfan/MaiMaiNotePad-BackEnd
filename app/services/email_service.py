"""
Email service for sending emails via SMTP
"""

import smtplib
from email.mime.text import MIMEText
from app.core.config import settings


class EmailService:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        """Initialize email service with configuration from settings"""
        self.mail_host = settings.MAIL_HOST
        self.mail_user = settings.MAIL_USER
        self.mail_port = settings.MAIL_PORT
        self.mail_pwd = settings.MAIL_PWD
        self.mail_timeout = settings.MAIL_TIMEOUT
    
    def send_email(self, receiver: str, subject: str, content: str) -> None:
        """
        Send an email to the specified receiver
        
        Args:
            receiver: Email address of the recipient
            subject: Subject line of the email
            content: Plain text content of the email
            
        Raises:
            RuntimeError: If email sending fails for any reason
        """
        message = MIMEText(content, "plain", "utf-8")
        message["From"] = self.mail_user
        message["To"] = receiver
        message["Subject"] = subject

        smtp = None
        try:
            # 创建SMTP连接，设置超时
            smtp = smtplib.SMTP_SSL(self.mail_host, self.mail_port, timeout=self.mail_timeout)
            # 启用调试模式（可选，生产环境可以关闭）
            # smtp.set_debuglevel(1)

            # 登录
            smtp.login(self.mail_user, self.mail_pwd)

            # 发送邮件
            smtp.sendmail(self.mail_user, receiver, message.as_string())

        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f"邮件发送失败: 邮箱认证失败 - {str(e)}")
        except smtplib.SMTPConnectError as e:
            raise RuntimeError(
                f"邮件发送失败: 无法连接到SMTP服务器 {self.mail_host}:{self.mail_port} - {str(e)}")
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


# Convenience function for backward compatibility
def send_email(receiver: str, subject: str, content: str) -> None:
    """
    Send an email using the EmailService
    
    This function provides backward compatibility with the old email_service module.
    
    Args:
        receiver: Email address of the recipient
        subject: Subject line of the email
        content: Plain text content of the email
        
    Raises:
        RuntimeError: If email sending fails for any reason
    """
    email_service = EmailService()
    email_service.send_email(receiver, subject, content)
