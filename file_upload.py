"""
文件上传功能实现
支持txt、json、toml格式文件的上传和管理
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel
import toml
import json

from models import (
    KnowledgeBase, PersonaCard
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
        
        # 保存上传的文件
        file_paths = []
        for file in files:
            file_path = await self._save_uploaded_file(file, kb_dir)
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
        metadata_path = self._create_metadata_file(metadata, kb_dir, "kb")
        
        # 创建知识库对象
        kb = KnowledgeBase(
            name=name,
            description=description,
            uploader_id=uploader_id,
            copyright_owner=copyright_owner,
            file_paths=file_paths,
            metadata_path=metadata_path
        )
        
        # 保存到数据库
        if not sqlite_db_manager.save_knowledge_base(kb):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="知识库保存失败"
            )
        
        return kb
    
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
        if not sqlite_db_manager.save_persona_card(pc):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="人设卡保存失败"
            )
        
        return pc
    
    def get_knowledge_base_content(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库内容"""
        kb = sqlite_db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )
        
        # 读取元数据
        try:
            with open(kb.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"读取元数据失败: {str(e)}"
            )
        
        # 读取文件内容
        files_content = {}
        for file_path in kb.file_paths:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content[os.path.basename(file_path)] = f.read()
                except Exception as e:
                    files_content[os.path.basename(file_path)] = f"读取文件失败: {str(e)}"
            else:
                files_content[os.path.basename(file_path)] = "文件不存在"
        
        return {
            "knowledge_base": kb.dict(),
            "metadata": metadata,
            "files_content": files_content
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
            "persona_card": pc.dict(),
            "metadata": metadata,
            "files_content": files_content
        }


# 创建全局文件上传服务实例
file_upload_service = FileUploadService()