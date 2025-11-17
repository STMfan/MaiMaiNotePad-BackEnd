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

from models import (
    KnowledgeBase, PersonaCard, KnowledgeBaseFile
)
from database_models import sqlite_db_manager


class FileUploadService:
    """文件上传服务"""
    
    # 配置常量
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_KNOWLEDGE_FILES = 5  # 知识库最多文件数
    MAX_PERSONA_FILES = 2  # 人设卡最多文件数
    ALLOWED_KNOWLEDGE_TYPES = ['.txt', '.json']  # 知识库允许的文件类型
    ALLOWED_PERSONA_TYPES = ['.toml']  # 人设卡允许的文件类型
    
    def __init__(self):
        # 确保上传目录存在
        self.upload_dir = "./uploads"
        self.knowledge_dir = "uploads/knowledge"
        self.persona_dir = "uploads/persona"
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
        copyright_owner: Optional[str] = None
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
            "base_path": kb_dir
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

        # 创建元数据
        metadata = {
            "name": name,
            "description": description,
            "uploader_id": uploader_id,
            "copyright_owner": copyright_owner,
            "files": [file.to_dict() for file in saved_files],
            "created_at": datetime.now().isoformat()
        }

        # 保存元数据文件
        metadata_path = self._create_metadata_file(metadata, kb_dir, "kb")
        
        # 更新知识库的元数据路径
        saved_kb.metadata_path = metadata_path
        sqlite_db_manager.save_knowledge_base(saved_kb.to_dict())
        
        return saved_kb
    
    async def upload_persona_card(
        self, 
        files: List[UploadFile], 
        name: str,
        description: str,
        uploader_id: str,
        copyright_owner: Optional[str] = None
    ) -> PersonaCard:
        """上传人设卡"""
        # 验证文件数量
        if len(files) < 1 or len(files) > self.MAX_PERSONA_FILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"人设卡必须包含1-{self.MAX_PERSONA_FILES}个.toml文件"
            )
        
        # 验证文件类型和大小
        for file in files:
            if not self._validate_file_type(file, self.ALLOWED_PERSONA_TYPES):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的文件类型: {file.filename}。人设卡仅支持{', '.join(self.ALLOWED_PERSONA_TYPES)}文件"
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
        
        # 创建人设卡目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pc_dir = os.path.join(self.persona_dir, f"{uploader_id}_{timestamp}")
        os.makedirs(pc_dir, exist_ok=True)
        
        # 保存上传的文件
        file_paths = []
        for file in files:
            file_path = await self._save_uploaded_file(file, pc_dir)
            file_paths.append(file_path)
        
        # 创建元数据
        metadata = {
            "name": name,
            "description": description,
            "uploader_id": uploader_id,
            "copyright_owner": copyright_owner,
            "files": [os.path.basename(path) for path in file_paths],
            "created_at": datetime.now().isoformat()
        }
        
        # 保存元数据文件
        metadata_path = self._create_metadata_file(metadata, pc_dir, "pc")
        
        # 创建人设卡对象
        pc = PersonaCard(
            name=name,
            description=description,
            uploader_id=uploader_id,
            copyright_owner=copyright_owner,
            file_paths=file_paths,
            metadata_path=metadata_path
        )
        
        # 保存到数据库
        updated_pc = sqlite_db_manager.save_persona_card(pc)
        if not updated_pc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="人设卡保存失败"
            )
        
        return updated_pc
    
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
                "file_size": file.file_size,  # 添加文件大小(B)
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
        
        # 读取元数据
        try:
            with open(pc.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"读取元数据失败: {str(e)}"
            )
        
        # 读取文件内容
        files_content = {}
        for file_path in pc.file_paths:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content[os.path.basename(file_path)] = f.read()
                except Exception as e:
                    files_content[os.path.basename(file_path)] = f"读取文件失败: {str(e)}"
            else:
                files_content[os.path.basename(file_path)] = "文件不存在"
        
        return {
            "persona_card": pc.to_dict(),
            "metadata": metadata,
            "files_content": files_content
        }
    
    async def add_files_to_knowledge_base(self, kb_id: str, files: List[UploadFile], user_id: str) -> Optional[KnowledgeBase]:
        """向知识库添加文件"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            return None
        
        # 获取知识库现有文件
        current_files = sqlite_db_manager.get_files_by_knowledge_base_id(kb_id)
        current_file_count = len(current_files)
        
        # 检查文件数量限制
        if current_file_count + len(files) > self.MAX_KNOWLEDGE_FILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件数量超过限制，当前{current_file_count}个文件，最多允许{self.MAX_KNOWLEDGE_FILES}个文件"
            )
        
        # 检查同名文件
        existing_file_names = {file.original_name for file in current_files}
        for file in files:
            if file.filename in existing_file_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件名已存在: {file.filename}"
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
        
        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="知识库目录不存在"
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
        
        # 更新元数据文件
        try:
            with open(kb.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 获取最新的文件列表
            all_files = sqlite_db_manager.get_files_by_knowledge_base_id(kb_id)
            metadata["files"] = [file.to_dict() for file in all_files]
            metadata["updated_at"] = datetime.now().isoformat()
            
            with open(kb.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新元数据失败: {str(e)}"
            )
        
        # 更新知识库时间戳
        kb.updated_at = datetime.now()
        updated_kb = sqlite_db_manager.save_knowledge_base(kb.to_dict())
        
        return updated_kb
    
    async def delete_files_from_knowledge_base(self, kb_id: str, file_id: str, user_id: str) -> bool:
        """从知识库删除文件"""
        # 获取知识库信息
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            return False
        
        # 获取要删除的文件
        kb_file = sqlite_db_manager.get_knowledge_base_file_by_id(file_id)
        
        # 获取知识库目录
        kb_dir = kb.base_path
        if not kb_dir or not os.path.exists(kb_dir):
            return False
        
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
        
        # 更新元数据文件
        try:
            with open(kb.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 获取最新的文件列表
            remaining_files = sqlite_db_manager.get_files_by_knowledge_base_id(kb_id)
            metadata["files"] = [file.to_dict() for file in remaining_files]
            metadata["updated_at"] = datetime.now().isoformat()
            
            with open(kb.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新元数据失败: {str(e)}"
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
                    file_full_path = os.path.join(kb.base_path, kb_file.file_path)
                    zipf.write(file_full_path, kb_file.original_name)
                
                # 不再添加kb_metadata.json文件，根据用户需求排除
                
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


# 创建全局文件上传服务实例
file_upload_service = FileUploadService()