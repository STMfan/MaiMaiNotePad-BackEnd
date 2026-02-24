"""
文件上传功能实现
支持txt、json、toml格式文件的上传和管理
"""

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any

import toml
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from app.core.config import settings
from app.core.config_manager import config_manager
from app.core.error_handlers import DatabaseError, ValidationError
from app.models.database import (
    KnowledgeBase,
    KnowledgeBaseFile,
    PersonaCard,
    PersonaCardFile,
    User,
)

load_dotenv()


class FileUploadService:
    """文件上传服务 - 使用 SQLAlchemy Session"""

    # 从配置管理器读取配置
    MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    MAX_PERSONA_TOML_SIZE = 5 * 1024 * 1024  # 人设卡 TOML 文件限制为 5MB
    MAX_KNOWLEDGE_FILES = config_manager.get_int("upload.knowledge.max_files", 100)
    MAX_PERSONA_FILES = config_manager.get_int("upload.persona.max_files", 1)
    ALLOWED_KNOWLEDGE_TYPES = config_manager.get_list("upload.knowledge.allowed_types", [".txt", ".json"])
    ALLOWED_PERSONA_TYPES = config_manager.get_list("upload.persona.allowed_types", [".toml"])

    def __init__(self, db: Session | None = None):
        """
        初始化文件上传服务

        Args:
            db: SQLAlchemy 数据库会话。如果为 None，将在每个方法中使用 get_db_context()
        """
        self.db = db
        self._owns_db = db is None  # 标记是否需要自己管理数据库会话

        # 使用配置管理器获取上传目录
        base_dir = os.getenv("UPLOAD_DIR", config_manager.get("upload.base_dir", "uploads"))
        if not base_dir:
            base_dir = "uploads"
        if not (base_dir.startswith("/") or base_dir.startswith(".")):
            base_dir = "./" + base_dir
        self.upload_dir = base_dir
        self.knowledge_dir = os.path.join(self.upload_dir, "knowledge")
        self.persona_dir = os.path.join(self.upload_dir, "persona")
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.knowledge_dir, exist_ok=True)
        os.makedirs(self.persona_dir, exist_ok=True)

    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self.db is not None:
            return self.db
        # 如果没有提供 db，这里会有问题，因为 get_db_context 是上下文管理器
        # 调用者应该使用 with get_db_context() 或提供 db
        raise RuntimeError(
            "数据库会话未提供。请在初始化时传入 db 参数，"
            "或使用 with get_db_context() as db: service = FileUploadService(db)"
        )

    async def _save_uploaded_file(self, file: UploadFile, target_dir: str) -> str:
        """保存上传的文件到目标目录"""
        try:
            # 创建唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{timestamp}_{file.filename}"
            file_path = os.path.join(target_dir, file_name)

            # 保存文件
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            return file_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"文件保存失败: {str(e)}"
            ) from e

    async def _save_uploaded_file_with_size(self, file: UploadFile, directory: str) -> tuple:
        """保存上传的文件到指定目录，并返回文件路径和文件大小(B)"""
        try:
            # 确保目录存在
            os.makedirs(directory, exist_ok=True)

            # 生成安全的文件名
            filename = secure_filename(file.filename)
            file_path = os.path.join(directory, filename)

            # 如果文件已存在，添加时间戳
            if os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}{ext}"
                file_path = os.path.join(directory, filename)

            # 保存文件并计算大小
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # 计算文件大小(B)
            file_size_b = len(content)  # 保持字节单位

            return file_path, file_size_b
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"文件保存失败: {str(e)}"
            ) from e

    def _validate_file_type(self, file: UploadFile, allowed_types: list[str]) -> bool:
        """验证文件类型"""
        if not file.filename:
            return False

        file_ext = os.path.splitext(file.filename)[1].lower()
        return file_ext in allowed_types

    def _validate_file_size(self, file: UploadFile) -> bool:
        """验证文件大小"""
        if not file.size:
            return True  # 如果无法获取大小，暂时允许

        return file.size <= self.MAX_FILE_SIZE

    def _validate_persona_toml_size(self, file: UploadFile) -> bool:
        """验证人设卡 TOML 文件大小（5MB 限制）"""
        if not file.size:
            return True  # 如果无法获取大小，暂时允许

        return file.size <= self.MAX_PERSONA_TOML_SIZE

    async def _validate_file_content(self, file: UploadFile) -> bool:
        """验证文件内容大小"""
        # 读取文件内容以验证实际大小
        content = await file.read()
        await file.seek(0)  # 重置文件指针

        return len(content) <= self.MAX_FILE_SIZE

    async def _validate_persona_toml_content(self, file: UploadFile) -> bool:
        """验证人设卡 TOML 文件内容大小（5MB 限制）"""
        # 读取文件内容以验证实际大小
        content = await file.read()
        await file.seek(0)  # 重置文件指针

        return len(content) <= self.MAX_PERSONA_TOML_SIZE

    def _extract_version_from_toml(self, data: dict[str, Any]) -> str | None:
        """从TOML数据中提取版本号

        Args:
            data: TOML数据字典

        Returns:
            Optional[str]: 版本号，如果未找到则返回None
        """
        if not isinstance(data, dict):
            return None

        # 尝试从顶层提取版本
        version = self._extract_version_from_top_level(data)
        if version:
            return version

        # 尝试从meta/card字段提取版本
        version = self._extract_version_from_meta_fields(data)
        if version:
            return version

        # 深度搜索版本字段
        return self._deep_search_version(data)

    def _extract_version_from_top_level(self, data: dict) -> str | None:
        """从顶层字段提取版本号

        Args:
            data: TOML数据字典

        Returns:
            版本号或None
        """
        version_keys = ["version", "Version", "schema_version", "card_version"]
        for key in version_keys:
            value = data.get(key)
            if isinstance(value, (str, int, float)):
                return str(value)
        return None

    def _extract_version_from_meta_fields(self, data: dict) -> str | None:
        """从meta或card字段中提取版本号

        Args:
            data: TOML数据字典

        Returns:
            版本号或None
        """
        meta_keys = ["meta", "Meta", "card", "Card"]
        version_keys = ["version", "Version", "schema_version", "card_version"]

        for meta_key in meta_keys:
            meta_value = data.get(meta_key)
            if isinstance(meta_value, dict):
                for version_key in version_keys:
                    value = meta_value.get(version_key)
                    if isinstance(value, (str, int, float)):
                        return str(value)
        return None

    def _deep_search_version(self, data: dict) -> str | None:
        """深度搜索版本字段

        Args:
            data: TOML数据字典

        Returns:
            版本号或None
        """
        visited = set()
        stack: list[Any] = [data]

        while stack:
            current = stack.pop()

            # 避免循环引用
            if id(current) in visited:
                continue
            visited.add(id(current))

            # 处理字典
            if isinstance(current, dict):
                version = self._search_version_in_dict(current, stack)
                if version:
                    return version

            # 处理列表
            elif isinstance(current, list):
                self._add_list_items_to_stack(current, stack)

        return None

    def _search_version_in_dict(self, data: dict, stack: list) -> str | None:
        """在字典中搜索版本字段

        Args:
            data: 字典数据
            stack: 搜索栈

        Returns:
            版本号或None
        """
        for k, v in data.items():
            # 找到version键
            if isinstance(k, str) and k.lower() == "version" and isinstance(v, (str, int, float)):
                return str(v)

            # 将嵌套结构加入栈
            if isinstance(v, dict):
                stack.append(v)
            elif isinstance(v, list):
                self._add_list_items_to_stack(v, stack)

        return None

    def _add_list_items_to_stack(self, items: list, stack: list) -> None:
        """将列表中的字典和列表项加入搜索栈

        Args:
            items: 列表项
            stack: 搜索栈
        """
        for item in items:
            if isinstance(item, (dict, list)):
                stack.append(item)

    def _create_metadata_file(self, metadata: dict[str, Any], target_dir: str, prefix: str) -> str:
        """创建元数据文件"""
        try:
            datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{prefix}_metadata.json"
            file_path = os.path.join(target_dir, file_name)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            return file_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"元数据文件创建失败: {str(e)}"
            ) from e

    async def upload_knowledge_base(
        self,
        files: list[UploadFile],
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: str | None = None,
        content: str | None = None,
        tags: str | None = None,
    ) -> KnowledgeBase:
        """上传知识库"""
        db = self._get_db()

        # 验证文件数量
        if len(files) > self.MAX_KNOWLEDGE_FILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件数量超过限制，最多允许{self.MAX_KNOWLEDGE_FILES}个文件",
            )

        # 验证文件类型和大小
        for file in files:
            if not self._validate_file_type(file, self.ALLOWED_KNOWLEDGE_TYPES):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的文件类型: {file.filename}。仅支持{', '.join(self.ALLOWED_KNOWLEDGE_TYPES)}文件",
                )

            if not self._validate_file_size(file):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                )

            # 验证实际文件内容大小
            if not await self._validate_file_content(file):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件内容过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                )

        # 创建知识库目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kb_dir = os.path.join(self.knowledge_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(kb_dir, exist_ok=True)

        try:
            # 创建知识库记录
            import uuid

            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                uploader_id=uploader_id,
                copyright_owner=copyright_owner,
                content=content,
                tags=tags,
                base_path=kb_dir,
                is_pending=True,  # 新上传的内容默认为待审核状态
                is_public=False,  # 新上传的内容默认为非公开
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            db.add(kb)
            db.flush()  # 获取 ID 但不提交

            # 保存上传的文件并创建文件记录
            for file in files:
                file_path, file_size_b = await self._save_uploaded_file_with_size(file, kb_dir)
                file_ext = os.path.splitext(file.filename)[1].lower()

                # 创建文件记录
                kb_file = KnowledgeBaseFile(
                    id=str(uuid.uuid4()),
                    knowledge_base_id=kb.id,
                    file_name=file.filename,
                    original_name=file.filename,
                    file_path=os.path.basename(file_path),  # 只存储文件名，相对于知识库目录
                    file_type=file_ext,
                    file_size=file_size_b,
                    created_at=datetime.now(),
                )
                db.add(kb_file)

            db.commit()
            db.refresh(kb)
            return kb

        except Exception as e:
            db.rollback()
            # 清理已创建的目录
            if os.path.exists(kb_dir):
                shutil.rmtree(kb_dir)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"知识库保存失败: {str(e)}"
            ) from e

    async def upload_persona_card(
        self,
        files: list[UploadFile],
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: str,
        content: str | None = None,
        tags: str | None = None,
    ) -> PersonaCard:
        """上传人设卡 - 处理文件操作并保存到数据库"""
        self._validate_persona_files(files)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pc_dir = os.path.join(self.persona_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(pc_dir, exist_ok=True)

        try:
            persona_version = await self._process_persona_files(files, pc_dir)
            pc = self._create_persona_card_object(
                name, description, uploader_id, copyright_owner, content, tags, pc_dir, persona_version
            )

            # 清除人设卡相关缓存
            try:
                from app.core.cache.factory import get_cache_manager
                from app.core.cache.invalidation import invalidate_persona_cache

                cache_manager = get_cache_manager()
                if cache_manager.is_enabled():
                    invalidate_persona_cache(pc.id)
            except Exception as cache_error:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"清除缓存失败: {cache_error}")

            return pc
        except Exception as e:
            if os.path.exists(pc_dir):
                shutil.rmtree(pc_dir)
            raise e

    def _validate_persona_files(self, files: list[UploadFile]) -> None:
        """验证人设卡文件

        Args:
            files: 上传的文件列表

        Raises:
            ValidationError: 文件验证失败
        """
        if len(files) != 1:
            raise ValidationError(
                message="人设卡配置错误：必须且仅包含一个 bot_config.toml 文件",
                details={"code": "PERSONA_FILE_COUNT_INVALID"},
            )

        for file in files:
            self._validate_single_persona_file(file)

    def _validate_single_persona_file(self, file: UploadFile) -> None:
        """验证单个人设卡文件

        Args:
            file: 上传的文件

        Raises:
            ValidationError: 文件验证失败
        """
        if file.filename != "bot_config.toml":
            raise ValidationError(
                message="人设卡配置错误：配置文件名必须为 bot_config.toml",
                details={"code": "PERSONA_FILE_NAME_INVALID", "filename": file.filename},
            )

        if not self._validate_file_type(file, self.ALLOWED_PERSONA_TYPES):
            raise ValidationError(
                message=f"人设卡配置错误：不支持的文件类型 {file.filename}，仅支持{', '.join(self.ALLOWED_PERSONA_TYPES)} 文件",
                details={"code": "PERSONA_FILE_TYPE_INVALID", "filename": file.filename},
            )

        if not self._validate_persona_toml_size(file):
            raise ValidationError(
                message=f"人设卡配置错误：文件过大 {file.filename}，单个文件最大允许{self.MAX_PERSONA_TOML_SIZE // (1024*1024)}MB",
                details={"code": "PERSONA_FILE_SIZE_EXCEEDED", "filename": file.filename},
            )

    async def _process_persona_files(self, files: list[UploadFile], pc_dir: str) -> str:
        """处理人设卡文件并提取版本号

        Args:
            files: 上传的文件列表
            pc_dir: 人设卡目录

        Returns:
            人设卡版本号

        Raises:
            ValidationError: 文件处理失败或版本号缺失
        """
        persona_version: str | None = None

        for file in files:
            if not await self._validate_persona_toml_content(file):
                raise ValidationError(
                    message=f"人设卡配置错误：文件内容过大 {file.filename}，单个文件最大允许{self.MAX_PERSONA_TOML_SIZE // (1024*1024)}MB",
                    details={"code": "PERSONA_FILE_CONTENT_SIZE_EXCEEDED", "filename": file.filename},
                )

            file_path, file_size_b = await self._save_uploaded_file_with_size(file, pc_dir)
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext == ".toml":
                persona_version = self._extract_persona_version(file_path)

        if not persona_version:
            raise ValidationError(
                message="人设卡配置错误：未能从 TOML 中解析出版本号，请在 bot_config.toml 中添加 version 等版本字段后重试",
                details={"code": "PERSONA_TOML_VERSION_MISSING"},
            )

        return persona_version

    def _extract_persona_version(self, file_path: str) -> str | None:
        """从 TOML 文件中提取版本号

        Args:
            file_path: TOML 文件路径

        Returns:
            版本号，如果未找到则返回 None

        Raises:
            ValidationError: TOML 解析失败
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                toml_data = toml.load(f)
            parsed_version = self._extract_version_from_toml(toml_data)
            if not parsed_version:
                raise ValidationError(
                    message="人设卡配置错误：TOML 中未找到版本号字段，请在 bot_config.toml 中添加 version 等版本字段后重试",
                    details={"code": "PERSONA_TOML_VERSION_MISSING"},
                )
            return parsed_version
        except HTTPException:
            raise
        except Exception:
            raise ValidationError(
                message="人设卡配置解析失败：TOML 语法错误，请检查 bot_config.toml 格式是否正确",
                details={"code": "PERSONA_TOML_PARSE_ERROR"},
            ) from None

    def _create_persona_card_object(
        self,
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: str,
        content: str | None,
        tags: str | None,
        pc_dir: str,
        persona_version: str,
    ) -> PersonaCard:
        """创建 PersonaCard 对象

        Args:
            name: 人设卡名称
            description: 人设卡描述
            uploader_id: 上传者ID
            copyright_owner: 版权所有者
            content: 内容
            tags: 标签
            pc_dir: 人设卡目录
            persona_version: 版本号

        Returns:
            PersonaCard 对象
        """
        import uuid

        return PersonaCard(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            uploader_id=uploader_id,
            copyright_owner=copyright_owner,
            content=content,
            tags=tags,
            base_path=pc_dir,
            version=persona_version,
            is_pending=True,
            is_public=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def get_knowledge_base_content(self, kb_id: str) -> dict[str, Any]:
        """获取知识库内容"""
        db = self._get_db()

        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

        # 获取知识库文件列表
        kb_files = db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()

        return {
            "knowledge_base": kb.to_dict(),
            "files": [
                {
                    "file_id": file.id,
                    "original_name": file.original_name,
                    "file_size": file.file_size,
                }
                for file in kb_files
            ],
        }

    def get_persona_card_content(self, pc_id: str) -> dict[str, Any]:
        """获取人设卡内容"""
        db = self._get_db()

        pc = db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()

        if not pc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="人设卡不存在")

        # 获取人设卡文件列表
        pc_files = db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).all()

        return {
            "persona_card": pc.to_dict(),
            "files": [
                {
                    "file_id": file.id,
                    "original_name": file.original_name,
                    "file_size": file.file_size,
                }
                for file in pc_files
            ],
        }

    async def add_files_to_knowledge_base(
        self, kb_id: str, files: list[UploadFile], user_id: str
    ) -> KnowledgeBase | None:
        """向知识库添加文件"""
        db = self._get_db()

        kb = self._get_kb_for_file_addition(db, kb_id)
        current_files = self._get_current_kb_files(db, kb_id)

        await self._validate_kb_file_addition(files, current_files)
        kb_dir = self._get_kb_directory(kb)

        try:
            await self._save_kb_files(db, kb_id, files, kb_dir)
            kb.updated_at = datetime.now()
            db.commit()
            db.refresh(kb)
            return kb

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"添加文件失败: {str(e)}"
            ) from e

    def _get_kb_for_file_addition(self, db, kb_id: str) -> KnowledgeBase:
        """获取知识库用于文件添加

        Args:
            db: 数据库会话
            kb_id: 知识库ID

        Returns:
            知识库对象

        Raises:
            ValidationError: 知识库不存在
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValidationError(message="知识库不存在")
        return kb

    def _get_current_kb_files(self, db, kb_id: str) -> list:
        """获取知识库当前文件列表

        Args:
            db: 数据库会话
            kb_id: 知识库ID

        Returns:
            文件列表
        """
        return db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()

    async def _validate_kb_file_addition(self, files: list[UploadFile], current_files: list) -> None:
        """验证知识库文件添加

        Args:
            files: 要添加的文件列表
            current_files: 当前文件列表

        Raises:
            ValidationError: 验证失败
        """
        self._check_kb_file_count_limit(len(files), len(current_files))
        self._check_kb_duplicate_filenames(files, current_files)
        await self._validate_kb_files_type_and_size(files)

    def _check_kb_file_count_limit(self, new_file_count: int, current_file_count: int) -> None:
        """检查知识库文件数量限制

        Args:
            new_file_count: 新文件数量
            current_file_count: 当前文件数量

        Raises:
            ValidationError: 超过限制
        """
        if current_file_count + new_file_count > self.MAX_KNOWLEDGE_FILES:
            raise ValidationError(
                message=f"文件数量超过限制，当前{current_file_count}个文件，最多允许{self.MAX_KNOWLEDGE_FILES}个文件"
            )

    def _check_kb_duplicate_filenames(self, files: list[UploadFile], current_files: list) -> None:
        """检查知识库重复文件名

        Args:
            files: 要添加的文件列表
            current_files: 当前文件列表

        Raises:
            ValidationError: 存在重复文件名
        """
        existing_file_names = {file.original_name for file in current_files}
        for file in files:
            if file.filename in existing_file_names:
                raise ValidationError(message=f"文件名已存在: {file.filename}")

    async def _validate_kb_files_type_and_size(self, files: list[UploadFile]) -> None:
        """验证知识库文件类型和大小

        Args:
            files: 文件列表

        Raises:
            ValidationError: 验证失败
        """
        for file in files:
            if not self._validate_file_type(file, self.ALLOWED_KNOWLEDGE_TYPES):
                raise ValidationError(
                    message=f"不支持的文件类型: {file.filename}。仅支持{', '.join(self.ALLOWED_KNOWLEDGE_TYPES)}文件"
                )

            if not self._validate_file_size(file):
                raise ValidationError(
                    message=f"文件过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB"
                )

            if not await self._validate_file_content(file):
                raise ValidationError(
                    message=f"文件内容过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB"
                )

    def _get_kb_directory(self, kb: KnowledgeBase) -> str:
        """获取知识库目录

        Args:
            kb: 知识库对象

        Returns:
            目录路径

        Raises:
            HTTPException: 目录不存在
        """
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="知识库目录不存在")
        return kb_dir

    async def _save_kb_files(self, db, kb_id: str, files: list[UploadFile], kb_dir: str) -> None:
        """保存知识库文件

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            files: 文件列表
            kb_dir: 知识库目录
        """
        import uuid

        for file in files:
            file_path, file_size_b = await self._save_uploaded_file_with_size(file, kb_dir)
            file_ext = os.path.splitext(file.filename)[1].lower()

            kb_file = KnowledgeBaseFile(
                id=str(uuid.uuid4()),
                knowledge_base_id=kb_id,
                file_name=file.filename,
                original_name=file.filename,
                file_path=os.path.basename(file_path),
                file_type=file_ext,
                file_size=file_size_b,
                created_at=datetime.now(),
            )
            db.add(kb_file)

    async def delete_files_from_knowledge_base(self, kb_id: str, file_id: str, user_id: str) -> bool:
        """从知识库删除文件"""
        db = self._get_db()

        # 获取知识库信息
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

        # 获取要删除的文件
        kb_file = (
            db.query(KnowledgeBaseFile)
            .filter(KnowledgeBaseFile.id == file_id, KnowledgeBaseFile.knowledge_base_id == kb_id)
            .first()
        )

        if not kb_file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="知识库目录不存在")

        try:
            # 删除物理文件
            file_full_path = os.path.join(kb_dir, kb_file.file_path)
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

            # 删除数据库记录
            db.delete(kb_file)

            # 更新知识库时间戳
            kb.updated_at = datetime.now()
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文件失败 {kb_file.original_name}: {str(e)}",
            ) from e

    async def delete_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """删除整个知识库"""
        db = self._get_db()

        # 获取知识库信息
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

        if not kb:
            return False

        # 获取知识库目录
        kb_dir = kb.base_path

        try:
            # 删除数据库中的文件记录
            db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).delete()

            # 删除知识库记录
            db.delete(kb)
            db.commit()

            # 删除整个知识库目录
            if kb_dir and os.path.exists(kb_dir):
                shutil.rmtree(kb_dir)

            return True

        except Exception as e:
            db.rollback()
            print(f"删除知识库失败 {kb_id}: {str(e)}")
            return False

    async def create_knowledge_base_zip(self, kb_id: str) -> dict:
        """创建知识库的ZIP文件，返回ZIP文件路径和文件名"""
        db = self._get_db()

        # 获取知识库信息
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

        # 获取知识库文件列表
        kb_files = db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()

        # 获取上传者信息
        uploader = db.query(User).filter(User.id == kb.uploader_id).first()
        uploader_name = uploader.username if uploader else "未知用户"

        # 检查文件是否存在
        missing_files = []
        for kb_file in kb_files:
            file_full_path = os.path.join(kb.base_path, kb_file.file_path)
            if not os.path.exists(file_full_path):
                missing_files.append(kb_file.original_name)

        if missing_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"以下文件不存在: {', '.join(missing_files)}"
            )

        # 创建临时ZIP文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{kb.name}-{uploader_name}_{timestamp}.zip"
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, zip_filename)

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # 添加知识库文件
                for kb_file in kb_files:
                    file_full_path = os.path.join(kb.base_path, kb_file.file_path)
                    zipf.write(file_full_path, kb_file.original_name)

                # 创建说明文件
                readme_content = f"""知识库下载包
==================

知识库名称: {kb.name}
描述: {kb.description}
上传者: {uploader_name}
版权所有者: {kb.copyright_owner or '未指定'}
创建时间: {kb.created_at}
更新时间: {kb.updated_at}

包含文件:
"""
                for kb_file in kb_files:
                    file_size_b = kb_file.file_size or 0
                    readme_content += f"- {kb_file.original_name} ({file_size_b} B)\n"

                readme_content += """
注意事项:
- 本压缩包包含知识库的所有文件
- 请遵守相关的版权协议
"""

                zipf.writestr("README.txt", readme_content)

            return {"zip_path": zip_path, "zip_filename": zip_filename}

        except Exception as e:
            # 清理临时文件
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建压缩包失败: {str(e)}"
            ) from e

    async def get_knowledge_base_file_path(self, kb_id: str, file_id: str) -> dict:
        """获取知识库中指定文件的完整路径"""
        db = self._get_db()

        # 获取知识库信息
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

        if not kb:
            return None

        # 查找文件
        kb_file = (
            db.query(KnowledgeBaseFile)
            .filter(KnowledgeBaseFile.id == file_id, KnowledgeBaseFile.knowledge_base_id == kb_id)
            .first()
        )

        if not kb_file:
            return None

        return {"file_name": kb_file.original_name, "file_path": kb_file.file_path}

    async def add_files_to_persona_card(self, pc_id: str, files: list[UploadFile]) -> PersonaCard | None:
        """向人设卡添加文件"""
        db = self._get_db()
        pc = self._get_persona_card(db, pc_id)
        if not pc:
            return None

        current_files = db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).all()
        self._validate_persona_files(files)

        pc_dir = self._get_persona_card_directory(pc)
        new_file = files[0]

        try:
            file_path, file_size_b, persona_version = await self._save_and_validate_persona_file(new_file, pc_dir)
            pc_file = self._create_persona_file_record(new_file, file_path, file_size_b, pc_id)

            db.add(pc_file)
            db.flush()

            self._remove_old_persona_files(db, current_files, pc_dir)
            self._update_persona_card_metadata(pc, persona_version)

            db.commit()
            db.refresh(pc)
            return pc

        except HTTPException:
            db.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        except Exception:
            db.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValidationError(
                message="人设卡配置解析失败：TOML 语法错误，请检查 bot_config.toml 格式是否正确",
                details={"code": "PERSONA_TOML_PARSE_ERROR"},
            ) from None

    def _get_persona_card(self, db, pc_id: str) -> PersonaCard | None:
        """获取人设卡信息"""
        return db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()

    async def _validate_persona_file_content(self, file: UploadFile) -> None:
        """验证人设卡文件内容大小"""
        if not await self._validate_persona_toml_content(file):
            raise ValidationError(
                message=f"人设卡配置错误：文件内容过大 {file.filename}，单个文件最大允许{self.MAX_PERSONA_TOML_SIZE // (1024*1024)}MB",
                details={"code": "PERSONA_FILE_CONTENT_SIZE_EXCEEDED", "filename": file.filename},
            )

    def _get_persona_card_directory(self, pc: PersonaCard) -> str:
        """获取人设卡目录"""
        pc_dir = pc.base_path
        if not pc_dir or not os.path.exists(pc_dir):
            raise DatabaseError(message="人设卡目录不存在，请稍后重试或联系管理员")
        return pc_dir

    async def _save_and_validate_persona_file(self, file: UploadFile, pc_dir: str) -> tuple:
        """保存并验证人设卡文件，返回 (file_path, file_size, version)"""
        await self._validate_persona_file_content(file)

        file_path, file_size_b = await self._save_uploaded_file_with_size(file, pc_dir)
        file_ext = os.path.splitext(file.filename)[1].lower()
        persona_version: str | None = None

        if file_ext == ".toml":
            with open(file_path, encoding="utf-8") as f:
                toml_data = toml.load(f)
            parsed_version = self._extract_version_from_toml(toml_data)
            if not parsed_version:
                raise ValidationError(
                    message="人设卡配置错误：TOML 中未找到版本号字段，请在 bot_config.toml 中添加 version 等版本字段后重试",
                    details={"code": "PERSONA_TOML_VERSION_MISSING"},
                )
            persona_version = parsed_version

        return file_path, file_size_b, persona_version

    def _create_persona_file_record(
        self, file: UploadFile, file_path: str, file_size: int, pc_id: str
    ) -> PersonaCardFile:
        """创建人设卡文件记录"""
        import uuid

        file_ext = os.path.splitext(file.filename)[1].lower()
        return PersonaCardFile(
            id=str(uuid.uuid4()),
            persona_card_id=pc_id,
            file_name=file.filename,
            original_name=file.filename,
            file_path=os.path.basename(file_path),
            file_type=file_ext,
            file_size=file_size,
            created_at=datetime.now(),
        )

    def _remove_old_persona_files(self, db, current_files: list[PersonaCardFile], pc_dir: str) -> None:
        """删除旧的人设卡文件"""
        for old_file in current_files:
            try:
                old_full_path = os.path.join(pc_dir, old_file.file_path)
                if os.path.exists(old_full_path):
                    os.remove(old_full_path)
                db.delete(old_file)
            except Exception as e:
                raise DatabaseError(message=f"删除旧人设卡文件失败：{old_file.original_name}，错误：{str(e)}") from e

    def _update_persona_card_metadata(self, pc: PersonaCard, version: str | None) -> None:
        """更新人设卡元数据"""
        pc.updated_at = datetime.now()
        if version:
            pc.version = version

    async def delete_files_from_persona_card(self, pc_id: str, file_id: str, user_id: str) -> bool:
        """从人设卡删除文件"""
        db = self._get_db()

        # 获取人设卡信息
        pc = db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()

        if not pc:
            return False

        # 获取要删除的文件
        pc_file = (
            db.query(PersonaCardFile)
            .filter(PersonaCardFile.id == file_id, PersonaCardFile.persona_card_id == pc_id)
            .first()
        )

        if not pc_file:
            return False

        # 获取人设卡目录
        pc_dir = pc.base_path
        if not pc_dir or not os.path.exists(pc_dir):
            return False

        try:
            # 删除物理文件
            file_full_path = os.path.join(pc_dir, pc_file.file_path)
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

            # 删除数据库记录
            db.delete(pc_file)

            # 更新人设卡时间戳
            pc.updated_at = datetime.now()
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文件失败 {pc_file.original_name}: {str(e)}",
            ) from e

    async def get_persona_card_file_path(self, pc_id: str, file_id: str) -> dict:
        """获取人设卡中指定文件的信息"""
        db = self._get_db()

        # 获取人设卡信息
        pc = db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()

        if not pc:
            return None

        # 查找文件
        pc_file = (
            db.query(PersonaCardFile)
            .filter(PersonaCardFile.id == file_id, PersonaCardFile.persona_card_id == pc_id)
            .first()
        )

        if not pc_file:
            return None

        return {"file_id": pc_file.id, "file_name": pc_file.original_name, "file_path": pc_file.file_path}

    async def create_persona_card_zip(self, pc_id: str) -> dict:
        """创建人设卡的ZIP文件，返回ZIP文件路径和文件名"""
        db = self._get_db()

        # 获取人设卡信息
        pc = db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()

        if not pc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="人设卡不存在")

        # 获取人设卡文件列表
        pc_files = db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).all()

        # 获取上传者信息
        uploader = db.query(User).filter(User.id == pc.uploader_id).first()
        uploader_name = uploader.username if uploader else "未知用户"

        # 检查文件是否存在
        missing_files = []
        for pc_file in pc_files:
            file_full_path = os.path.join(pc.base_path, pc_file.file_path)
            if not os.path.exists(file_full_path):
                missing_files.append(pc_file.original_name)

        if missing_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"以下文件不存在: {', '.join(missing_files)}"
            )

        # 创建临时ZIP文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{pc.name}-{uploader_name}_{timestamp}.zip"
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, zip_filename)

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # 添加人设卡文件
                for pc_file in pc_files:
                    file_full_path = os.path.join(pc.base_path, pc_file.file_path)
                    zipf.write(file_full_path, pc_file.original_name)

                # 创建说明文件
                readme_content = f"""人设卡下载包
    ==================

    人设卡名称: {pc.name}
    描述: {pc.description}
    上传者: {uploader_name}
    版权所有者: {pc.copyright_owner or '未指定'}
    创建时间: {pc.created_at}
    更新时间: {pc.updated_at}

    包含文件:
    """
                for pc_file in pc_files:
                    file_size_b = pc_file.file_size or 0
                    readme_content += f"- {pc_file.original_name} ({file_size_b} B)\n"

                readme_content += """
    注意事项:
    - 本压缩包包含人设卡的所有文件
    - 请遵守相关的版权协议
    """

                zipf.writestr("README.txt", readme_content)

            return {"zip_path": zip_path, "zip_filename": zip_filename}

        except Exception as e:
            # 清理临时文件
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建压缩包失败: {str(e)}"
            ) from e


# 注意：FileUploadService 需要在使用时传入 db 参数
# 示例：file_upload_service = FileUploadService(db=db)
