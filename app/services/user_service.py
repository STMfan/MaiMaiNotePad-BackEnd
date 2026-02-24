"""
用户服务模块
包含用户管理相关的业务逻辑
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.database import User
from app.core.security import verify_password, get_password_hash
from app.core.config_manager import config_manager
from app.core.cache.decorators import cached, cache_invalidate
from app.core.cache.invalidation import invalidate_user_cache

logger = logging.getLogger(__name__)


class UserService:
    """
    用户管理服务类。
    处理用户的增删改查操作和认证逻辑。
    """

    def __init__(self, db: Session):
        """
        初始化用户服务。

        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        根据 ID 获取用户。

        Args:
            user_id: 用户 ID

        Returns:
            找到返回用户对象，否则返回 None
        """
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户。

        Args:
            username: 用户名

        Returns:
            找到返回用户对象，否则返回 None
        """
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {str(e)}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户。

        Args:
            email: 邮箱地址（会自动转为小写）

        Returns:
            找到返回用户对象，否则返回 None
        """
        try:
            email_lower = email.lower() if email else ""
            return self.db.query(User).filter(User.email == email_lower).first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None

    def get_all_users(self) -> List[User]:
        """
        获取数据库中所有用户。

        Returns:
            用户对象列表
        """
        try:
            return self.db.query(User).all()
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False,
        is_moderator: bool = False,
        is_super_admin: bool = False,
    ) -> Optional[User]:
        """
        创建新用户。

        Args:
            username: 用户名
            email: 邮箱地址
            password: 明文密码
            is_admin: 是否为管理员
            is_moderator: 是否为审核员
            is_super_admin: 是否为超级管理员

        Returns:
            成功返回创建的用户对象，否则返回 None
        """
        try:
            # 检查用户名是否已存在
            if self.get_user_by_username(username):
                logger.warning(f"Username {username} already exists")
                return None

            # 检查邮箱是否已存在
            email_lower = email.lower() if email else ""
            if self.get_user_by_email(email_lower):
                logger.warning(f"Email {email_lower} already exists")
                return None

            # 确保密码不超过 72 字节（bcrypt 限制）
            password = password[:72]

            # 创建新用户
            new_user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email_lower,
                hashed_password=get_password_hash(password),
                is_admin=is_admin,
                is_moderator=is_moderator,
                is_super_admin=is_super_admin,
                is_active=True,
                created_at=datetime.now(),
                password_version=0,
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            # 失效用户缓存
            invalidate_user_cache()

            logger.info(f"User {username} created successfully")
            return new_user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user {username}: {str(e)}")
            return None

    @cache_invalidate(key_pattern="user:{user_id}")
    def update_user(self, user_id: str, username: Optional[str] = None, email: Optional[str] = None) -> Optional[User]:
        """
        更新用户信息（自动失效缓存）。

        Args:
            user_id: 用户 ID
            username: 新用户名（可选）
            email: 新邮箱（可选）

        Returns:
            成功返回更新后的用户对象，否则返回 None
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None

            # 检查是否尝试修改超级管理员用户名
            if username and username != user.username and user.is_super_admin:
                logger.warning(f"Super admin username change attempted and blocked: {user.username} -> {username}")
                raise ValueError("不能修改超级管理员用户名")

            # 如果提供了新用户名则更新
            if username and username != user.username:
                # 检查新用户名是否已存在
                existing = self.get_user_by_username(username)
                if existing and existing.id != user_id:
                    logger.warning(f"Username {username} already exists")
                    return None
                
                user.username = username

            # 如果提供了新邮箱则更新
            if email and email != user.email:
                email_lower = email.lower()
                # 检查新邮箱是否已存在
                existing = self.get_user_by_email(email_lower)
                if existing and existing.id != user_id:
                    logger.warning(f"Email {email_lower} already exists")
                    return None
                user.email = email_lower

            self.db.commit()
            self.db.refresh(user)

            # 失效用户缓存
            invalidate_user_cache()

            logger.info(f"User {user.username} updated successfully")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise

    def update_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        更新用户密码。

        Args:
            user_id: 用户 ID
            old_password: 当前密码
            new_password: 新密码

        Returns:
            成功返回 True，否则返回 False
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            # 验证旧密码
            if not verify_password(old_password, user.hashed_password):
                logger.warning(f"User {user.username} tried to update password but old password verification failed")
                return False

            # 确保新密码不超过 72 字节（bcrypt 限制）
            new_password = new_password[:72]

            # 更新密码
            user.hashed_password = get_password_hash(new_password)
            # 递增密码版本号以使现有令牌失效
            user.password_version = (user.password_version or 0) + 1

            self.db.commit()

            # 失效用户缓存
            invalidate_user_cache()

            logger.info(f"User {user.username} updated password successfully")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating password for user {user_id}: {str(e)}")
            return False

    def update_role(
        self, user_id: str, is_admin: Optional[bool] = None, is_moderator: Optional[bool] = None
    ) -> Optional[User]:
        """
        更新用户角色。

        Args:
            user_id: 用户 ID
            is_admin: 是否为管理员（可选）
            is_moderator: 是否为审核员（可选）

        Returns:
            成功返回更新后的用户对象，否则返回 None
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None

            if is_admin is not None:
                user.is_admin = is_admin
            if is_moderator is not None:
                user.is_moderator = is_moderator

            self.db.commit()
            self.db.refresh(user)

            # 失效用户缓存
            invalidate_user_cache()

            logger.info(f"User {user.username} role updated successfully")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating role for user {user_id}: {str(e)}")
            return None

    def verify_credentials(self, username: str, password: str) -> Optional[User]:
        """
        验证用户凭证（带计时攻击防护）。

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            凭证有效返回用户对象，否则返回 None
        """
        import time

        try:
            user = self.get_user_by_username(username)

            # 如果用户不存在，使用虚拟哈希验证（防止计时攻击）
            if not user:
                dummy_hash = "$2b$12$dummy.hash.for.timing.attack.prevention.abcdefghijklmnopqrstuv"
                try:
                    verify_password(password, dummy_hash)
                except Exception:
                    pass
                # 添加随机延迟以进一步模糊时间差异
                time.sleep(0.1)
                return None

            # 验证真实密码
            if verify_password(password, user.hashed_password):
                # 登录成功，重置失败次数
                self.reset_failed_login(user.id)
                return user

            # 密码错误，添加延迟
            time.sleep(0.1)
            # 递增登录失败次数
            self.increment_failed_login(user.id)
            return None
        except Exception as e:
            logger.error(f"Error verifying user credentials: {str(e)}")
            return None

    def check_account_lock(self, user_id: str) -> bool:
        """
        检查账户是否被锁定。

        Args:
            user_id: 用户 ID

        Returns:
            账户未锁定返回 True，已锁定返回 False
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            if user.locked_until and user.locked_until > datetime.now():
                return False  # Account is locked

            return True  # Account is not locked
        except Exception as e:
            logger.error(f"Error checking account lock for user {user_id}: {str(e)}")
            return False

    def increment_failed_login(self, user_id: str) -> None:
        """
        递增登录失败次数，可能锁定账户。

        Args:
            user_id: 用户 ID
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return

            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login = datetime.now()

            # 从配置读取失败次数限制和锁定时长
            max_attempts = config_manager.get_int("security.max_failed_login_attempts", 5)
            lock_duration = config_manager.get_int("security.account_lock_duration_minutes", 30)

            # 达到失败次数限制后锁定账户
            if user.failed_login_attempts >= max_attempts:
                user.locked_until = datetime.now() + timedelta(minutes=lock_duration)
                logger.warning(f"Account locked: username={user.username}, attempts={user.failed_login_attempts}")

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error incrementing failed login for user {user_id}: {str(e)}")

    def reset_failed_login(self, user_id: str) -> None:
        """
        重置登录失败次数。

        Args:
            user_id: 用户 ID
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return

            if user.failed_login_attempts > 0 or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resetting failed login for user {user_id}: {str(e)}")

    def ensure_super_admin_exists(self) -> None:
        """
        确保默认超级管理员账户存在。
        如果不存在则创建。
        """
        try:
            # 检查超级管理员是否存在
            super_admin = self.db.query(User).filter(User.is_super_admin.is_(True)).first()
            if super_admin:
                return

            # 创建超级管理员
            super_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
            super_pwd = os.getenv("SUPERADMIN_PWD", "admin123456")
            external_domain = os.getenv("EXTERNAL_DOMAIN", "example.com")

            super_pwd = super_pwd[:72]  # bcrypt 限制

            super_admin = User(
                id=str(uuid.uuid4()),
                username=super_username,
                email=f"{super_username}@{external_domain}".lower(),
                hashed_password=get_password_hash(super_pwd),
                is_active=True,
                is_admin=False,
                is_moderator=False,
                is_super_admin=True,
                created_at=datetime.now(),
                password_version=0,
            )

            self.db.add(super_admin)
            self.db.commit()

            logger.info(f"Super admin account created: {super_username}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error ensuring super admin exists: {str(e)}")

    def promote_to_admin(self, user_id: str, highest_pwd: str) -> bool:
        """
        将用户提升为管理员角色。

        Args:
            user_id: 用户 ID
            highest_pwd: 最高权限密码用于验证

        Returns:
            成功返回 True，否则返回 False
        """
        try:
            # 验证最高权限密码
            highest_password_hash = get_password_hash(os.getenv("HIGHEST_PASSWORD", ""))
            if not verify_password(highest_pwd, highest_password_hash):
                logger.error(f"User {user_id} tried to become admin but highest password verification failed")
                return False

            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_admin = True
            self.db.commit()

            logger.info(f"User {user.username} promoted to admin")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error promoting user {user_id} to admin: {str(e)}")
            return False

    def promote_to_moderator(self, user_id: str, highest_pwd: str) -> bool:
        """
        将用户提升为审核员角色。

        Args:
            user_id: 用户 ID
            highest_pwd: 最高权限密码用于验证

        Returns:
            成功返回 True，否则返回 False
        """
        try:
            # 验证最高权限密码
            highest_password_hash = get_password_hash(os.getenv("HIGHEST_PASSWORD", ""))
            if not verify_password(highest_pwd, highest_password_hash):
                logger.error(f"User {user_id} tried to become moderator but highest password verification failed")
                return False

            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_moderator = True
            self.db.commit()

            logger.info(f"User {user.username} promoted to moderator")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error promoting user {user_id} to moderator: {str(e)}")
            return False

    def get_upload_records_by_uploader(
        self, uploader_id: str, page: int = 1, page_size: int = 20, status: Optional[str] = None
    ) -> List:
        """
        Get upload records by uploader with pagination and optional status filter.

        Args:
            uploader_id: Uploader user ID
            page: Page number (starting from 1)
            page_size: Number of records per page
            status: Optional status filter (approved, rejected, pending)

        Returns:
            List of UploadRecord objects
        """
        try:
            from app.models.database import UploadRecord

            query = self.db.query(UploadRecord).filter(UploadRecord.uploader_id == uploader_id)

            # Apply status filter if provided
            if status:
                query = query.filter(UploadRecord.status == status)

            # Apply pagination
            offset = (page - 1) * page_size
            records = query.order_by(UploadRecord.created_at.desc()).offset(offset).limit(page_size).all()

            return records
        except Exception as e:
            logger.error(f"Error getting upload records for uploader {uploader_id}: {str(e)}")
            return []

    def get_upload_records_count_by_uploader(self, uploader_id: str, status: Optional[str] = None) -> int:
        """
        Get total count of upload records by uploader with optional status filter.

        Args:
            uploader_id: Uploader user ID
            status: Optional status filter (approved, rejected, pending)

        Returns:
            Total count of upload records
        """
        try:
            from app.models.database import UploadRecord

            query = self.db.query(UploadRecord).filter(UploadRecord.uploader_id == uploader_id)

            # Apply status filter if provided
            if status:
                query = query.filter(UploadRecord.status == status)

            return query.count()
        except Exception as e:
            logger.error(f"Error counting upload records for uploader {uploader_id}: {str(e)}")
            return 0

    def get_upload_stats_by_uploader(self, uploader_id: str) -> dict:
        """
        Get upload statistics for a user.

        Args:
            uploader_id: Uploader user ID

        Returns:
            Dictionary with upload statistics
        """
        try:
            from app.models.database import UploadRecord

            # Get all records
            all_records = self.db.query(UploadRecord).filter(UploadRecord.uploader_id == uploader_id).all()

            # Calculate statistics
            total = len(all_records)
            success = sum(1 for r in all_records if r.status == "approved")
            pending = sum(1 for r in all_records if r.status == "pending")
            failed = sum(1 for r in all_records if r.status == "rejected")
            knowledge = sum(1 for r in all_records if r.target_type == "knowledge")
            persona = sum(1 for r in all_records if r.target_type == "persona")

            return {
                "total": total,
                "success": success,
                "pending": pending,
                "failed": failed,
                "knowledge": knowledge,
                "persona": persona,
            }
        except Exception as e:
            logger.error(f"Error getting upload stats for uploader {uploader_id}: {str(e)}")
            return {"total": 0, "success": 0, "pending": 0, "failed": 0, "knowledge": 0, "persona": 0}

    def get_knowledge_base_by_id(self, kb_id: str):
        """
        Get knowledge base by ID.

        Args:
            kb_id: Knowledge base ID

        Returns:
            KnowledgeBase object if found, None otherwise
        """
        try:
            from app.models.database import KnowledgeBase

            return self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        except Exception as e:
            logger.error(f"Error getting knowledge base {kb_id}: {str(e)}")
            return None

    def get_persona_card_by_id(self, pc_id: str):
        """
        Get persona card by ID.

        Args:
            pc_id: Persona card ID

        Returns:
            PersonaCard object if found, None otherwise
        """
        try:
            from app.models.database import PersonaCard

            return self.db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
        except Exception as e:
            logger.error(f"Error getting persona card {pc_id}: {str(e)}")
            return None

    def get_total_file_size_by_target(self, target_id: str, target_type: str) -> int:
        """
        Get total file size for a target (knowledge base or persona card).

        Args:
            target_id: Target ID
            target_type: Target type ('knowledge' or 'persona')

        Returns:
            Total file size in bytes
        """
        try:
            if target_type == "knowledge":
                from app.models.database import KnowledgeBaseFile

                kb_files = (
                    self.db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == target_id).all()
                )
                total_size = sum(f.file_size for f in kb_files if f.file_size)
                return total_size
            elif target_type == "persona":
                from app.models.database import PersonaCardFile

                pc_files = self.db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == target_id).all()
                total_size = sum(f.file_size for f in pc_files if f.file_size)
                return total_size
            else:
                return 0
        except Exception as e:
            logger.error(f"Error getting total file size for {target_type} {target_id}: {str(e)}")
            return 0

    def get_dashboard_trend_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get download and star trend statistics for a user.

        Args:
            user_id: User ID (uploader)
            days: Number of days to include in the trend (default 30, max 90)

        Returns:
            Dictionary with trend statistics, including a list of daily items.
        """
        try:
            from sqlalchemy import func
            from app.models.database import KnowledgeBase, PersonaCard, DownloadRecord, StarRecord

            # 从配置读取天数限制
            min_days = config_manager.get_int("statistics.min_trend_days", 1)
            max_days = config_manager.get_int("statistics.max_trend_days", 90)

            if days < min_days:
                days = min_days
            if days > max_days:
                days = max_days

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            kb_downloads: Dict[str, int] = {}
            persona_downloads: Dict[str, int] = {}
            kb_stars: Dict[str, int] = {}
            persona_stars: Dict[str, int] = {}

            kb_download_rows = (
                self.db.query(
                    func.date(DownloadRecord.created_at).label("day"),
                    func.count(DownloadRecord.id).label("count"),
                )
                .join(KnowledgeBase, DownloadRecord.target_id == KnowledgeBase.id)
                .filter(
                    DownloadRecord.target_type == "knowledge",
                    KnowledgeBase.uploader_id == user_id,
                    DownloadRecord.created_at >= start_dt,
                    DownloadRecord.created_at <= end_dt,
                )
                .group_by(func.date(DownloadRecord.created_at))
                .all()
            )
            for row in kb_download_rows:
                day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)
                kb_downloads[day_str] = int(row.count or 0)

            persona_download_rows = (
                self.db.query(
                    func.date(DownloadRecord.created_at).label("day"),
                    func.count(DownloadRecord.id).label("count"),
                )
                .join(PersonaCard, DownloadRecord.target_id == PersonaCard.id)
                .filter(
                    DownloadRecord.target_type == "persona",
                    PersonaCard.uploader_id == user_id,
                    DownloadRecord.created_at >= start_dt,
                    DownloadRecord.created_at <= end_dt,
                )
                .group_by(func.date(DownloadRecord.created_at))
                .all()
            )
            for row in persona_download_rows:
                day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)
                persona_downloads[day_str] = int(row.count or 0)

            kb_star_rows = (
                self.db.query(
                    func.date(StarRecord.created_at).label("day"),
                    func.count(StarRecord.id).label("count"),
                )
                .join(KnowledgeBase, StarRecord.target_id == KnowledgeBase.id)
                .filter(
                    StarRecord.target_type == "knowledge",
                    KnowledgeBase.uploader_id == user_id,
                    StarRecord.created_at >= start_dt,
                    StarRecord.created_at <= end_dt,
                )
                .group_by(func.date(StarRecord.created_at))
                .all()
            )
            for row in kb_star_rows:
                day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)
                kb_stars[day_str] = int(row.count or 0)

            persona_star_rows = (
                self.db.query(
                    func.date(StarRecord.created_at).label("day"),
                    func.count(StarRecord.id).label("count"),
                )
                .join(PersonaCard, StarRecord.target_id == PersonaCard.id)
                .filter(
                    StarRecord.target_type == "persona",
                    PersonaCard.uploader_id == user_id,
                    StarRecord.created_at >= start_dt,
                    StarRecord.created_at <= end_dt,
                )
                .group_by(func.date(StarRecord.created_at))
                .all()
            )
            for row in persona_star_rows:
                day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)
                persona_stars[day_str] = int(row.count or 0)

            items = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                day_str = day.strftime("%Y-%m-%d")
                items.append(
                    {
                        "date": day_str,
                        "knowledgeDownloads": kb_downloads.get(day_str, 0),
                        "personaDownloads": persona_downloads.get(day_str, 0),
                        "knowledgeStars": kb_stars.get(day_str, 0),
                        "personaStars": persona_stars.get(day_str, 0),
                    }
                )

            return {
                "days": days,
                "items": items,
            }
        except Exception as e:
            logger.error(f"Error getting dashboard trend stats for user {user_id}: {str(e)}")
            return {
                "days": days,
                "items": [],
            }
