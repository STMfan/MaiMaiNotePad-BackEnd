"""
文件上传功能实现
支持txt、json、toml格式文件的上传和管理
"""

import os
import shutil
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel
import toml
import json
import tempfile
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from app.models.database import (
    KnowledgeBase,
    PersonaCard,
    KnowledgeBaseFile,
)
from app.error_handlers import ValidationError
from app.core.database import get_db_context

load_dotenv()


class FileUploadService:
    """文件上传服务"""

    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    MAX_KNOWLEDGE_FILES = 100
    MAX_PERSONA_FILES = 1
    ALLOWED_KNOWLEDGE_TYPES = [".txt", ".json"]
    ALLOWED_PERSONA_TYPES = [".toml"]

    def __init__(self):
        base_dir = os.getenv("UPLOAD_DIR", "uploads")
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件保存失败: {str(e)}"
            )

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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件保存失败: {str(e)}"
            )

    def _validate_file_type(self, file: UploadFile, allowed_types: List[str]) -> bool:
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

    async def _validate_file_content(self, file: UploadFile) -> bool:
        """验证文件内容大小"""
        # 读取文件内容以验证实际大小
        content = await file.read()
        await file.seek(0)  # 重置文件指针

        return len(content) <= self.MAX_FILE_SIZE

    def _extract_version_from_toml(self, data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        for key in ["version", "Version", "schema_version", "card_version"]:
            value = data.get(key)
            if isinstance(value, (str, int, float)):
                return str(value)
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
        visited = set()
        stack = [data]
        while stack:
            current = stack.pop()
            if id(current) in visited:
                continue
            visited.add(id(current))
            if isinstance(current, dict):
                for k, v in current.items():
                    if isinstance(k, str) and k.lower() == "version" and isinstance(v, (str, int, float)):
                        return str(v)
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(current, list):
                for v in current:
                    if isinstance(v, (dict, list)):
                        stack.append(v)
        return None

    def _create_metadata_file(self, metadata: Dict[str, Any], target_dir: str, prefix: str) -> str:
        """创建元数据文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{prefix}_metadata.json"
            file_path = os.path.join(target_dir, file_name)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            return file_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"元数据文件创建失败: {str(e)}"
            )

    async def upload_knowledge_base(
        self,
        files: List[UploadFile],
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> KnowledgeBase:
        """上传知识库"""
        # 验证文件数量
        if len(files) > self.MAX_KNOWLEDGE_FILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件数量超过限制，最多允许{self.MAX_KNOWLEDGE_FILES}个文件"
            )

        # 验证文件类型和大小
        for file in files:
            if not self._validate_file_type(file, self.ALLOWED_KNOWLEDGE_TYPES):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的文件类型: {file.filename}。仅支持{', '.join(self.ALLOWED_KNOWLEDGE_TYPES)}文件"
                )

            if not self._validate_file_size(file):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB"
                )

            # 验证实际文件内容大小
            if not await self._validate_file_content(file):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件内容过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB"
                )

        # 创建知识库目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kb_dir = os.path.join(self.knowledge_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(kb_dir, exist_ok=True)

        # 保存知识库基本信息到数据库
        kb_data = {
            "name": name,
            "description": description,
            "uploader_id": uploader_id,
            "copyright_owner": copyright_owner,
            "content": content,
            "tags": tags,
            "base_path": kb_dir,
            "is_pending": True,  # 新上传的内容默认为待审核状态
            "is_public": False   # 新上传的内容默认为非公开
        }

        saved_kb = sqlite_db_manager.save_knowledge_base(kb_data)
        if not saved_kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="知识库保存失败"
            )

        # 保存上传的文件并创建文件记录
        saved_files = []
        for file in files:
            file_path, file_size_b = await self._save_uploaded_file_with_size(file, kb_dir)
            file_ext = os.path.splitext(file.filename)[1].lower()

            # 创建文件记录
            file_data = {
                "knowledge_base_id": saved_kb.id,
                "file_name": file.filename,
                "original_name": file.filename,
                "file_path": os.path.basename(file_path),  # 只存储文件名，相对于知识库目录
                "file_type": file_ext,
                "file_size": file_size_b  # 添加文件大小(B)
            }

            saved_file = sqlite_db_manager.save_knowledge_base_file(file_data)
            if saved_file:
                saved_files.append(saved_file)

        return saved_kb

    async def upload_persona_card(
        self,
        files: List[UploadFile],
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: str,
        content: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> PersonaCard:
        """上传人设卡 - 只处理文件操作，返回PersonaCard对象供调用者保存到数据库"""
        # 验证文件数量
        if len(files) != 1:
            raise ValidationError(
                message="人设卡配置错误：必须且仅包含一个 bot_config.toml 文件",
                details={"code": "PERSONA_FILE_COUNT_INVALID"}
            )

        # 验证文件类型、名称和大小
        for file in files:
            if file.filename != "bot_config.toml":
                raise ValidationError(
                    message="人设卡配置错误：配置文件名必须为 bot_config.toml",
                    details={"code": "PERSONA_FILE_NAME_INVALID", "filename": file.filename}
                )

            if not self._validate_file_type(file, self.ALLOWED_PERSONA_TYPES):
                raise ValidationError(
                    message=f"人设卡配置错误：不支持的文件类型 {file.filename}，仅支持{', '.join(self.ALLOWED_PERSONA_TYPES)} 文件",
                    details={"code": "PERSONA_FILE_TYPE_INVALID", "filename": file.filename}
                )

            if not self._validate_file_size(file):
                raise ValidationError(
                    message=f"人设卡配置错误：文件过大 {file.filename}，单个文件最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                    details={"code": "PERSONA_FILE_SIZE_EXCEEDED", "filename": file.filename}
                )

            # 验证实际文件内容大小
            if not await self._validate_file_content(file):
                raise ValidationError(
                    message=f"人设卡配置错误：文件内容过大 {file.filename}，单个文件最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                    details={"code": "PERSONA_FILE_CONTENT_SIZE_EXCEEDED", "filename": file.filename}
                )

        # 创建人设卡目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pc_dir = os.path.join(self.persona_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(pc_dir, exist_ok=True)

        try:
            persona_version: Optional[str] = None
            
            # 保存上传的文件并解析 TOML 版本号
            for file in files:
                file_path, file_size_b = await self._save_uploaded_file_with_size(file, pc_dir)
                file_ext = os.path.splitext(file.filename)[1].lower()

                if file_ext == ".toml":
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            toml_data = toml.load(f)
                        parsed_version = self._extract_version_from_toml(toml_data)
                        if not parsed_version:
                            raise ValidationError(
                                message="人设卡配置错误：TOML 中未找到版本号字段，请在 bot_config.toml 中添加 version 等版本字段后重试",
                                details={"code": "PERSONA_TOML_VERSION_MISSING"}
                            )
                        persona_version = parsed_version
                    except HTTPException:
                        raise
                    except Exception:
                        raise ValidationError(
                            message="人设卡配置解析失败：TOML 语法错误，请检查 bot_config.toml 格式是否正确",
                            details={"code": "PERSONA_TOML_PARSE_ERROR"}
                        )

            if not persona_version:
                raise ValidationError(
                    message="人设卡配置错误：未能从 TOML 中解析出版本号，请在 bot_config.toml 中添加 version 等版本字段后重试",
                    details={"code": "PERSONA_TOML_VERSION_MISSING"}
                )

            # 创建 PersonaCard 对象（不保存到数据库，由调用者处理）
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
                is_public=False
            )

            return pc
        except Exception as e:
            # 发生任何错误时，清理已创建的目录
            if os.path.exists(pc_dir):
                shutil.rmtree(pc_dir)
            # 重新抛出异常
            raise e

    def get_knowledge_base_content(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库内容"""
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 获取知识库文件列表
        kb_files = sqlite_db_manager.get_files_by_knowledge_base_id(kb_id)

        return {
            "knowledge_base": kb.to_dict(),
            "files": [{
                "file_id": file.id,
                "original_name": file.original_name,
                "file_size": file.file_size,
            } for file in kb_files],
        }

    def get_persona_card_content(self, pc_id: str) -> Dict[str, Any]:
        """获取人设卡内容"""
        pc = sqlite_db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="人设卡不存在"
            )

        # 获取人设卡文件列表
        pc_files = sqlite_db_manager.get_files_by_persona_card_id(pc_id)

        return {
            "persona_card": pc.to_dict(),
            "files": [{
                "file_id": file.id,
                "original_name": file.original_name,
                "file_size": file.file_size,
            } for file in pc_files],
        }

    async def add_files_to_knowledge_base(self, kb_id: str, files: List[UploadFile], user_id: str) -> Optional[KnowledgeBase]:
        """向知识库添加文件"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise ValidationError(
                message="知识库不存在"
            )

        # 获取知识库现有文件
        current_files = sqlite_db_manager.get_files_by_knowledge_base_id(kb_id)
        current_file_count = len(current_files)

        # 检查文件数量限制
        if current_file_count + len(files) > self.MAX_KNOWLEDGE_FILES:
            raise ValidationError(
                message=f"文件数量超过限制，当前{current_file_count}个文件，最多允许{self.MAX_KNOWLEDGE_FILES}个文件"
            )

        # 检查同名文件
        existing_file_names = {file.original_name for file in current_files}
        for file in files:
            if file.filename in existing_file_names:
                raise ValidationError(
                    message=f"文件名已存在: {file.filename}"
                )

        # 验证文件类型和大小
        for file in files:
            if not self._validate_file_type(file, self.ALLOWED_KNOWLEDGE_TYPES):
                raise ValidationError(
                    message=f"不支持的文件类型: {file.filename}。仅支持{', '.join(self.ALLOWED_KNOWLEDGE_TYPES)}文件"
                )

            if not self._validate_file_size(file):
                raise ValidationError(
                    message=f"文件过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB"
                )

            # 验证实际文件内容大小
            if not await self._validate_file_content(file):
                raise ValidationError(
                    message=f"文件内容过大: {file.filename}。最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB"
                )

        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="知识库目录不存在"
            )

        # 保存新文件并创建文件记录
        saved_files = []
        for file in files:
            file_path, file_size_b = await self._save_uploaded_file_with_size(file, kb_dir)
            file_ext = os.path.splitext(file.filename)[1].lower()

            # 创建文件记录
            file_data = {
                "knowledge_base_id": kb_id,
                "file_name": file.filename,
                "original_name": file.filename,
                "file_path": os.path.basename(file_path),  # 只存储文件名，相对于知识库目录
                "file_type": file_ext,
                "file_size": file_size_b  # 添加文件大小(B)
            }

            saved_file = sqlite_db_manager.save_knowledge_base_file(file_data)
            if saved_file:
                saved_files.append(saved_file)

        # 更新知识库时间戳
        kb.updated_at = datetime.now()
        updated_kb = sqlite_db_manager.save_knowledge_base(kb.to_dict())

        return updated_kb

    async def delete_files_from_knowledge_base(self, kb_id: str, file_id: str, user_id: str) -> bool:
        """从知识库删除文件"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 获取要删除的文件
        kb_file = sqlite_db_manager.get_knowledge_base_file_by_id(file_id)
        if not kb_file or kb_file.knowledge_base_id != kb_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )

        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="知识库目录不存在"
            )

        # 删除文件和文件记录
        try:
            # 删除物理文件
            file_full_path = os.path.join(kb_dir, kb_file.file_path)
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

            # 删除数据库记录
            sqlite_db_manager.delete_knowledge_base_file(kb_file.id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文件失败 {kb_file.original_name}: {str(e)}"
            )

        # 更新知识库时间戳
        kb.updated_at = datetime.now()
        sqlite_db_manager.save_knowledge_base(kb.to_dict())

        return True

    async def delete_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """删除整个知识库"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            return False

        # 获取知识库目录
        kb_dir = kb.base_path
        if kb_dir and os.path.exists(kb_dir):
            try:
                # 删除整个知识库目录
                shutil.rmtree(kb_dir)
            except Exception as e:
                # 记录删除失败但继续处理
                print(f"删除知识库目录失败 {kb_dir}: {str(e)}")
                return False

        # 删除数据库中的文件记录（在delete_knowledge_base方法中已经处理）
        return True

    async def create_knowledge_base_zip(self, kb_id: str) -> dict:
        """创建知识库的ZIP文件，返回ZIP文件路径和文件名"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 获取知识库文件列表
        kb_files = sqlite_db_manager.get_files_by_knowledge_base_id(kb_id)

        # 获取上传者信息
        uploader = sqlite_db_manager.get_user_by_id(kb.uploader_id)
        uploader_name = uploader.username if uploader else "未知用户"

        # 检查文件是否存在
        missing_files = []
        for kb_file in kb_files:
            file_full_path = os.path.join(kb.base_path, kb_file.file_path)
            if not os.path.exists(file_full_path):
                missing_files.append(kb_file.original_name)

        if missing_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"以下文件不存在: {', '.join(missing_files)}"
            )

        # 创建临时ZIP文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{kb.name}-{uploader_name}_{timestamp}.zip"
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, zip_filename)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加知识库文件
                for kb_file in kb_files:
                    file_full_path = os.path.join(
                        kb.base_path, kb_file.file_path)
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
                    file_size_b = kb_file.file_size or 0  # 使用数据库中的文件大小(B)
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建压缩包失败: {str(e)}"
            )

    async def get_knowledge_base_file_path(self, kb_id: str, file_id: str) -> dict:
        """获取知识库中指定文件的完整路径"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            return None

        # 查找文件
        kb_files = sqlite_db_manager.get_knowledge_base_file_by_id(file_id)
        if not kb_files:
            return None
        else:
            return {
                "file_name": kb_files.original_name,
                "file_path": kb_files.file_path
            }

    async def add_files_to_persona_card(self, pc_id: str, files: List[UploadFile]) -> Optional[PersonaCard]:
        """向人设卡添加文件"""
        # 获取人设卡信息
        pc = sqlite_db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            return None

        # 只允许一次上传一个文件
        if len(files) != 1:
            raise ValidationError(
                message="人设卡配置错误：一次仅支持上传一个 bot_config.toml 文件",
                details={"code": "PERSONA_FILE_COUNT_INVALID"}
            )

        # 验证文件类型、名称和大小
        for file in files:
            if file.filename != "bot_config.toml":
                raise ValidationError(
                    message=f"人设卡配置错误：文件名必须为 bot_config.toml，当前为 {file.filename}",
                    details={"code": "PERSONA_FILE_NAME_INVALID", "filename": file.filename}
                )

            if not self._validate_file_type(file, self.ALLOWED_PERSONA_TYPES):
                raise ValidationError(
                    message=f"人设卡配置错误：不支持的文件类型 {file.filename}，仅支持{', '.join(self.ALLOWED_PERSONA_TYPES)} 文件",
                    details={"code": "PERSONA_FILE_TYPE_INVALID", "filename": file.filename}
                )

            if not self._validate_file_size(file):
                raise ValidationError(
                    message=f"人设卡配置错误：文件过大 {file.filename}，单个文件最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                    details={"code": "PERSONA_FILE_SIZE_EXCEEDED", "filename": file.filename}
                )

            # 验证实际文件内容大小
            if not await self._validate_file_content(file):
                raise ValidationError(
                    message=f"人设卡配置错误：文件内容过大 {file.filename}，单个文件最大允许{self.MAX_FILE_SIZE // (1024*1024)}MB",
                    details={"code": "PERSONA_FILE_CONTENT_SIZE_EXCEEDED", "filename": file.filename}
                )

        # 获取人设卡目录
        pc_dir = pc.base_path  # 人设卡主文件所在目录
        if not pc_dir or not os.path.exists(pc_dir):
            raise DatabaseError(
                message="人设卡目录不存在，请稍后重试或联系管理员"
            )

        # 保存新文件并创建文件记录，同时校验 TOML 版本号
        new_file = files[0]
        persona_version: Optional[str] = None
        file_path, file_size_b = await self._save_uploaded_file_with_size(new_file, pc_dir)
        file_ext = os.path.splitext(new_file.filename)[1].lower()

        try:
            if file_ext == ".toml":
                with open(file_path, "r", encoding="utf-8") as f:
                    toml_data = toml.load(f)
                parsed_version = self._extract_version_from_toml(toml_data)
                if not parsed_version:
                    raise ValidationError(
                        message="人设卡配置错误：TOML 中未找到版本号字段，请在 bot_config.toml 中添加 version 等版本字段后重试",
                        details={"code": "PERSONA_TOML_VERSION_MISSING"}
                    )
                persona_version = parsed_version

            # 创建新文件记录
            file_data = {
                "persona_card_id": pc_id,
                "file_name": new_file.filename,
                "original_name": new_file.filename,
                "file_path": os.path.basename(file_path),  # 只存储文件名，相对于人设卡目录
                "file_type": file_ext,
                "file_size": file_size_b  # 添加文件大小(B)
            }

            saved_file = sqlite_db_manager.save_persona_card_file(file_data)
            if not saved_file:
                raise DatabaseError(
                    message="人设卡文件保存失败，请稍后重试或联系管理员"
                )

            # 新文件保存成功后，删除旧文件及记录（实现“替换”）
            for old_file in current_files:
                try:
                    old_full_path = os.path.join(pc_dir, old_file.file_path)
                    if os.path.exists(old_full_path):
                        os.remove(old_full_path)
                    sqlite_db_manager.delete_persona_card_file(old_file.id)
                except Exception as e:
                    raise DatabaseError(
                        message=f"删除旧人设卡文件失败：{old_file.original_name}，请稍后重试或联系管理员"
                    )

            # 更新人设卡时间戳和版本号（使用新文件的版本）
            pc.updated_at = datetime.now()
            if persona_version:
                pc.version = persona_version
            updated_pc = sqlite_db_manager.save_persona_card(pc.to_dict())

            return updated_pc
        except HTTPException:
            # 删除新文件，保留旧文件不变
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValidationError(
                message="人设卡配置解析失败：TOML 语法错误，请检查 bot_config.toml 格式是否正确",
                details={"code": "PERSONA_TOML_PARSE_ERROR"}
            )

    async def delete_files_from_persona_card(self, pc_id: str, file_id: str, user_id: str) -> bool:
        """从人设卡删除文件"""
        # 获取人设卡信息
        pc = sqlite_db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            return False

        # 获取要删除的文件
        pc_file = sqlite_db_manager.get_persona_card_file_by_id(file_id)

        # 获取人设卡目录
        pc_dir = pc.base_path  # 人设卡主文件所在目录
        if not pc_dir or not os.path.exists(pc_dir):
            return False

        # 删除文件和文件记录
        try:
            # 删除物理文件
            file_full_path = os.path.join(pc_dir, pc_file.file_path)
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

            # 删除数据库记录
            sqlite_db_manager.delete_persona_card_file(pc_file.id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文件失败 {pc_file.original_name}: {str(e)}"
            )

        return True

    async def get_persona_card_file_path(self, pc_id: str, file_id: str) -> dict:
        """获取人设卡中指定文件的信息"""
        # 获取人设卡信息
        pc = sqlite_db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            return None

        # 查找文件
        pc_file = sqlite_db_manager.get_persona_card_file_by_id(file_id)
        if not pc_file:
            return None
        else:
            return {
                "file_id": pc_file.id,
                "file_name": pc_file.original_name,
                "file_path": pc_file.file_path
            }

    async def create_persona_card_zip(self, pc_id: str) -> dict:
        """创建人设卡的ZIP文件，返回ZIP文件路径和文件名"""
        # 获取人设卡信息
        pc = sqlite_db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="人设卡不存在"
            )

        # 获取人设卡文件列表
        pc_files = sqlite_db_manager.get_persona_card_files_by_persona_card_id(
            pc_id)

        # 获取上传者信息
        uploader = sqlite_db_manager.get_user_by_id(pc.uploader_id)
        uploader_name = uploader.username if uploader else "未知用户"

        # 检查文件是否存在
        missing_files = []
        for pc_file in pc_files:
            file_full_path = os.path.join(pc.base_path, pc_file.file_path)
            if not os.path.exists(file_full_path):
                missing_files.append(pc_file.original_name)

        if missing_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"以下文件不存在: {', '.join(missing_files)}"
            )

        # 创建临时ZIP文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{pc.name}-{uploader_name}_{timestamp}.zip"
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, zip_filename)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加人设卡文件
                for pc_file in pc_files:
                    file_full_path = os.path.join(
                        pc.base_path, pc_file.file_path)
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
                    file_size_b = pc_file.file_size or 0  # 使用数据库中的文件大小(B)
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建压缩包失败: {str(e)}"
            )


# 创建全局文件上传服务实例
file_upload_service = FileUploadService()
