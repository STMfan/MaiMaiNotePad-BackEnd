"""
Knowledge base service module
Contains business logic for knowledge base management
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.database import KnowledgeBase, KnowledgeBaseFile, User, UploadRecord

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Service class for knowledge base management operations.
    Handles knowledge base CRUD operations, approval, star, and download functionality.
    """

    def __init__(self, db: Session):
        """
        Initialize KnowledgeService with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_knowledge_base_by_id(self, kb_id: str, include_files: bool = False) -> Optional[KnowledgeBase]:
        """
        Get knowledge base by ID.
        
        Args:
            kb_id: Knowledge base ID
            include_files: Whether to include file information
            
        Returns:
            KnowledgeBase object if found, None otherwise
        """
        try:
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            return kb
        except Exception as e:
            logger.error(f'Error getting knowledge base by ID {kb_id}: {str(e)}')
            return None

    def get_public_knowledge_bases(
        self,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        uploader_id: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        Get public knowledge bases with pagination, search, and sorting.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            name: Search by name (optional)
            uploader_id: Filter by uploader ID (optional)
            sort_by: Sort field (created_at, updated_at, star_count)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Tuple of (list of KnowledgeBase objects, total count)
        """
        try:
            query = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.is_public == True,
                KnowledgeBase.is_pending == False
            )

            # Apply filters
            if name:
                query = query.filter(KnowledgeBase.name.ilike(f"%{name}%"))
            
            if uploader_id:
                query = query.filter(KnowledgeBase.uploader_id == uploader_id)

            # Get total count before pagination
            total = query.count()

            # Apply sorting
            sort_field_map = {
                "created_at": KnowledgeBase.created_at,
                "updated_at": KnowledgeBase.updated_at,
                "star_count": KnowledgeBase.star_count
            }
            sort_field = sort_field_map.get(sort_by, KnowledgeBase.created_at)
            
            if sort_order.lower() == "asc":
                query = query.order_by(sort_field.asc())
            else:
                query = query.order_by(sort_field.desc())

            # Apply pagination
            offset = (page - 1) * page_size
            kbs = query.offset(offset).limit(page_size).all()

            return kbs, total
        except Exception as e:
            logger.error(f'Error getting public knowledge bases: {str(e)}')
            return [], 0

    def get_user_knowledge_bases(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        status: str = "all",
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        Get knowledge bases uploaded by a specific user.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            name: Search by name (optional)
            tag: Search by tag (optional)
            status: Status filter (all/pending/approved/rejected)
            sort_by: Sort field (created_at/updated_at/name/downloads/star_count)
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (list of KnowledgeBase objects, total count)
        """
        try:
            kbs = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.uploader_id == user_id
            ).all()

            # Filter by status
            def match_status(kb):
                if status == "pending":
                    return kb.is_pending
                if status == "approved":
                    return not kb.is_pending and kb.is_public
                if status == "rejected":
                    return not kb.is_pending and (not kb.is_public)
                return True

            # Apply filters
            filtered = []
            for kb in kbs:
                if name and name.lower() not in kb.name.lower():
                    continue
                if tag:
                    tag_list = []
                    if kb.tags:
                        tag_list = kb.tags.split(",") if isinstance(kb.tags, str) else kb.tags
                    if not any(tag.lower() in t.lower() for t in tag_list):
                        continue
                if not match_status(kb):
                    continue
                filtered.append(kb)

            # Sort
            sort_field_map = {
                "created_at": lambda kb: kb.created_at,
                "updated_at": lambda kb: kb.updated_at,
                "name": lambda kb: kb.name.lower(),
                "downloads": lambda kb: kb.downloads or 0,
                "star_count": lambda kb: kb.star_count or 0,
            }
            key_func = sort_field_map.get(sort_by, sort_field_map["created_at"])
            reverse = sort_order.lower() != "asc"
            filtered.sort(key=key_func, reverse=reverse)

            total = len(filtered)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = filtered[start:end]

            return page_items, total
        except Exception as e:
            logger.error(f'Error getting user knowledge bases for user {user_id}: {str(e)}')
            return [], 0

    def save_knowledge_base(self, kb_data: Dict[str, Any]) -> Optional[KnowledgeBase]:
        """
        Save or update knowledge base.
        
        Args:
            kb_data: Dictionary containing knowledge base data
            
        Returns:
            KnowledgeBase object if successful, None otherwise
        """
        try:
            kb_id = kb_data.get("id")
            
            if kb_id:
                # Update existing knowledge base
                kb = self.get_knowledge_base_by_id(kb_id)
                if not kb:
                    return None
                
                for key, value in kb_data.items():
                    if hasattr(kb, key) and key not in ["id", "created_at"]:
                        setattr(kb, key, value)
            else:
                # Create new knowledge base
                kb = KnowledgeBase(**kb_data)
                self.db.add(kb)
            
            self.db.commit()
            self.db.refresh(kb)
            
            logger.info(f'Knowledge base saved: kb_id={kb.id}')
            return kb
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error saving knowledge base: {str(e)}')
            return None

    def check_duplicate_name(self, user_id: str, name: str, exclude_kb_id: Optional[str] = None) -> bool:
        """
        Check if user already has a knowledge base with the same name.
        
        Args:
            user_id: User ID
            name: Knowledge base name
            exclude_kb_id: KB ID to exclude from check (for updates)
            
        Returns:
            True if duplicate exists, False otherwise
        """
        try:
            query = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.uploader_id == user_id,
                KnowledgeBase.name == name
            )
            
            if exclude_kb_id:
                query = query.filter(KnowledgeBase.id != exclude_kb_id)
            
            return query.first() is not None
        except Exception as e:
            logger.error(f'Error checking duplicate name: {str(e)}')
            return False

    def update_knowledge_base(
        self,
        kb_id: str,
        update_data: Dict[str, Any],
        user_id: str,
        is_admin: bool = False,
        is_moderator: bool = False
    ) -> Tuple[bool, str, Optional[KnowledgeBase]]:
        """
        Update knowledge base information.
        
        Args:
            kb_id: Knowledge base ID
            update_data: Dictionary of fields to update
            user_id: User ID making the update
            is_admin: Whether user is admin
            is_moderator: Whether user is moderator
            
        Returns:
            Tuple of (success: bool, message: str, kb: Optional[KnowledgeBase])
        """
        try:
            kb = self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return False, "知识库不存在", None

            # Check permissions
            if kb.uploader_id != user_id and not is_admin and not is_moderator:
                return False, "是你的知识库吗你就改", None

            # Restrict updates for public or pending knowledge bases
            if kb.is_public or kb.is_pending:
                allowed_fields = {"content"}
                disallowed_fields = [key for key in update_data.keys() if key not in allowed_fields]
                if disallowed_fields:
                    return False, "公开或审核中的知识库仅允许修改补充说明", None

            # Remove protected fields
            update_data.pop("copyright_owner", None)
            update_data.pop("name", None)

            # Check is_public permission
            if not (kb.is_public or kb.is_pending):
                if "is_public" in update_data and not (is_admin or is_moderator):
                    return False, "只有管理员可以直接修改公开状态", None

            # Apply updates
            for key, value in update_data.items():
                if hasattr(kb, key):
                    setattr(kb, key, value)

            # Update timestamp if non-content fields changed
            if any(field != "content" for field in update_data.keys()):
                kb.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(kb)

            logger.info(f'Knowledge base updated: kb_id={kb_id}, user_id={user_id}')
            return True, "修改知识库成功", kb
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error updating knowledge base {kb_id}: {str(e)}')
            return False, "修改知识库失败", None

    def delete_knowledge_base(self, kb_id: str) -> bool:
        """
        Delete knowledge base from database.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            kb = self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return False

            self.db.delete(kb)
            self.db.commit()

            logger.info(f'Knowledge base deleted: kb_id={kb_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error deleting knowledge base {kb_id}: {str(e)}')
            return False

    def is_starred(self, user_id: str, kb_id: str) -> bool:
        """
        Check if knowledge base is starred by user.
        
        Args:
            user_id: User ID
            kb_id: Knowledge base ID
            
        Returns:
            True if starred, False otherwise
        """
        try:
            from app.models.database import StarRecord
            record = self.db.query(StarRecord).filter(
                StarRecord.user_id == user_id,
                StarRecord.target_id == kb_id,
                StarRecord.target_type == "knowledge"
            ).first()
            return record is not None
        except Exception as e:
            logger.error(f'Error checking star status: {str(e)}')
            return False

    def add_star(self, user_id: str, kb_id: str) -> bool:
        """
        Add star to knowledge base.
        
        Args:
            user_id: User ID
            kb_id: Knowledge base ID
            
        Returns:
            True if successful, False if already starred
        """
        try:
            # Check if already starred
            if self.is_starred(user_id, kb_id):
                return False

            from app.models.database import StarRecord
            import uuid
            
            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_id=kb_id,
                target_type="knowledge",
                created_at=datetime.now()
            )
            self.db.add(star)

            # Increment star count
            kb = self.get_knowledge_base_by_id(kb_id)
            if kb:
                kb.star_count = (kb.star_count or 0) + 1

            self.db.commit()

            logger.info(f'Star added: user_id={user_id}, kb_id={kb_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error adding star: {str(e)}')
            return False

    def remove_star(self, user_id: str, kb_id: str) -> bool:
        """
        Remove star from knowledge base.
        
        Args:
            user_id: User ID
            kb_id: Knowledge base ID
            
        Returns:
            True if successful, False if not starred
        """
        try:
            from app.models.database import StarRecord
            
            star = self.db.query(StarRecord).filter(
                StarRecord.user_id == user_id,
                StarRecord.target_id == kb_id,
                StarRecord.target_type == "knowledge"
            ).first()

            if not star:
                return False

            self.db.delete(star)

            # Decrement star count
            kb = self.get_knowledge_base_by_id(kb_id)
            if kb and kb.star_count > 0:
                kb.star_count = kb.star_count - 1

            self.db.commit()

            logger.info(f'Star removed: user_id={user_id}, kb_id={kb_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error removing star: {str(e)}')
            return False

    def increment_downloads(self, kb_id: str) -> bool:
        """
        Increment download count for knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            kb = self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return False

            kb.downloads = (kb.downloads or 0) + 1
            self.db.commit()

            logger.info(f'Download count incremented: kb_id={kb_id}, count={kb.downloads}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error incrementing downloads for {kb_id}: {str(e)}')
            return False

    def get_files_by_knowledge_base_id(self, kb_id: str) -> List[KnowledgeBaseFile]:
        """
        Get all files for a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            List of KnowledgeBaseFile objects
        """
        try:
            files = self.db.query(KnowledgeBaseFile).filter(
                KnowledgeBaseFile.knowledge_base_id == kb_id
            ).all()
            return files
        except Exception as e:
            logger.error(f'Error getting files for knowledge base {kb_id}: {str(e)}')
            return []

    def create_upload_record(
        self,
        uploader_id: str,
        target_id: str,
        name: str,
        description: str,
        status: str = "success"
    ) -> Optional[str]:
        """
        Create upload record for knowledge base.
        
        Args:
            uploader_id: Uploader user ID
            target_id: Knowledge base ID
            name: Knowledge base name
            description: Knowledge base description
            status: Upload status (success/pending)
            
        Returns:
            Upload record ID if successful, None otherwise
        """
        try:
            import uuid
            
            record = UploadRecord(
                id=str(uuid.uuid4()),
                uploader_id=uploader_id,
                target_id=target_id,
                target_type="knowledge",
                name=name,
                description=description,
                status=status,
                created_at=datetime.now()
            )
            self.db.add(record)
            self.db.commit()

            logger.info(f'Upload record created: target_id={target_id}, status={status}')
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error creating upload record: {str(e)}')
            return None

    def delete_upload_records_by_target(self, target_id: str) -> bool:
        """
        Delete upload records for a knowledge base.
        
        Args:
            target_id: Knowledge base ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.db.query(UploadRecord).filter(
                UploadRecord.target_id == target_id,
                UploadRecord.target_type == "knowledge"
            ).delete()
            self.db.commit()

            logger.info(f'Upload records deleted: target_id={target_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error deleting upload records for {target_id}: {str(e)}')
            return False

    def resolve_uploader_id(self, uploader_identifier: str) -> Optional[str]:
        """
        Resolve uploader identifier to user ID.
        Accepts either user ID or username.
        
        Args:
            uploader_identifier: User ID or username
            
        Returns:
            User ID if found, None otherwise
        """
        try:
            # Try to find by ID first
            user = self.db.query(User).filter(User.id == uploader_identifier).first()
            if user:
                return user.id
            
            # Try to find by username
            user = self.db.query(User).filter(User.username == uploader_identifier).first()
            if user:
                return user.id
            
            return None
        except Exception as e:
            logger.error(f'Error resolving uploader identifier {uploader_identifier}: {str(e)}')
            return None
