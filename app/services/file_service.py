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

        # 首先在顶层查找版本字段
        for key in ["version", "Version", "schema_version", "card_version"]:
            value = data.get(key)
            if isinstance(value, (str, int, float)):
                return str(value)

        # 在meta或card字段中查找
        meta_candidates = []
        for meta_key in ["meta", "Meta", "card", "Card"]:
            meta_value = data.get(meta_key)
            if isinstance(meta_value, dict):
                meta_candidates.append(meta_value)

        for meta in meta_candidates:
            for key in ["version", "Version", "schema_version", "card_version"]:
                value = meta.get(key)
                if isinstance(value, (str, int, float)):
                    return str(value)

        # 深度搜索
        visited = set()
        stack: List[Any] = [data]
        while stack:
            current = stack.pop()
            if id(current) in visited:
                continue
            visited.add(id(current))

            if isinstance(current, dict):
                for k, v in current.items():
                    if isinstance(k, str) and k.lower() == "version" and isinstance(v, (str, int, float)):
                        return str(v)
                    if isinstance(v, dict):
                        stack.append(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, (dict, list)):
                                stack.append(item)
            elif isinstance(current, list):
                for v in current:
                    if isinstance(v, (dict, list)):
                        stack.append(v)

        return None

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
        # 验证文件数量
        if len(files) != 1:
            raise FileValidationError(
                "人设卡配置错误：必须且仅包含一个 bot_config.toml 文件", code="PERSONA_FILE_COUNT_INVALID"
            )

        # 验证文件
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

        # 创建人设卡目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pc_dir = os.path.join(self.persona_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(pc_dir, exist_ok=True)

        try:
            # 保存文件
            file_path, file_size = self._save_file(file_content, filename, pc_dir)
            file_ext = os.path.splitext(filename)[1].lower()

            # 解析TOML获取版本号
            persona_version = None
            if file_ext == ".toml":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        toml_data = toml.load(f)
                    persona_version = self._extract_version_from_toml(toml_data)
                    if not persona_version:
                        raise FileValidationError(
                            "人设卡配置错误：TOML 中未找到版本号字段，请在 bot_config.toml 中添加 version 等版本字段后重试",
                            code="PERSONA_TOML_VERSION_MISSING",
                        )
                except FileValidationError:
                    raise
                except Exception:
                    raise FileValidationError(
                        "人设卡配置解析失败：TOML 语法错误，请检查 bot_config.toml 格式是否正确",
                        code="PERSONA_TOML_PARSE_ERROR",
                    )

            # 创建人设卡记录
            pc = PersonaCard(
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
            )
            self.db.add(pc)
            self.db.flush()

            # 创建文件记录
            pc_file = PersonaCardFile(
                persona_card_id=pc.id,
                file_name=filename,
                original_name=filename,
                file_path=os.path.basename(file_path),
                file_type=file_ext,
                file_size=file_size,
            )
            self.db.add(pc_file)

            self.db.commit()
            self.db.refresh(pc)
            return pc

        except Exception as e:
            self.db.rollback()
            # 清理已创建的目录
            if os.path.exists(pc_dir):
                shutil.rmtree(pc_dir)
            if isinstance(e, (FileValidationError, FileDatabaseError)):
                raise
            raise FileDatabaseError(f"人设卡保存失败: {str(e)}")

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
        # 获取知识库
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise FileValidationError("知识库不存在", code="KB_NOT_FOUND")

        # 获取现有文件
        current_files = self.db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()
        current_file_count = len(current_files)

        # 检查文件数量限制
        if current_file_count + len(files) > self.MAX_KNOWLEDGE_FILES:
            raise FileValidationError(
                f"文件数量超过限制，当前{current_file_count}个文件，最多允许{self.MAX_KNOWLEDGE_FILES}个文件",
                code="FILE_COUNT_EXCEEDED",
            )

        # 检查同名文件
        existing_file_names = {file.original_name for file in current_files}
        for filename, _ in files:
            if filename in existing_file_names:
                raise FileValidationError(f"文件名已存在: {filename}", code="DUPLICATE_FILENAME")

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

        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise FileDatabaseError("知识库目录不存在")

        try:
            # 保存新文件
            for filename, file_content in files:
                file_path, file_size = self._save_file(file_content, filename, kb_dir)
                file_ext = os.path.splitext(filename)[1].lower()

                # 创建文件记录
                kb_file = KnowledgeBaseFile(
                    knowledge_base_id=kb_id,
                    file_name=filename,
                    original_name=filename,
                    file_path=os.path.basename(file_path),
                    file_type=file_ext,
                    file_size=file_size,
                )
                self.db.add(kb_file)

            # 更新知识库时间戳
            kb.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(kb)
            return kb

        except Exception as e:
            self.db.rollback()
            if isinstance(e, (FileValidationError, FileDatabaseError)):
                raise
            raise FileDatabaseError(f"添加文件失败: {str(e)}")

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
