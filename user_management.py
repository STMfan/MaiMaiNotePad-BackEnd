# 导入必要的库
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from passlib.context import CryptContext

# 导入SQLite数据库管理器
from database_models import sqlite_db_manager, User as DBUser

# 配置日志
logger = logging.getLogger(__name__)

# 配置密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 用户模型（兼容原有接口）
class User:
    def __init__(self, db_user: DBUser = None):
        if db_user:
            # 从数据库用户模型创建
            self.userID = db_user.id
            self.username = db_user.username
            self.pwdHash = db_user.hashed_password
            self.email = db_user.email
            self.role = "admin" if db_user.is_admin else ("moderator" if db_user.is_moderator else "user")
            self.updateContent = []  # 这个字段在数据库模型中没有，暂时设为空列表
            self.created_at = db_user.created_at
            self.updated_at = db_user.created_at  # 数据库模型中没有updated_at字段
            self._db_user = db_user
        else:
            # 创建新用户
            self.userID = str(uuid.uuid4())
            self.username = ""
            self.pwdHash = ""
            self.email = ""
            self.role = "user"
            self.updateContent = []
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
            self._db_user = None

    def __str__(self):
        return f'UserID: {self.userID}, Username: {self.username}, Email: {self.email}, Role: {self.role}'

    def to_dict(self):
        """将用户对象转换为字典"""
        return {
            "userID": self.userID,
            "username": self.username,
            "pwdHash": self.pwdHash,
            "email": self.email,
            "role": self.role,
            "updateContent": self.updateContent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建用户对象"""
        user = cls()
        user.userID = data.get("userID", str(uuid.uuid4()))
        user.username = data.get("username", "")
        user.pwdHash = data.get("pwdHash", "")
        # 统一转换为小写
        email = data.get("email", "")
        user.email = email.lower() if email else ""
        user.role = data.get("role", "user")
        user.updateContent = data.get("updateContent", [])
        user.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        user.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        return user

    def to_admin(self, highest_pwd):
        """提升用户为管理员"""
        if pwd_context.verify(highest_pwd, pwd_context.hash(os.getenv('HIGHEST_PASSWORD', ''))):
            self.role = 'admin'
            self.updated_at = datetime.now()
            return self.save()
        else:
            logger.error(f'User {self.username} tried to become admin but failed')
            return False

    def to_moderator(self, highest_pwd):
        """提升用户为版主"""
        if pwd_context.verify(highest_pwd, pwd_context.hash(os.getenv('HIGHEST_PASSWORD', ''))):
            self.role = 'moderator'
            self.updated_at = datetime.now()
            return self.save()
        else:
            logger.error(f'User {self.username} tried to become moderator but failed')
            return False

    def save(self):
        """保存用户数据到数据库"""
        try:
            # 统一将邮箱转换为小写
            email_lower = self.email.lower() if self.email else ""
            
            # 创建或更新数据库用户模型
            if self._db_user:
                # 更新现有用户
                self._db_user.username = self.username
                self._db_user.hashed_password = self.pwdHash
                self._db_user.email = email_lower
                self._db_user.is_admin = (self.role == "admin")
                self._db_user.is_moderator = (self.role == "moderator")
            else:
                # 创建新用户
                self._db_user = DBUser(
                    id=self.userID,
                    username=self.username,
                    hashed_password=self.pwdHash,
                    email=email_lower,
                    is_admin=(self.role == "admin"),
                    is_moderator=(self.role == "moderator"),
                    created_at=datetime.now()
                )
            
            # 保存到数据库
            user_data = self._db_user.to_dict()
            return sqlite_db_manager.save_user(user_data)
        except Exception as e:
            logger.error(f'Error saving user {self.username}: {str(e)}')
            return False

    def update_file_record(self, fileName):
        """更新用户文件记录"""
        if fileName not in self.updateContent:
            self.updateContent.append(fileName)
            self.updated_at = datetime.now()
            return self.save()
        return True

    def pwd_update(self, original_pwd, new_pwd):
        """更新密码"""
        try:
            # 验证原始密码
            if not pwd_context.verify(original_pwd, self.pwdHash):
                logger.warning(f'{self.username} tried to update password but original password verification failed')
                return False

            # 确保新密码不超过72字节（bcrypt限制）
            new_pwd = new_pwd[:72]

            # 更新密码
            self.pwdHash = pwd_context.hash(new_pwd)
            self.updated_at = datetime.now()
            success = self.save()

            if success:
                logger.info(f'{self.username} updated password successfully')
            else:
                logger.error(f'{self.username} failed to update password')

            return success
        except Exception as e:
            logger.error(f'Error updating password for {self.username}: {str(e)}')
            return False

    def username_update(self, new_username):
        """更新用户名"""
        try:
            self.username = new_username
            self.updated_at = datetime.now()
            return self.save()
        except Exception as e:
            logger.error(f'Error updating username for {self.username}: {str(e)}')
            return False

    def update_email(self, new_email):
        """更新邮箱"""
        try:
            # 统一转换为小写存储
            self.email = new_email.lower()
            self.updated_at = datetime.now()
            return self.save()
        except Exception as e:
            logger.error(f'Error updating email for {self.username}: {str(e)}')
            return False


def load_users():
    """从数据库加载所有用户"""
    try:
        db_users = sqlite_db_manager.get_all_users()
        
        # 如果没有用户，创建默认管理员用户
        if not db_users:
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_pwd = os.getenv('ADMIN_PWD', 'admin123')
            # 确保密码不超过72字节（bcrypt限制）
            admin_pwd = admin_pwd[:72]
            external_domain = os.getenv('EXTERNAL_DOMAIN', 'example.com')

            admin = User()
            admin.userID = "111111"
            admin.username = admin_username
            admin.pwdHash = pwd_context.hash(admin_pwd)
            admin.email = f'official@{external_domain}'.lower()  # 统一转换为小写
            admin.role = 'admin'
            admin.updateContent = []
            admin.save()
            return [admin]

        # 转换数据库用户为User对象
        return [User(db_user) for db_user in db_users]
    except Exception as e:
        logger.error(f'Error loading users: {str(e)}')
        return []


def get_user_by_id(user_id: str) -> Optional[User]:
    """根据用户ID获取用户"""
    try:
        db_user = sqlite_db_manager.get_user_by_id(user_id)
        if db_user:
            return User(db_user)
        return None
    except Exception as e:
        logger.error(f'Error getting user by ID {user_id}: {str(e)}')
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名获取用户"""
    try:
        db_user = sqlite_db_manager.get_user_by_username(username)
        if db_user:
            return User(db_user)
        return None
    except Exception as e:
        logger.error(f'Error getting user by username {username}: {str(e)}')
        return None


def get_user_by_credentials(username: str, password: str) -> Optional[User]:
    """根据用户名和密码验证用户（防止时间攻击）"""
    import time
    try:
        db_user = sqlite_db_manager.get_user_by_username(username)
        
        # 使用虚拟密码哈希进行验证（如果用户不存在），防止时间攻击
        if not db_user:
            # 使用一个固定的虚拟哈希，确保验证时间一致
            dummy_hash = "$2b$12$dummy.hash.for.timing.attack.prevention.abcdefghijklmnopqrstuv"
            try:
                pwd_context.verify(password, dummy_hash)
            except:
                pass  # 忽略验证错误
            # 添加随机延迟，进一步模糊时间差异
            time.sleep(0.1)
            return None
        
        # 验证真实密码
        if db_user.verify_password(password):
            # 登录成功，重置失败次数
            reset_failed_login(db_user)
            return User(db_user)
        
        # 密码错误时也添加延迟
        time.sleep(0.1)
        # 增加失败登录次数
        increment_failed_login(db_user)
        return None
    except Exception as e:
        logger.error(f'Error verifying user credentials: {str(e)}')
        return None


def check_account_lock(db_user: DBUser) -> bool:
    """检查账户是否被锁定"""
    from datetime import datetime
    if db_user.locked_until and db_user.locked_until > datetime.now():
        return False  # 账户被锁定
    return True  # 账户未锁定


def increment_failed_login(db_user: DBUser):
    """增加失败登录次数并可能锁定账户"""
    from datetime import datetime, timedelta
    try:
        with sqlite_db_manager.get_session() as session:
            # 重新获取用户以确保数据最新
            user = session.query(DBUser).filter(DBUser.id == db_user.id).first()
            if not user:
                return
            
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login = datetime.now()
            
            # 5次失败后锁定30分钟
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now() + timedelta(minutes=30)
                logger.warning(f'Account locked: username={user.username}, attempts={user.failed_login_attempts}')
            
            session.commit()
    except Exception as e:
        logger.error(f'Error incrementing failed login: {str(e)}')


def reset_failed_login(db_user: DBUser):
    """重置失败登录次数"""
    from datetime import datetime
    try:
        with sqlite_db_manager.get_session() as session:
            # 重新获取用户以确保数据最新
            user = session.query(DBUser).filter(DBUser.id == db_user.id).first()
            if not user:
                return
            
            if user.failed_login_attempts > 0 or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                session.commit()
    except Exception as e:
        logger.error(f'Error resetting failed login: {str(e)}')


def get_user_by_credentials_with_lock_check(username: str, password: str) -> Optional[User]:
    """根据用户名和密码验证用户（带账户锁定检查）"""
    try:
        db_user = sqlite_db_manager.get_user_by_username(username)
        
        # 如果用户存在，检查是否被锁定
        if db_user:
            if not check_account_lock(db_user):
                from datetime import datetime
                if db_user.locked_until:
                    remaining_time = (db_user.locked_until - datetime.now()).total_seconds() / 60
                    logger.warning(f'Login attempt on locked account: username={db_user.username}, remaining={remaining_time:.1f}min')
                return None  # 账户被锁定
        
        # 使用原有的验证逻辑（已包含时间攻击防护）
        return get_user_by_credentials(username, password)
    except Exception as e:
        logger.error(f'Error verifying user credentials with lock check: {str(e)}')
        return None


def create_user(username: str, password: str, email: str, role: str = "user") -> Optional[User]:
    """创建新用户"""
    try:
        # 检查用户名是否已存在
        if get_user_by_username(username):
            return None
        
        # 确保密码不超过72字节（bcrypt限制）
        password = password[:72]
        
        # 创建新用户（邮箱统一转换为小写存储）
        new_user = User()
        new_user.username = username
        new_user.pwdHash = pwd_context.hash(password)
        new_user.email = email.lower()
        new_user.role = role
        
        if new_user.save():
            return new_user
        return None
    except Exception as e:
        logger.error(f'Error creating user {username}: {str(e)}')
        return None


def update_user_role(user_id: str, new_role: str) -> bool:
    """更新用户角色"""
    try:
        user = get_user_by_id(user_id)
        if not user:
            return False
        
        user.role = new_role
        user.updated_at = datetime.now()
        return user.save()
    except Exception as e:
        logger.error(f'Error updating user role: {str(e)}')
        return False


# FastAPI依赖项
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """获取当前认证用户"""
    token = credentials.credentials
    
    # 导入JWT验证工具
    from jwt_utils import get_user_from_token
    
    # 验证JWT令牌
    payload = get_user_from_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从JWT中获取用户信息
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从数据库获取用户信息
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码版本号（如果密码已修改，Token失效）
    if user._db_user:
        token_pwd_ver = payload.get("pwd_ver", 0)
        user_pwd_ver = user._db_user.password_version or 0
        if token_pwd_ver < user_pwd_ver:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired due to password change. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # 返回用户信息字典
    # 从数据库模型获取 is_admin 和 is_moderator，如果不存在则从 role 推导
    is_admin = False
    is_moderator = False
    if user._db_user:
        is_admin = user._db_user.is_admin
        is_moderator = user._db_user.is_moderator
    else:
        # 如果数据库模型不存在，从 role 推导
        is_admin = user.role == "admin"
        is_moderator = user.role in ["admin", "moderator"]
    
    return {
        "id": user.userID,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_admin": is_admin,
        "is_moderator": is_moderator
    }


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """获取当前管理员用户"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_moderator_user(current_user: dict = Depends(get_current_user)) -> dict:
    """获取当前版主或管理员用户"""
    if current_user.get("role") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """获取当前认证用户（可选，如果未提供token则返回None）"""
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # 导入JWT验证工具
    from jwt_utils import get_user_from_token
    
    # 验证JWT令牌
    payload = get_user_from_token(token)
    if not payload:
        return None
    
    # 从JWT中获取用户信息
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # 从数据库获取用户信息
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # 返回用户信息字典
    return {
        "id": user.userID,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }