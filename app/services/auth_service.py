"""
认证服务模块

包含登录、注册、密码重置等认证相关的业务逻辑。
"""

import uuid
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.database import User, EmailVerification
from app.core.security import (
    verify_password,
    get_password_hash,
    create_user_token,
    create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.core.config_manager import config_manager

logger = logging.getLogger(__name__)


class AuthService:
    """
    认证服务类。
    处理登录、注册和密码重置逻辑。
    """

    def __init__(self, db: Session):
        """
        初始化认证服务。
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        使用用户名和密码进行身份验证。
        包含计时攻击防护和账户锁定检查。
        
        Args:
            username: 用户名
            password: 明文密码
            
        Returns:
            验证成功返回包含令牌和用户信息的字典，否则返回 None
        """
        import time
        try:
            user = self.db.query(User).filter(User.username == username).first()

            # 用户不存在时使用虚拟哈希验证（防止计时攻击）
            if not user:
                dummy_hash = "$2b$12$dummy.hash.for.timing.attack.prevention.abcdefghijklmnopqrstuv"
                try:
                    verify_password(password, dummy_hash)
                except:
                    pass
                # 添加随机延迟以进一步模糊时间差异
                time.sleep(0.1)
                return None

            # 检查账户是否被锁定
            if user.locked_until and user.locked_until > datetime.now():
                logger.warning(f'账户已锁定: username={username}, locked_until={user.locked_until}')
                time.sleep(0.1)
                return None

            # 验证密码
            if verify_password(password, user.hashed_password):
                # 登录成功，重置失败次数
                self._reset_failed_login(user)
                # 返回令牌和用户信息
                return self.create_tokens(user)

            # 密码错误，添加延迟并递增失败次数
            time.sleep(0.1)
            self._increment_failed_login(user)
            return None
        except Exception as e:
            logger.error(f'用户认证失败: {str(e)}')
            return None

    def create_tokens(self, user: User) -> Dict[str, Any]:
        """
        为已认证用户创建访问令牌和刷新令牌。
        
        Args:
            user: 已认证的用户对象
            
        Returns:
            包含 access_token、refresh_token、token_type、expires_in 和用户信息的字典
        """
        try:
            # 确定用户角色
            if user.is_super_admin:
                role = "super_admin"
            elif user.is_admin:
                role = "admin"
            elif user.is_moderator:
                role = "moderator"
            else:
                role = "user"

            # 创建令牌
            access_token = create_user_token(
                user_id=user.id,
                username=user.username,
                role=role,
                password_version=user.password_version or 0
            )
            refresh_token = create_refresh_token(user_id=user.id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 转换为秒
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                    "is_admin": user.is_admin,
                    "is_moderator": user.is_moderator,
                    "is_super_admin": user.is_super_admin
                }
            }
        except Exception as e:
            logger.error(f'为用户 {user.id} 创建令牌失败: {str(e)}')
            raise

    def register_user(
        self,
        username: str,
        password: str,
        email: str
    ) -> Optional[User]:
        """
        注册新用户（假设邮箱验证已完成）。
        
        Args:
            username: 用户名
            password: 明文密码
            email: 邮箱地址（应为小写）
            
        Returns:
            成功返回用户对象，否则返回 None
        """
        try:
            # 邮箱统一转小写
            email_lower = email.lower()
            
            # 检查是否重复
            legality_check = self.check_register_legality(username, email_lower)
            if legality_check != "ok":
                logger.warning(f'注册失败: {legality_check}')
                return None

            # 确保密码不超过 72 字节（bcrypt 限制）
            password = password[:72]

            # 创建新用户
            new_user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email_lower,
                hashed_password=get_password_hash(password),
                is_admin=False,
                is_moderator=False,
                is_super_admin=False,
                is_active=True,
                created_at=datetime.now(),
                password_version=0
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            logger.info(f'用户注册成功: username={username}, email={email_lower}')
            return new_user
        except Exception as e:
            self.db.rollback()
            logger.error(f'注册用户 {username} 失败: {str(e)}')
            return None

    def verify_email_code(self, email: str, code: str) -> bool:
        """
        验证邮箱验证码（未使用且未过期）。
        验证通过后将验证码标记为已使用。
        
        Args:
            email: 邮箱地址（应为小写）
            code: 验证码
            
        Returns:
            验证码有效返回 True，否则返回 False
        """
        try:
            record = self.db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.code == code,
                EmailVerification.is_used == False,
                EmailVerification.expires_at > datetime.now()
            ).first()

            if record:
                # 标记为已使用
                record.is_used = True
                self.db.commit()
                logger.info(f'邮箱验证码验证成功: email={email}')
                return True

            logger.warning(f'验证码无效或已过期: email={email}')
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f'验证邮箱验证码失败 {email}: {str(e)}')
            return False

    def save_verification_code(self, email: str, code: str) -> Optional[str]:
        """
        保存邮箱验证码到数据库。
        验证码有效期从配置读取（默认 2 分钟）。
        
        Args:
            email: 邮箱地址（应为小写）
            code: 验证码
            
        Returns:
            成功返回验证记录 ID，否则返回 None
        """
        try:
            # 从配置读取验证码有效期
            expire_minutes = config_manager.get_int("email_verification.code_expire_minutes", 2)
            
            verification = EmailVerification(
                id=str(uuid.uuid4()),
                email=email,
                code=code,
                is_used=False,
                expires_at=datetime.now() + timedelta(minutes=expire_minutes)
            )
            self.db.add(verification)
            self.db.commit()
            
            logger.info(f'验证码已保存: email={email}, code_id={verification.id}')
            return verification.id
        except Exception as e:
            self.db.rollback()
            logger.error(f'保存验证码失败 {email}: {str(e)}')
            return None

    def check_email_rate_limit(self, email: str) -> bool:
        """
        检查邮箱是否超过发送频率限制。
        限制从配置读取（默认：每小时 5 次，每分钟 1 次）
        
        Args:
            email: 邮箱地址（应为小写）
            
        Returns:
            未超限返回 True，已超限返回 False
        """
        try:
            # 从配置读取频率限制
            hourly_limit = config_manager.get_int("email_verification.hourly_limit", 5)
            minute_limit = config_manager.get_int("email_verification.minute_limit", 1)
            
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            one_minute_ago = now - timedelta(minutes=1)

            # 检查每小时限制
            hourly_count = self.db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.created_at > one_hour_ago
            ).count()
            
            if hourly_count >= hourly_limit:
                logger.warning(f'邮箱发送频率超限（每小时）: email={email}, count={hourly_count}')
                return False

            # 检查每分钟限制
            minute_count = self.db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.created_at > one_minute_ago
            ).count()
            
            if minute_count >= minute_limit:
                logger.warning(f'邮箱发送频率超限（每分钟）: email={email}')
                return False

            return True
        except Exception as e:
            logger.error(f'检查邮箱发送频率失败 {email}: {str(e)}')
            return False

    def reset_password(
        self,
        email: str,
        verification_code: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        通过邮箱验证重置用户密码。
        
        Args:
            email: 邮箱地址
            verification_code: 邮箱验证码
            new_password: 新明文密码
            
        Returns:
            (是否成功, 提示消息) 元组
        """
        try:
            # 邮箱统一转小写
            email_lower = email.lower()

            # 验证邮箱验证码
            if not self.verify_email_code(email_lower, verification_code):
                return False, "验证码错误或已失效"

            # 根据邮箱查找用户
            user = self.db.query(User).filter(User.email == email_lower).first()
            if not user:
                return False, "用户不存在"

            # 确保密码不超过 72 字节（bcrypt 限制）
            new_password = new_password[:72]

            # 更新密码并递增密码版本号
            user.hashed_password = get_password_hash(new_password)
            user.password_version = (user.password_version or 0) + 1

            # 重置登录失败次数
            user.failed_login_attempts = 0
            user.locked_until = None

            self.db.commit()

            logger.info(f'密码重置成功: username={user.username}, email={email_lower}')
            return True, "密码重置成功"
        except Exception as e:
            self.db.rollback()
            logger.error(f'重置密码失败 {email}: {str(e)}')
            return False, "密码重置失败"

    def generate_verification_code(self) -> str:
        """
        生成 6 位数字验证码。
        
        Returns:
            6 位数字验证码字符串
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def send_verification_code(self, email: str) -> Optional[str]:
        """
        生成并保存注册用邮箱验证码。
        
        Args:
            email: 邮箱地址（应为小写）
            
        Returns:
            成功返回验证记录 ID，否则返回 None
        """
        try:
            code = self.generate_verification_code()
            code_id = self.save_verification_code(email, code)
            
            if code_id:
                # 发送验证码邮件
                from app.services.email_service import send_email
                subject = "MaiMaiNotePad 注册验证码"
                body = f"您的验证码是: {code}\n\n验证码将在2分钟后过期。"
                send_email(email, subject, body)
                
            return code_id
        except Exception as e:
            logger.error(f'发送验证码到 {email} 失败: {str(e)}')
            raise

    def send_reset_password_code(self, email: str) -> Optional[str]:
        """
        生成并保存重置密码用邮箱验证码。
        
        Args:
            email: 邮箱地址（应为小写）
            
        Returns:
            成功返回验证记录 ID，否则返回 None
        """
        try:
            code = self.generate_verification_code()
            code_id = self.save_verification_code(email, code)
            
            if code_id:
                # 发送验证码邮件
                from app.services.email_service import send_email
                subject = "MaiMaiNotePad 重置密码验证码"
                body = f"您的重置密码验证码是: {code}\n\n验证码将在2分钟后过期。"
                send_email(email, subject, body)
                
            return code_id
        except Exception as e:
            logger.error(f'发送重置密码验证码到 {email} 失败: {str(e)}')
            raise

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        使用刷新令牌获取新的访问令牌。
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            包含新 access_token 和用户信息的字典
        """
        from app.core.security import verify_token, create_user_token
        
        try:
            # 验证刷新令牌
            payload = verify_token(refresh_token)
            if not payload:
                raise ValueError("无效的刷新令牌")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("无效的令牌载荷")
            
            # 从数据库获取用户
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            
            # 确定用户角色
            if user.is_super_admin:
                role = "super_admin"
            elif user.is_admin:
                role = "admin"
            elif user.is_moderator:
                role = "moderator"
            else:
                role = "user"
            
            # 创建新的访问令牌
            access_token = create_user_token(
                user_id=user.id,
                username=user.username,
                role=role,
                password_version=user.password_version or 0
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user_id": user.id
            }
        except Exception as e:
            logger.error(f'刷新访问令牌失败: {str(e)}')
            raise

    def check_register_legality(self, username: str, email: str) -> str:
        """
        检查用户名和邮箱是否可用于注册。
        
        Args:
            username: 用户名
            email: 邮箱地址（应为小写）
            
        Returns:
            可用返回 "ok"，否则返回错误消息
        """
        try:
            # 检查用户名是否已存在
            user = self.db.query(User).filter(User.username == username).first()
            if user:
                return "用户名已存在"

            # 检查邮箱是否已存在
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                return "该邮箱已被注册"

            return "ok"
        except Exception as e:
            logger.error(f'检查注册合法性失败: {str(e)}')
            return "系统错误"

    def _increment_failed_login(self, user: User) -> None:
        """
        递增登录失败次数，可能锁定账户。
        失败次数限制和锁定时长从配置读取（默认：5 次失败后锁定 30 分钟）
        
        Args:
            user: 用户对象
        """
        try:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login = datetime.now()

            # 从配置读取失败次数限制和锁定时长
            max_attempts = config_manager.get_int("security.max_failed_login_attempts", 5)
            lock_duration = config_manager.get_int("security.account_lock_duration_minutes", 30)
            
            # 达到失败次数限制后锁定账户
            if user.failed_login_attempts >= max_attempts:
                user.locked_until = datetime.now() + timedelta(minutes=lock_duration)
                logger.warning(
                    f'账户因多次登录失败被锁定: '
                    f'username={user.username}, attempts={user.failed_login_attempts}'
                )

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f'递增用户 {user.id} 登录失败次数出错: {str(e)}')

    def _reset_failed_login(self, user: User) -> None:
        """
        登录成功后重置失败次数。
        
        Args:
            user: 用户对象
        """
        try:
            if user.failed_login_attempts > 0 or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f'重置用户 {user.id} 登录失败次数出错: {str(e)}')
