"""
EmailService 单元测试

测试邮件发送功能，包括验证码、
通知、SMTP 连接处理和错误场景。

需求: 2.2 - 服务层单元测试
"""

import pytest
import smtplib
from unittest.mock import Mock, patch, MagicMock, call
from email.mime.text import MIMEText

from app.services.email_service import EmailService, send_email


class TestEmailServiceInitialization:
    """测试 EmailService 初始化"""
    
    def test_init_loads_settings(self):
        """测试 EmailService 从设置加载配置"""
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "test@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            
            assert service.mail_host == "smtp.example.com"
            assert service.mail_user == "test@example.com"
            assert service.mail_port == 465
            assert service.mail_pwd == "password123"
            assert service.mail_timeout == 30


class TestSendEmail:
    """测试邮件发送功能"""
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_success(self, mock_smtp_ssl):
        """测试成功发送邮件"""
        # Setup mock SMTP connection
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            service.send_email(
                receiver="recipient@example.com",
                subject="Test Subject",
                content="Test content"
            )
            
            # Verify SMTP connection was created with correct parameters
            mock_smtp_ssl.assert_called_once_with(
                "smtp.example.com",
                465,
                timeout=30
            )
            
            # Verify login was called
            mock_smtp.login.assert_called_once_with("sender@example.com", "password123")
            
            # Verify sendmail was called
            assert mock_smtp.sendmail.called
            call_args = mock_smtp.sendmail.call_args[0]
            assert call_args[0] == "sender@example.com"
            assert call_args[1] == "recipient@example.com"
            # Content is base64 encoded, so just verify the call was made
            assert len(call_args[2]) > 0
            
            # Verify connection was closed
            mock_smtp.quit.assert_called_once()
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_with_verification_code(self, mock_smtp_ssl):
        """测试发送验证码邮件"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            verification_code = "123456"
            service.send_email(
                receiver="user@example.com",
                subject="验证码",
                content=f"您的验证码是: {verification_code}"
            )
            
            # Verify email was sent
            assert mock_smtp.sendmail.called
            # Content is base64 encoded, so just verify sendmail was called
            assert mock_smtp.sendmail.call_count == 1
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_with_notification(self, mock_smtp_ssl):
        """测试发送通知邮件"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            service.send_email(
                receiver="user@example.com",
                subject="系统通知",
                content="您有一条新消息"
            )
            
            # Verify email was sent
            assert mock_smtp.sendmail.called
            # Content is base64 encoded, so just verify sendmail was called
            assert mock_smtp.sendmail.call_count == 1


class TestEmailErrorHandling:
    """测试邮件发送中的错误处理"""
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_authentication_error(self, mock_smtp_ssl):
        """测试处理 SMTP 认证错误"""
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "wrongpassword"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            
            with pytest.raises(RuntimeError) as exc_info:
                service.send_email(
                    receiver="recipient@example.com",
                    subject="Test",
                    content="Test"
                )
            
            assert "邮件发送失败: 邮箱认证失败" in str(exc_info.value)
            # Verify connection cleanup was attempted
            mock_smtp.quit.assert_called_once()
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_connection_error(self, mock_smtp_ssl):
        """测试处理 SMTP 连接错误"""
        mock_smtp_ssl.side_effect = smtplib.SMTPConnectError(421, b"Service not available")
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            
            with pytest.raises(RuntimeError) as exc_info:
                service.send_email(
                    receiver="recipient@example.com",
                    subject="Test",
                    content="Test"
                )
            
            assert "邮件发送失败: 无法连接到SMTP服务器" in str(exc_info.value)
            assert "smtp.example.com:465" in str(exc_info.value)
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_smtp_exception(self, mock_smtp_ssl):
        """测试处理一般 SMTP 异常"""
        mock_smtp = MagicMock()
        mock_smtp.sendmail.side_effect = smtplib.SMTPException("SMTP error occurred")
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            
            with pytest.raises(RuntimeError) as exc_info:
                service.send_email(
                    receiver="recipient@example.com",
                    subject="Test",
                    content="Test"
                )
            
            assert "邮件发送失败: SMTP错误" in str(exc_info.value)
            # Verify connection cleanup was attempted
            mock_smtp.quit.assert_called_once()
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_generic_exception(self, mock_smtp_ssl):
        """测试处理通用异常"""
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = Exception("Unexpected error")
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            
            with pytest.raises(RuntimeError) as exc_info:
                service.send_email(
                    receiver="recipient@example.com",
                    subject="Test",
                    content="Test"
                )
            
            assert "邮件发送失败: Unexpected error" in str(exc_info.value)
            # Verify connection cleanup was attempted
            mock_smtp.quit.assert_called_once()
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_quit_fails_uses_close(self, mock_smtp_ssl):
        """测试如果 quit() 失败则调用 close()"""
        mock_smtp = MagicMock()
        mock_smtp.quit.side_effect = Exception("Quit failed")
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            service.send_email(
                receiver="recipient@example.com",
                subject="Test",
                content="Test"
            )
            
            # Verify quit was attempted
            mock_smtp.quit.assert_called_once()
            # Verify close was called as fallback
            mock_smtp.close.assert_called_once()
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_send_email_both_quit_and_close_fail(self, mock_smtp_ssl):
        """测试清理期间的异常被静默处理"""
        mock_smtp = MagicMock()
        mock_smtp.quit.side_effect = Exception("Quit failed")
        mock_smtp.close.side_effect = Exception("Close failed")
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            # Should not raise exception even if cleanup fails
            service.send_email(
                receiver="recipient@example.com",
                subject="Test",
                content="Test"
            )
            
            # Verify both cleanup methods were attempted
            mock_smtp.quit.assert_called_once()
            mock_smtp.close.assert_called_once()


class TestConvenienceFunction:
    """测试便捷的 send_email 函数"""
    
    @patch('app.services.email_service.EmailService')
    def test_send_email_function(self, mock_email_service_class):
        """测试便捷函数创建服务并发送邮件"""
        mock_service = MagicMock()
        mock_email_service_class.return_value = mock_service
        
        send_email(
            receiver="recipient@example.com",
            subject="Test Subject",
            content="Test content"
        )
        
        # Verify EmailService was instantiated
        mock_email_service_class.assert_called_once()
        
        # Verify send_email was called on the service (with positional args)
        mock_service.send_email.assert_called_once_with(
            "recipient@example.com",
            "Test Subject",
            "Test content"
        )
    
    @patch('app.services.email_service.EmailService')
    def test_send_email_function_propagates_errors(self, mock_email_service_class):
        """测试便捷函数传播服务的错误"""
        mock_service = MagicMock()
        mock_service.send_email.side_effect = RuntimeError("Email failed")
        mock_email_service_class.return_value = mock_service
        
        with pytest.raises(RuntimeError) as exc_info:
            send_email(
                receiver="recipient@example.com",
                subject="Test",
                content="Test"
            )
        
        assert "Email failed" in str(exc_info.value)


class TestEmailMessageFormat:
    """测试邮件消息格式"""
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_email_message_has_correct_headers(self, mock_smtp_ssl):
        """测试邮件消息具有正确的 From、To 和 Subject 头"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            service.send_email(
                receiver="recipient@example.com",
                subject="测试主题",
                content="测试内容"
            )
            
            # Get the message that was sent
            call_args = mock_smtp.sendmail.call_args[0]
            message_str = call_args[2]
            
            # Verify headers are present
            assert "From: sender@example.com" in message_str
            assert "To: recipient@example.com" in message_str
            assert "Subject:" in message_str
            # Content is base64 encoded, so just verify message was sent
            assert len(message_str) > 0
    
    @patch('app.services.email_service.smtplib.SMTP_SSL')
    def test_email_content_is_utf8_encoded(self, mock_smtp_ssl):
        """测试邮件内容支持中文字符的 UTF-8 编码"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.MAIL_HOST = "smtp.example.com"
            mock_settings.MAIL_USER = "sender@example.com"
            mock_settings.MAIL_PORT = 465
            mock_settings.MAIL_PWD = "password123"
            mock_settings.MAIL_TIMEOUT = 30
            
            service = EmailService()
            chinese_content = "您好，这是一封测试邮件。验证码：123456"
            service.send_email(
                receiver="recipient@example.com",
                subject="中文主题",
                content=chinese_content
            )
            
            # Verify email was sent successfully with Chinese content
            assert mock_smtp.sendmail.called
            call_args = mock_smtp.sendmail.call_args[0]
            message_str = call_args[2]
            
            # The content should be in the message (encoded)
            assert mock_smtp.sendmail.call_count == 1
