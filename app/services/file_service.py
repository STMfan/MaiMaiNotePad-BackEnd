"""
文件服务层
处理文件上传、下载、删除等业务逻辑
"""

import os
import shutil
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import toml
import tempfile
from werkzeug.utils import secure_filename

from app.core.config import settings
from app.core.config_manager import config_manager
from app.models.database import KnowledgeBase, PersonaCard, KnowledgeBaseFile, PersonaCardFile, User


class FileValidationError(Exception):
    """文件验证错误"""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class FileDatabaseError(Exception):
    """文件数据库操作错误"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FileService:
    """文件服务类"""

    # 从配置管理器读取配置
    MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    MAX_KNOWLEDGE_FILES = config_manager.get_int("upload.knowledge.max_files", 100)
    MAX_PERSONA_FILES = config_manager.get_int("upload.persona.max_files", 1)
    ALLOWED_KNOWLEDGE_TYPES = config_manager.get_list("upload.knowledge.allowed_types", [".txt", ".json"])
    ALLOWED_PERSONA_TYPES = config_manager.get_list("upload.persona.allowed_types", [".toml"])

    def __init__(self, db: Session):
        """初始化文件服务

        Args:
            db: 数据库会话
        """
        self.db = db

        # 设置上传目录
        base_dir = os.getenv("UPLOAD_DIR", "uploads")
        if not base_dir:
            base_dir = "uploads"
        if not (base_dir.startswith("/") or base_dir.startswith(".")):
            base_dir = "./" + base_dir
        self.upload_dir = base_dir
        self.knowledge_dir = os.path.join(self.upload_dir, "knowledge")
        self.persona_dir = os.path.join(self.upload_dir, "persona")

        # 确保目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.knowledge_dir, exist_ok=True)
        os.makedirs(self.persona_dir, exist_ok=True)

    def _save_file(self, file_content: bytes, filename: str, target_dir: str) -> tuple[str, int]:
        """保存文件到目标目录

        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            target_dir: 目标目录

        Returns:
            tuple: (文件路径, 文件大小)
        """
        try:
            # 确保目录存在
            os.makedirs(target_dir, exist_ok=True)

            # 生成安全的文件名
            safe_filename = secure_filename(filename)
            file_path = os.path.join(target_dir, safe_filename)

            # 如果文件已存在，添加时间戳
            if os.path.exists(file_path):
                name, ext = os.path.splitext(safe_filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"{name}_{timestamp}{ext}"
                file_path = os.path.join(target_dir, safe_filename)

            # 保存文件
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

            # 返回文件路径和大小
            file_size = len(file_content)
            return file_path, file_size

        except Exception as e:
            raise FileDatabaseError(f"文件保存失败: {str(e)}")

    def _validate_file_type(self, filename: str, allowed_types: List[str]) -> bool:
        """验证文件类型

        Args:
            filename: 文件名
            allowed_types: 允许的文件类型列表

        Returns:
            bool: 是否有效
        """
        if not filename:
            return False
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in allowed_types

    def _validate_file_size(self, file_size: int) -> bool:
        """验证文件大小

        Args:
            file_size: 文件大小（字节）

        Returns:
            bool: 是否有效
        """
        return file_size <= self.MAX_FILE_SIZE

    def _extract_version_from_toml(self, data: Dict[str, Any]) -> Optional[str]:
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

    def _extract_version_from_top_level(self, data: dict) -> Optional[str]:
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

    def _extract_version_from_meta_fields(self, data: dict) -> Optional[str]:
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

    def _deep_search_version(self, data: dict) -> Optional[str]:
        """深度搜索版本字段

        Args:
            data: TOML数据字典

        Returns:
            版本号或None
        """
        visited = set()
        stack: List[Any] = [data]

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

    def _search_version_in_dict(self, data: dict, stack: list) -> Optional[str]:
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

    def upload_knowledge_base(
        self,
        files: List[tuple[str, bytes]],  # List of (filename, content)
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> KnowledgeBase:
        """上传知识库

        Args:
            files: 文件列表，每个元素为(文件名, 文件内容)元组
            name: 知识库名称
            description: 描述
            uploader_id: 上传者ID
            copyright_owner: 版权所有者
            content: 内容
            tags: 标签

        Returns:
            KnowledgeBase: 创建的知识库对象
        """
        # 验证文件数量
        if len(files) > self.MAX_KNOWLEDGE_FILES:
            raise FileValidationError(
                f"文件数量超过限制，最多允许{self.MAX_KNOWLEDGE_FILES}个文件", code="FILE_COUNT_EXCEEDED"
            )

        # 验证文件类型和大小
        for filename, file_content in files:
            if not self._validate_file_type(filename, self.ALLOWED_KNOWLEDGE_TYPES):
                raise FileValidationError(
                    f"不支持的文件类型: {filename}。仅支持{', '.join(self.ALLOWED_KNOWLEDGE_TYPES)}文件",
                    code="INVALID_FILE_TYPE",
                )

            if not self._validate_file_size(len(file_content)):
                raise FileValidationError(
                    f"文件过大: {filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB", code="FILE_SIZE_EXCEEDED"
                )

        # 创建知识库目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kb_dir = os.path.join(self.knowledge_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(kb_dir, exist_ok=True)

        try:
            # 创建知识库记录
            kb = KnowledgeBase(
                name=name,
                description=description,
                uploader_id=uploader_id,
                copyright_owner=copyright_owner,
                content=content,
                tags=tags,
                base_path=kb_dir,
                is_pending=True,
                is_public=False,
            )
            self.db.add(kb)
            self.db.flush()  # 获取ID

            # 保存文件
            for filename, file_content in files:
                file_path, file_size = self._save_file(file_content, filename, kb_dir)
                file_ext = os.path.splitext(filename)[1].lower()

                # 创建文件记录
                kb_file = KnowledgeBaseFile(
                    knowledge_base_id=kb.id,
                    file_name=filename,
                    original_name=filename,
                    file_path=os.path.basename(file_path),
                    file_type=file_ext,
                    file_size=file_size,
                )
                self.db.add(kb_file)

            self.db.commit()
            self.db.refresh(kb)
            return kb

        except Exception as e:
            self.db.rollback()
            # 清理已创建的目录
            if os.path.exists(kb_dir):
                shutil.rmtree(kb_dir)
            raise FileDatabaseError(f"知识库保存失败: {str(e)}")

    def upload_persona_card(
        self,
        files: List[tuple[str, bytes]],  # List of (filename, content)
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: str,
        content: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> PersonaCard:
        """上传人设卡

        Args:
            files: 文件列表，每个元素为(文件名, 文件内容)元组
            name: 人设卡名称
            description: 描述
            uploader_id: 上传者ID
            copyright_owner: 版权所有者
            content: 内容
            tags: 标签

        Returns:
            PersonaCard: 创建的人设卡对象
        """
        filename, file_content = self._validate_persona_card_files(files)
        pc_dir = self._create_persona_card_directory(uploader_id)

        try:
            file_path, file_size, persona_version = self._process_persona_card_file(file_content, filename, pc_dir)
            pc = self._create_persona_card_record(
                name, description, uploader_id, copyright_owner, content, tags, pc_dir, persona_version
            )
            self._create_persona_card_file_record(pc.id, filename, file_path, file_size)

            self.db.commit()
            self.db.refresh(pc)
            return pc

        except Exception as e:
            self.db.rollback()
            self._cleanup_persona_card_directory(pc_dir)
            if isinstance(e, (FileValidationError, FileDatabaseError)):
                raise
            raise FileDatabaseError(f"人设卡保存失败: {str(e)}")

    def _validate_persona_card_files(self, files: List[tuple[str, bytes]]) -> tuple[str, bytes]:
        """验证人设卡文件

        Args:
            files: 文件列表

        Returns:
            (文件名, 文件内容) 元组

        Raises:
            FileValidationError: 文件验证失败
        """
        if len(files) != 1:
            raise FileValidationError(
                "人设卡配置错误：必须且仅包含一个 bot_config.toml 文件", code="PERSONA_FILE_COUNT_INVALID"
            )

        filename, file_content = files[0]

        if filename != "bot_config.toml":
            raise FileValidationError(
                "人设卡配置错误：配置文件名必须为 bot_config.toml",
                code="PERSONA_FILE_NAME_INVALID",
                details={"filename": filename},
            )

        if not self._validate_file_type(filename, self.ALLOWED_PERSONA_TYPES):
            raise FileValidationError(
                f"人设卡配置错误：不支持的文件类型 {filename}，仅支持{', '.join(self.ALLOWED_PERSONA_TYPES)} 文件",
                code="PERSONA_FILE_TYPE_INVALID",
                details={"filename": filename},
            )

        if not self._validate_file_size(len(file_content)):
            raise FileValidationError(
                f"人设卡配置错误：文件过大 {filename}，单个文件最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                code="PERSONA_FILE_SIZE_EXCEEDED",
                details={"filename": filename},
            )

        return filename, file_content

    def _create_persona_card_directory(self, uploader_id: str) -> str:
        """创建人设卡目录

        Args:
            uploader_id: 上传者ID

        Returns:
            目录路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pc_dir = os.path.join(self.persona_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(pc_dir, exist_ok=True)
        return pc_dir

    def _process_persona_card_file(
        self, file_content: bytes, filename: str, pc_dir: str
    ) -> tuple[str, int, Optional[str]]:
        """处理人设卡文件

        Args:
            file_content: 文件内容
            filename: 文件名
            pc_dir: 人设卡目录

        Returns:
            (文件路径, 文件大小, 版本号) 元组

        Raises:
            FileValidationError: 文件处理失败
        """
        file_path, file_size = self._save_file(file_content, filename, pc_dir)
        file_ext = os.path.splitext(filename)[1].lower()

        persona_version = None
        if file_ext == ".toml":
            persona_version = self._parse_persona_card_version(file_path)

        return file_path, file_size, persona_version

    def _parse_persona_card_version(self, file_path: str) -> str:
        """解析人设卡版本号

        Args:
            file_path: TOML 文件路径

        Returns:
            版本号

        Raises:
            FileValidationError: 解析失败
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                toml_data = toml.load(f)
            persona_version = self._extract_version_from_toml(toml_data)
            if not persona_version:
                raise FileValidationError(
                    "人设卡配置错误：TOML 中未找到版本号字段，请在 bot_config.toml 中添加 version 等版本字段后重试",
                    code="PERSONA_TOML_VERSION_MISSING",
                )
            return persona_version
        except FileValidationError:
            raise
        except Exception:
            raise FileValidationError(
                "人设卡配置解析失败：TOML 语法错误，请检查 bot_config.toml 格式是否正确",
                code="PERSONA_TOML_PARSE_ERROR",
            )

    def _create_persona_card_record(
        self,
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: str,
        content: Optional[str],
        tags: Optional[str],
        base_path: str,
        version: Optional[str],
    ) -> PersonaCard:
        """创建人设卡数据库记录

        Args:
            name: 名称
            description: 描述
            uploader_id: 上传者ID
            copyright_owner: 版权所有者
            content: 内容
            tags: 标签
            base_path: 基础路径
            version: 版本号

        Returns:
            人设卡对象
        """
        pc = PersonaCard(
            name=name,
            description=description,
            uploader_id=uploader_id,
            copyright_owner=copyright_owner,
            content=content,
            tags=tags,
            base_path=base_path,
            version=version,
            is_pending=True,
            is_public=False,
        )
        self.db.add(pc)
        self.db.flush()
        return pc

    def _create_persona_card_file_record(
        self, persona_card_id: str, filename: str, file_path: str, file_size: int
    ) -> None:
        """创建人设卡文件记录

        Args:
            persona_card_id: 人设卡ID
            filename: 文件名
            file_path: 文件路径
            file_size: 文件大小
        """
        file_ext = os.path.splitext(filename)[1].lower()
        pc_file = PersonaCardFile(
            persona_card_id=persona_card_id,
            file_name=filename,
            original_name=filename,
            file_path=os.path.basename(file_path),
            file_type=file_ext,
            file_size=file_size,
        )
        self.db.add(pc_file)

    def _cleanup_persona_card_directory(self, pc_dir: str) -> None:
        """清理人设卡目录

        Args:
            pc_dir: 目录路径
        """
        if os.path.exists(pc_dir):
            shutil.rmtree(pc_dir)

    def get_knowledge_base_content(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库内容

        Args:
            kb_id: 知识库ID

        Returns:
            Dict: 包含知识库信息和文件列表的字典
        """
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise FileValidationError("知识库不存在", code="KB_NOT_FOUND")

        # 获取知识库文件列表
        kb_files = self.db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()

        return {
            "knowledge_base": {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "uploader_id": kb.uploader_id,
                "copyright_owner": kb.copyright_owner,
                "content": kb.content,
                "tags": kb.tags,
                "is_public": kb.is_public,
                "is_pending": kb.is_pending,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at,
            },
            "files": [
                {
                    "file_id": file.id,
                    "original_name": file.original_name,
                    "file_size": file.file_size,
                }
                for file in kb_files
            ],
        }

    def get_persona_card_content(self, pc_id: str) -> Dict[str, Any]:
        """获取人设卡内容

        Args:
            pc_id: 人设卡ID

        Returns:
            Dict: 包含人设卡信息和文件列表的字典
        """
        pc = self.db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
        if not pc:
            raise FileValidationError("人设卡不存在", code="PC_NOT_FOUND")

        # 获取人设卡文件列表
        pc_files = self.db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).all()

        return {
            "persona_card": {
                "id": pc.id,
                "name": pc.name,
                "description": pc.description,
                "uploader_id": pc.uploader_id,
                "copyright_owner": pc.copyright_owner,
                "content": pc.content,
                "tags": pc.tags,
                "version": pc.version,
                "is_public": pc.is_public,
                "is_pending": pc.is_pending,
                "created_at": pc.created_at,
                "updated_at": pc.updated_at,
            },
            "files": [
                {
                    "file_id": file.id,
                    "original_name": file.original_name,
                    "file_size": file.file_size,
                }
                for file in pc_files
            ],
        }

    def add_files_to_knowledge_base(self, kb_id: str, files: List[tuple[str, bytes]], user_id: str) -> KnowledgeBase:
        """向知识库添加文件

        Args:
            kb_id: 知识库ID
            files: 文件列表，每个元素为(文件名, 文件内容)元组
            user_id: 用户ID

        Returns:
            KnowledgeBase: 更新后的知识库对象
        """
        kb = self._get_knowledge_base_for_file_addition(kb_id)
        current_files = self._get_current_knowledge_base_files(kb_id)

        self._validate_knowledge_base_file_addition(files, current_files)
        kb_dir = self._get_knowledge_base_directory(kb)

        try:
            self._save_knowledge_base_files(kb_id, files, kb_dir)
            kb.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(kb)
            return kb

        except Exception as e:
            self.db.rollback()
            if isinstance(e, (FileValidationError, FileDatabaseError)):
                raise
            raise FileDatabaseError(f"添加文件失败: {str(e)}")

    def _get_knowledge_base_for_file_addition(self, kb_id: str) -> KnowledgeBase:
        """获取知识库用于文件添加

        Args:
            kb_id: 知识库ID

        Returns:
            知识库对象

        Raises:
            FileValidationError: 知识库不存在
        """
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise FileValidationError("知识库不存在", code="KB_NOT_FOUND")
        return kb

    def _get_current_knowledge_base_files(self, kb_id: str) -> List:
        """获取知识库当前文件列表

        Args:
            kb_id: 知识库ID

        Returns:
            文件列表
        """
        return self.db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()

    def _validate_knowledge_base_file_addition(self, files: List[tuple[str, bytes]], current_files: List) -> None:
        """验证知识库文件添加

        Args:
            files: 要添加的文件列表
            current_files: 当前文件列表

        Raises:
            FileValidationError: 验证失败
        """
        self._check_knowledge_base_file_count_limit(len(files), len(current_files))
        self._check_knowledge_base_duplicate_filenames(files, current_files)
        self._validate_knowledge_base_files_type_and_size(files)

    def _check_knowledge_base_file_count_limit(self, new_file_count: int, current_file_count: int) -> None:
        """检查知识库文件数量限制

        Args:
            new_file_count: 新文件数量
            current_file_count: 当前文件数量

        Raises:
            FileValidationError: 超过限制
        """
        if current_file_count + new_file_count > self.MAX_KNOWLEDGE_FILES:
            raise FileValidationError(
                f"文件数量超过限制，当前{current_file_count}个文件，最多允许{self.MAX_KNOWLEDGE_FILES}个文件",
                code="FILE_COUNT_EXCEEDED",
            )

    def _check_knowledge_base_duplicate_filenames(self, files: List[tuple[str, bytes]], current_files: List) -> None:
        """检查知识库重复文件名

        Args:
            files: 要添加的文件列表
            current_files: 当前文件列表

        Raises:
            FileValidationError: 存在重复文件名
        """
        existing_file_names = {file.original_name for file in current_files}
        for filename, _ in files:
            if filename in existing_file_names:
                raise FileValidationError(f"文件名已存在: {filename}", code="DUPLICATE_FILENAME")

    def _validate_knowledge_base_files_type_and_size(self, files: List[tuple[str, bytes]]) -> None:
        """验证知识库文件类型和大小

        Args:
            files: 文件列表

        Raises:
            FileValidationError: 验证失败
        """
        for filename, file_content in files:
            if not self._validate_file_type(filename, self.ALLOWED_KNOWLEDGE_TYPES):
                raise FileValidationError(
                    f"不支持的文件类型: {filename}。仅支持{', '.join(self.ALLOWED_KNOWLEDGE_TYPES)}文件",
                    code="INVALID_FILE_TYPE",
                )

            if not self._validate_file_size(len(file_content)):
                raise FileValidationError(
                    f"文件过大: {filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB", code="FILE_SIZE_EXCEEDED"
                )

    def _get_knowledge_base_directory(self, kb: KnowledgeBase) -> str:
        """获取知识库目录

        Args:
            kb: 知识库对象

        Returns:
            目录路径

        Raises:
            FileDatabaseError: 目录不存在
        """
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise FileDatabaseError("知识库目录不存在")
        return kb_dir

    def _save_knowledge_base_files(self, kb_id: str, files: List[tuple[str, bytes]], kb_dir: str) -> None:
        """保存知识库文件

        Args:
            kb_id: 知识库ID
            files: 文件列表
            kb_dir: 知识库目录
        """
        for filename, file_content in files:
            file_path, file_size = self._save_file(file_content, filename, kb_dir)
            file_ext = os.path.splitext(filename)[1].lower()

            kb_file = KnowledgeBaseFile(
                knowledge_base_id=kb_id,
                file_name=filename,
                original_name=filename,
                file_path=os.path.basename(file_path),
                file_type=file_ext,
                file_size=file_size,
            )
            self.db.add(kb_file)

    def delete_file_from_knowledge_base(self, kb_id: str, file_id: str, user_id: str) -> bool:
        """从知识库删除文件

        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            bool: 是否成功删除
        """
        # 获取知识库
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise FileValidationError("知识库不存在", code="KB_NOT_FOUND")

        # 获取文件
        kb_file = (
            self.db.query(KnowledgeBaseFile)
            .filter(KnowledgeBaseFile.id == file_id, KnowledgeBaseFile.knowledge_base_id == kb_id)
            .first()
        )
        if not kb_file:
            raise FileValidationError("文件不存在", code="FILE_NOT_FOUND")

        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise FileDatabaseError("知识库目录不存在")

        try:
            # 删除物理文件
            file_full_path = os.path.join(kb_dir, kb_file.file_path)
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

            # 删除数据库记录
            self.db.delete(kb_file)

            # 更新知识库时间戳
            kb.updated_at = datetime.now()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise FileDatabaseError(f"删除文件失败: {str(e)}")

    def delete_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """删除整个知识库

        Args:
            kb_id: 知识库ID
            user_id: 用户ID

        Returns:
            bool: 是否成功删除
        """
        # 获取知识库
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return False

        # 获取知识库目录
        kb_dir = kb.base_path
        if kb_dir and os.path.exists(kb_dir):
            try:
                # 删除整个知识库目录
                shutil.rmtree(kb_dir)
            except Exception as e:
                print(f"删除知识库目录失败 {kb_dir}: {str(e)}")
                return False

        return True

    def create_knowledge_base_zip(self, kb_id: str) -> dict:
        """创建知识库的ZIP文件

        Args:
            kb_id: 知识库ID

        Returns:
            dict: 包含zip_path和zip_filename的字典
        """
        # 获取知识库
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise FileValidationError("知识库不存在", code="KB_NOT_FOUND")

        # 获取知识库文件列表
        kb_files = self.db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()

        # 获取上传者信息
        uploader = self.db.query(User).filter(User.id == kb.uploader_id).first()
        uploader_name = uploader.username if uploader else "未知用户"

        # 检查文件是否存在
        missing_files = []
        for kb_file in kb_files:
            file_full_path = os.path.join(kb.base_path, kb_file.file_path)
            if not os.path.exists(file_full_path):
                missing_files.append(kb_file.original_name)

        if missing_files:
            raise FileValidationError(f"以下文件不存在: {', '.join(missing_files)}", code="FILES_MISSING")

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
            raise FileDatabaseError(f"创建压缩包失败: {str(e)}")

    def create_persona_card_zip(self, pc_id: str) -> dict:
        """创建人设卡的ZIP文件

        Args:
            pc_id: 人设卡ID

        Returns:
            dict: 包含zip_path和zip_filename的字典
        """
        # 获取人设卡
        pc = self.db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
        if not pc:
            raise FileValidationError("人设卡不存在", code="PC_NOT_FOUND")

        # 获取人设卡文件列表
        pc_files = self.db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).all()

        # 获取上传者信息
        uploader = self.db.query(User).filter(User.id == pc.uploader_id).first()
        uploader_name = uploader.username if uploader else "未知用户"

        # 检查文件是否存在
        missing_files = []
        for pc_file in pc_files:
            file_full_path = os.path.join(pc.base_path, pc_file.file_path)
            if not os.path.exists(file_full_path):
                missing_files.append(pc_file.original_name)

        if missing_files:
            raise FileValidationError(f"以下文件不存在: {', '.join(missing_files)}", code="FILES_MISSING")

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
            raise FileDatabaseError(f"创建压缩包失败: {str(e)}")

    def get_knowledge_base_file_path(self, kb_id: str, file_id: str) -> Optional[dict]:
        """获取知识库中指定文件的完整路径

        Args:
            kb_id: 知识库ID
            file_id: 文件ID

        Returns:
            Optional[dict]: 包含file_name和file_path的字典，如果不存在则返回None
        """
        # 获取知识库
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return None

        # 查找文件
        kb_file = (
            self.db.query(KnowledgeBaseFile)
            .filter(KnowledgeBaseFile.id == file_id, KnowledgeBaseFile.knowledge_base_id == kb_id)
            .first()
        )

        if not kb_file:
            return None

        return {"file_name": kb_file.original_name, "file_path": kb_file.file_path}

    def get_persona_card_file_path(self, pc_id: str, file_id: str) -> Optional[dict]:
        """获取人设卡中指定文件的信息

        Args:
            pc_id: 人设卡ID
            file_id: 文件ID

        Returns:
            Optional[dict]: 包含file_id、file_name和file_path的字典，如果不存在则返回None
        """
        # 获取人设卡
        pc = self.db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
        if not pc:
            return None

        # 查找文件
        pc_file = (
            self.db.query(PersonaCardFile)
            .filter(PersonaCardFile.id == file_id, PersonaCardFile.persona_card_id == pc_id)
            .first()
        )

        if not pc_file:
            return None

        return {"file_id": pc_file.id, "file_name": pc_file.original_name, "file_path": pc_file.file_path}
