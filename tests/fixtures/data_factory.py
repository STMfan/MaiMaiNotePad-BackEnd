"""
测试数据工厂
用于创建测试所需的各种数据对象
"""

import os
import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.database import Comment, KnowledgeBase, KnowledgeBaseFile, Message, PersonaCard, PersonaCardFile, User

# 密码哈希缓存，避免重复计算
# 使用 worker-specific 字典以避免并行测试中的状态污染
_PASSWORD_HASH_CACHE = {}


def get_cached_password_hash(password: str) -> str:
    """获取缓存的密码哈希，如果不存在则计算并缓存

    为每个 worker 创建独立的缓存以避免并行测试中的状态污染
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    # 为每个 worker 创建独立的缓存
    if worker_id not in _PASSWORD_HASH_CACHE:
        _PASSWORD_HASH_CACHE[worker_id] = {}

    worker_cache = _PASSWORD_HASH_CACHE[worker_id]
    if password not in worker_cache:
        worker_cache[password] = get_password_hash(password)
    return worker_cache[password]


class TestDataFactory:
    """统一的测试数据创建工厂

    注意：这不是一个 pytest 测试类，尽管名字以 Test 开头。
    它是一个用于创建测试数据的工厂类。
    """

    __test__ = False  # 告诉 pytest 不要收集这个类

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, **kwargs) -> User:
        """创建测试用户，支持自定义属性"""
        # Handle password parameter
        password = kwargs.pop("password", "Test123!@#")

        defaults = {
            "username": f"user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "hashed_password": get_cached_password_hash(password),  # 使用缓存
            "is_active": True,
            "is_admin": False,
            "is_moderator": False,
            "is_super_admin": False,
        }
        defaults.update(kwargs)

        user = User(**defaults)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_admin_user(self, **kwargs) -> User:
        """创建管理员用户"""
        kwargs["is_admin"] = True
        return self.create_user(**kwargs)

    def create_moderator_user(self, **kwargs) -> User:
        """创建审核员用户"""
        kwargs["is_moderator"] = True
        return self.create_user(**kwargs)

    def create_knowledge_base(self, uploader: User | None = None, **kwargs) -> KnowledgeBase:
        """创建测试知识库"""
        if uploader is None:
            uploader = self.create_user()

        defaults = {
            "name": f"KB_{uuid.uuid4().hex[:8]}",
            "description": "Test knowledge base",
            "uploader_id": uploader.id,
            "copyright_owner": uploader.username,
            "is_public": False,
            "is_pending": False,
            "base_path": f"/tmp/kb_{uuid.uuid4().hex[:8]}",
        }
        defaults.update(kwargs)

        kb = KnowledgeBase(**defaults)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def create_persona_card(self, uploader: User | None = None, **kwargs) -> PersonaCard:
        """创建测试人设卡"""
        if uploader is None:
            uploader = self.create_user()

        defaults = {
            "name": f"PC_{uuid.uuid4().hex[:8]}",
            "description": "Test persona card",
            "uploader_id": uploader.id,
            "copyright_owner": uploader.username,
            "version": "1.0.0",
            "is_public": False,
            "is_pending": False,
            "base_path": f"/tmp/pc_{uuid.uuid4().hex[:8]}",
        }
        defaults.update(kwargs)

        pc = PersonaCard(**defaults)
        self.db.add(pc)
        self.db.commit()
        self.db.refresh(pc)
        return pc

    def create_message(self, sender: User | None = None, recipient: User | None = None, **kwargs) -> Message:
        """创建测试消息"""
        if sender is None:
            sender = self.create_user()
        if recipient is None:
            recipient = self.create_user()

        defaults = {
            "sender_id": sender.id,
            "recipient_id": recipient.id,
            "title": f"Test Message {uuid.uuid4().hex[:8]}",
            "content": "Test message content",
            "is_read": False,
            "message_type": "direct",
        }
        defaults.update(kwargs)

        message = Message(**defaults)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def create_comment(self, author: User | None = None, **kwargs) -> Comment:
        """创建测试评论"""
        if author is None:
            author = self.create_user()

        # 需要一个目标（知识库或人设卡）
        if "knowledge_base_id" not in kwargs and "persona_card_id" not in kwargs:
            kb = self.create_knowledge_base()
            kwargs["knowledge_base_id"] = kb.id

        defaults = {"author_id": author.id, "content": f"Test comment {uuid.uuid4().hex[:8]}"}
        defaults.update(kwargs)

        comment = Comment(**defaults)
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def create_knowledge_base_file(self, knowledge_base: KnowledgeBase | None = None, **kwargs) -> KnowledgeBaseFile:
        """创建测试知识库文件"""
        if knowledge_base is None:
            knowledge_base = self.create_knowledge_base()

        file_name = f"test_file_{uuid.uuid4().hex[:8]}.txt"
        defaults = {
            "knowledge_base_id": knowledge_base.id,
            "file_name": file_name,
            "original_name": kwargs.get("original_name", file_name),  # Add original_name
            "file_path": f"/tmp/kb_file_{uuid.uuid4().hex[:8]}.txt",
            "file_size": 1024,
            "file_type": "text/plain",
        }
        defaults.update(kwargs)

        kb_file = KnowledgeBaseFile(**defaults)
        self.db.add(kb_file)
        self.db.commit()
        self.db.refresh(kb_file)
        return kb_file

    def create_persona_card_file(self, persona_card: PersonaCard | None = None, **kwargs) -> PersonaCardFile:
        """创建测试人设卡文件"""
        if persona_card is None:
            persona_card = self.create_persona_card()

        file_name = f"test_file_{uuid.uuid4().hex[:8]}.txt"
        defaults = {
            "persona_card_id": persona_card.id,
            "file_name": file_name,
            "original_name": kwargs.get("original_name", file_name),  # Add original_name
            "file_path": f"/tmp/pc_file_{uuid.uuid4().hex[:8]}.txt",
            "file_size": 1024,
            "file_type": "text/plain",
        }
        defaults.update(kwargs)

        pc_file = PersonaCardFile(**defaults)
        self.db.add(pc_file)
        self.db.commit()
        self.db.refresh(pc_file)
        return pc_file

    def create_star_record(
        self, user: User | None = None, target_id: str = None, target_type: str = "knowledge_base", **kwargs
    ):
        """创建测试 Star 记录"""
        from app.models.database import StarRecord

        if user is None:
            user = self.create_user()
        if target_id is None:
            if target_type == "knowledge_base":
                kb = self.create_knowledge_base()
                target_id = kb.id
            elif target_type == "persona":
                pc = self.create_persona_card()
                target_id = pc.id

        defaults = {"user_id": user.id, "target_id": target_id, "target_type": target_type}
        defaults.update(kwargs)

        star = StarRecord(**defaults)
        self.db.add(star)
        self.db.commit()
        self.db.refresh(star)
        return star
