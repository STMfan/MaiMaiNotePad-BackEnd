"""
Unit tests for email service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import smtplib

from app.services.email_service import EmailService, send_email


class TestEmailService:
    """Test cases for EmailService"""

    @pytest.fixture
    def email_service(self):
        """Create EmailService instance"""
        return EmailService()

    def test_email_service_initialization(self, email_service: EmailService):
        """Test EmailService initializes with correct configuration"""
        assert email_service.mail_host is not None
        assert email_service.mail_user is not None
        assert email_service.mail_port is not None
        assert email_service.mail_pwd is not None
        assert email_service.mail_timeout is not None

    @patch('smtplib.SMTP_SSL')
    def test_send_email_success(self, mock_smtp_ssl, email_service: EmailService):
        """Test successful email sending"""
        # Setup mock
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp

        # Send email
        email_service.send_email(
            receiver="test@example.com",
            subject="Test Subject",
            content="Test Content"
        )

        # Verify SMTP methods were called
        mock_smtp_ssl.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_authentication_error(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending with authentication error"""
        # Setup mock to raise authentication error
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp_ssl.return_value = mock_smtp

        # Verify exception is raised
        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "邮箱认证失败" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_connection_error(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending with connection error"""
        # Setup mock to raise connection error
        mock_smtp_ssl.side_effect = smtplib.SMTPConnectError(421, b"Cannot connect")

        # Verify exception is raised
        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "无法连接到SMTP服务器" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_smtp_exception(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending with generic SMTP exception"""
        # Setup mock to raise SMTP exception
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPException("SMTP error")
        mock_smtp_ssl.return_value = mock_smtp

        # Verify exception is raised
        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "SMTP错误" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_cleanup_on_error(self, mock_smtp_ssl, email_service: EmailService):
        """Test that SMTP connection is properly closed even on error"""
        # Setup mock to raise error during send
        mock_smtp = MagicMock()
        mock_smtp.sendmail.side_effect = Exception("Send failed")
        mock_smtp_ssl.return_value = mock_smtp

        # Verify exception is raised and cleanup happens
        with pytest.raises(RuntimeError):
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        # Verify quit was called for cleanup
        mock_smtp.quit.assert_called_once()

    @patch('app.services.email_service.EmailService.send_email')
    def test_send_email_convenience_function(self, mock_send_email):
        """Test the convenience send_email function"""
        # Call convenience function
        send_email(
            receiver="test@example.com",
            subject="Test Subject",
            content="Test Content"
        )

        # Verify EmailService.send_email was called
        mock_send_email.assert_called_once_with(
            "test@example.com",
            "Test Subject",
            "Test Content"
        )

    @patch('smtplib.SMTP_SSL')
    def test_send_email_with_html_content(self, mock_smtp_ssl, email_service: EmailService):
        """Test sending email with HTML content"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp

        html_content = "<html><body><h1>Test</h1></body></html>"
        email_service.send_email(
            receiver="test@example.com",
            subject="HTML Test",
            content=html_content
        )

        mock_smtp.sendmail.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_with_special_characters(self, mock_smtp_ssl, email_service: EmailService):
        """Test sending email with special characters in subject and content"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp

        email_service.send_email(
            receiver="test@example.com",
            subject="测试主题 - Test Subject 🎉",
            content="测试内容 - Test Content with émojis 🚀"
        )

        mock_smtp.sendmail.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_timeout_error(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending with timeout error"""
        mock_smtp_ssl.side_effect = TimeoutError("Connection timeout")

        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "邮件发送失败" in str(exc_info.value) or "发送邮件失败" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_recipient_refused(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending when recipient is refused"""
        mock_smtp = MagicMock()
        mock_smtp.sendmail.side_effect = smtplib.SMTPRecipientsRefused({
            "test@example.com": (550, b"User unknown")
        })
        mock_smtp_ssl.return_value = mock_smtp

        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "SMTP错误" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_sender_refused(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending when sender is refused"""
        mock_smtp = MagicMock()
        mock_smtp.sendmail.side_effect = smtplib.SMTPSenderRefused(
            550, b"Sender refused", "sender@example.com"
        )
        mock_smtp_ssl.return_value = mock_smtp

        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "SMTP错误" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_data_error(self, mock_smtp_ssl, email_service: EmailService):
        """Test email sending with data error"""
        mock_smtp = MagicMock()
        mock_smtp.sendmail.side_effect = smtplib.SMTPDataError(554, b"Message rejected")
        mock_smtp_ssl.return_value = mock_smtp

        with pytest.raises(RuntimeError) as exc_info:
            email_service.send_email(
                receiver="test@example.com",
                subject="Test Subject",
                content="Test Content"
            )
        
        assert "SMTP错误" in str(exc_info.value)

    @patch('smtplib.SMTP_SSL')
    def test_send_email_empty_subject(self, mock_smtp_ssl, email_service: EmailService):
        """Test sending email with empty subject"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp

        email_service.send_email(
            receiver="test@example.com",
            subject="",
            content="Test Content"
        )

        mock_smtp.sendmail.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_empty_content(self, mock_smtp_ssl, email_service: EmailService):
        """Test sending email with empty content"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp

        email_service.send_email(
            receiver="test@example.com",
            subject="Test Subject",
            content=""
        )

        mock_smtp.sendmail.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_long_content(self, mock_smtp_ssl, email_service: EmailService):
        """Test sending email with very long content"""
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp

        long_content = "A" * 10000
        email_service.send_email(
            receiver="test@example.com",
            subject="Test Subject",
            content=long_content
        )

        mock_smtp.sendmail.assert_called_once()
