"""
邮件服务模块

通过 SMTP 发送邮件。
"""

import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


class EmailService:
    """SMTP 邮件发送服务"""

    def __init__(self):
        """使用配置初始化邮件服务"""
        self.mail_host = settings.MAIL_HOST
        self.mail_user = settings.MAIL_USER
        self.mail_port = settings.MAIL_PORT
        self.mail_pwd = settings.MAIL_PWD
        self.mail_timeout = settings.MAIL_TIMEOUT

    def send_email(self, receiver: str, subject: str, content: str) -> None:
        """
        向指定收件人发送邮件

        Args:
            receiver: 收件人邮箱地址
            subject: 邮件主题
            content: 邮件正文（纯文本）

        Raises:
            RuntimeError: 邮件发送失败时抛出
        """
        message = MIMEText(content, "plain", "utf-8")
        message["From"] = self.mail_user
        message["To"] = receiver
        message["Subject"] = subject

        smtp: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            # 根据端口选择连接方式
            if self.mail_port == 465:
                # 端口 465: 使用 SSL
                smtp = smtplib.SMTP_SSL(self.mail_host, self.mail_port, timeout=self.mail_timeout)
            else:
                # 端口 25/587: 使用标准 SMTP（可选 STARTTLS）
                smtp = smtplib.SMTP(self.mail_host, self.mail_port, timeout=self.mail_timeout)
                # 如果是端口 587，尝试使用 STARTTLS
                if self.mail_port == 587:
                    smtp.starttls()

            # 登录
            smtp.login(self.mail_user, self.mail_pwd)

            # 发送邮件
            smtp.sendmail(self.mail_user, receiver, message.as_string())

        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f"邮件发送失败: 邮箱认证失败 - {str(e)}") from e
        except smtplib.SMTPConnectError as e:
            raise RuntimeError(
                f"邮件发送失败: 无法连接到SMTP服务器 {self.mail_host}:{self.mail_port} - {str(e)}"
            ) from e
        except smtplib.SMTPException as e:
            raise RuntimeError(f"邮件发送失败: SMTP错误 - {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"邮件发送失败: {str(e)}") from e
        finally:
            # 确保连接正确关闭
            if smtp:
                try:
                    smtp.quit()
                except Exception:
                    try:
                        smtp.close()
                    except Exception:
                        pass


# 便捷函数，保持向后兼容
def send_email(receiver: str, subject: str, content: str) -> None:
    """
    使用 EmailService 发送邮件

    提供向后兼容的便捷函数。

    Args:
        receiver: 收件人邮箱地址
        subject: 邮件主题
        content: 邮件正文（纯文本）

    Raises:
        RuntimeError: 邮件发送失败时抛出
    """
    email_service = EmailService()
    email_service.send_email(receiver, subject, content)
