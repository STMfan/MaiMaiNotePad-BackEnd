"""
Persona card service module
Contains business logic for persona card management
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.database import PersonaCard, PersonaCardFile, User, UploadRecord

logger = logging.getLogger(__name__)


class PersonaService:
    """
    Service class for persona card management operations.
    Handles persona card CRUD operations, approval, star, and download functionality.
    """

    def __init__(self, db: Session):
        """
        Initialize PersonaService with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_persona_card_by_id(self, pc_id: str, include_files: bool = False) -> Optional[PersonaCard]:
        """
        Get persona card by ID.
        
        Args:
            pc_id: Persona card ID
            include_files: Whether to include file information
            
        Returns:
            PersonaCard object if found, None otherwise
        """
        try:
            pc = self.db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
            return pc
        except Exception as e:
            logger.error(f'Error getting persona card by ID {pc_id}: {str(e)}')
            return None

    def get_all_persona_cards(self) -> List[PersonaCard]:
        """
        Get all persona cards.
        
        Returns:
            List of PersonaCard objects
        """
        try:
            pcs = self.db.query(PersonaCard).all()
            return pcs
        except Exception as e:
            logger.error(f'Error getting all persona cards: {str(e)}')
            return []

    def get_public_persona_cards(
        self,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        uploader_id: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[PersonaCard], int]:
        """
        Get public persona cards with pagination, search, and sorting.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            name: Search by name (optional)
            uploader_id: Filter by uploader ID (optional)
            sort_by: Sort field (created_at, updated_at, star_count)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Tuple of (list of PersonaCard objects, total count)
        """
        try:
            query = self.db.query(PersonaCard).filter(
                PersonaCard.is_public == True,
                PersonaCard.is_pending == False
            )

            # Apply filters
            if name:
                query = query.filter(PersonaCard.name.ilike(f"%{name}%"))
            
            if uploader_id:
                query = query.filter(PersonaCard.uploader_id == uploader_id)

            # Get total count before pagination
            total = query.count()

            # Apply sorting
            sort_field_map = {
                "created_at": PersonaCard.created_at,
                "updated_at": PersonaCard.updated_at,
                "star_count": PersonaCard.star_count
            }
            sort_field = sort_field_map.get(sort_by, PersonaCard.created_at)
            
            if sort_order.lower() == "asc":
                query = query.order_by(sort_field.asc())
            else:
                query = query.order_by(sort_field.desc())

            # Apply pagination
            offset = (page - 1) * page_size
            pcs = query.offset(offset).limit(page_size).all()

            return pcs, total
        except Exception as e:
            logger.error(f'Error getting public persona cards: {str(e)}')
            return [], 0

    def get_user_persona_cards(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        status: str = "all",
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[PersonaCard], int]:
        """
        Get persona cards uploaded by a specific user.
        
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
            Tuple of (list of PersonaCard objects, total count)
        """
        try:
            pcs = self.db.query(PersonaCard).filter(
                PersonaCard.uploader_id == user_id
            ).all()

            # Filter by status
            def match_status(pc):
                if status == "pending":
                    return pc.is_pending
                if status == "approved":
                    return not pc.is_pending and pc.is_public
                if status == "rejected":
                    return not pc.is_pending and (not pc.is_public)
                return True

            # Apply filters
            filtered = []
            for pc in pcs:
                if name and name.lower() not in pc.name.lower():
                    continue
                if tag:
                    tag_list = []
                    if pc.tags:
                        tag_list = pc.tags.split(",") if isinstance(pc.tags, str) else pc.tags
                    if not any(tag.lower() in t.lower() for t in tag_list):
                        continue
                if not match_status(pc):
                    continue
                filtered.append(pc)

            # Sort
            sort_field_map = {
                "created_at": lambda pc: pc.created_at,
                "updated_at": lambda pc: pc.updated_at,
                "name": lambda pc: pc.name.lower(),
                "downloads": lambda pc: pc.downloads or 0,
                "star_count": lambda pc: pc.star_count or 0,
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
            logger.error(f'Error getting user persona cards for user {user_id}: {str(e)}')
            return [], 0

    def save_persona_card(self, pc_data: Dict[str, Any]) -> Optional[PersonaCard]:
        """
        Save or update persona card.
        
        Args:
            pc_data: Dictionary containing persona card data
            
        Returns:
            PersonaCard object if successful, None otherwise
        """
        try:
            pc_id = pc_data.get("id")
            
            if pc_id:
                # Update existing persona card
                pc = self.get_persona_card_by_id(pc_id)
                if not pc:
                    return None
                
                for key, value in pc_data.items():
                    if hasattr(pc, key) and key not in ["id", "created_at"]:
                        setattr(pc, key, value)
            else:
                # Create new persona card
                pc = PersonaCard(**pc_data)
                self.db.add(pc)
            
            self.db.commit()
            self.db.refresh(pc)
            
            logger.info(f'Persona card saved: pc_id={pc.id}')
            return pc
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error saving persona card: {str(e)}')
            return None

    def update_persona_card(
        self,
        pc_id: str,
        update_data: Dict[str, Any],
        user_id: str,
        is_admin: bool = False,
        is_moderator: bool = False
    ) -> Tuple[bool, str, Optional[PersonaCard]]:
        """
        Update persona card information.
        
        Args:
            pc_id: Persona card ID
            update_data: Dictionary of fields to update
            user_id: User ID making the update
            is_admin: Whether user is admin
            is_moderator: Whether user is moderator
            
        Returns:
            Tuple of (success: bool, message: str, pc: Optional[PersonaCard])
        """
        try:
            pc = self.get_persona_card_by_id(pc_id)
            if not pc:
                return False, "人设卡不存在", None

            # Check permissions
            if pc.uploader_id != user_id and not is_admin and not is_moderator:
                return False, "没有权限修改此人设卡", None

            # Restrict updates for public or pending persona cards
            if pc.is_public or pc.is_pending:
                allowed_fields = {"content"}
                disallowed_fields = [key for key in update_data.keys() if key not in allowed_fields]
                if disallowed_fields:
                    return False, "公开或审核中的人设卡仅允许修改补充说明", None

            # Remove protected fields
            update_data.pop("copyright_owner", None)
            update_data.pop("name", None)

            # Check is_public permission
            if not (pc.is_public or pc.is_pending):
                if "is_public" in update_data and not (is_admin or is_moderator):
                    return False, "只有管理员可以直接修改公开状态", None

            # Apply updates
            for key, value in update_data.items():
                if hasattr(pc, key):
                    setattr(pc, key, value)

            # Update timestamp if non-content fields changed
            if any(field != "content" for field in update_data.keys()):
                pc.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(pc)

            logger.info(f'Persona card updated: pc_id={pc_id}, user_id={user_id}')
            return True, "人设卡更新成功", pc
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error updating persona card {pc_id}: {str(e)}')
            return False, "修改人设卡失败", None

    def delete_persona_card(self, pc_id: str) -> bool:
        """
        Delete persona card from database.
        
        Args:
            pc_id: Persona card ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pc = self.get_persona_card_by_id(pc_id)
            if not pc:
                return False

            self.db.delete(pc)
            self.db.commit()

            logger.info(f'Persona card deleted: pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error deleting persona card {pc_id}: {str(e)}')
            return False

    def is_starred(self, user_id: str, pc_id: str) -> bool:
        """
        Check if persona card is starred by user.
        
        Args:
            user_id: User ID
            pc_id: Persona card ID
            
        Returns:
            True if starred, False otherwise
        """
        try:
            from app.models.database import StarRecord
            record = self.db.query(StarRecord).filter(
                StarRecord.user_id == user_id,
                StarRecord.target_id == pc_id,
                StarRecord.target_type == "persona"
            ).first()
            return record is not None
        except Exception as e:
            logger.error(f'Error checking star status: {str(e)}')
            return False

    def add_star(self, user_id: str, pc_id: str) -> bool:
        """
        Add star to persona card.
        
        Args:
            user_id: User ID
            pc_id: Persona card ID
            
        Returns:
            True if successful, False if already starred
        """
        try:
            # Check if already starred
            if self.is_starred(user_id, pc_id):
                return False

            from app.models.database import StarRecord
            import uuid
            
            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_id=pc_id,
                target_type="persona",
                created_at=datetime.now()
            )
            self.db.add(star)

            # Increment star count
            pc = self.get_persona_card_by_id(pc_id)
            if pc:
                pc.star_count = (pc.star_count or 0) + 1

            self.db.commit()

            logger.info(f'Star added: user_id={user_id}, pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error adding star: {str(e)}')
            return False

    def remove_star(self, user_id: str, pc_id: str) -> bool:
        """
        Remove star from persona card.
        
        Args:
            user_id: User ID
            pc_id: Persona card ID
            
        Returns:
            True if successful, False if not starred
        """
        try:
            from app.models.database import StarRecord
            
            star = self.db.query(StarRecord).filter(
                StarRecord.user_id == user_id,
                StarRecord.target_id == pc_id,
                StarRecord.target_type == "persona"
            ).first()

            if not star:
                return False

            self.db.delete(star)

            # Decrement star count
            pc = self.get_persona_card_by_id(pc_id)
            if pc and pc.star_count > 0:
                pc.star_count = pc.star_count - 1

            self.db.commit()

            logger.info(f'Star removed: user_id={user_id}, pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error removing star: {str(e)}')
            return False

    def increment_downloads(self, pc_id: str) -> bool:
        """
        Increment download count for persona card.
        
        Args:
            pc_id: Persona card ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pc = self.get_persona_card_by_id(pc_id)
            if not pc:
                return False

            pc.downloads = (pc.downloads or 0) + 1
            self.db.commit()

            logger.info(f'Download count incremented: pc_id={pc_id}, count={pc.downloads}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error incrementing downloads for {pc_id}: {str(e)}')
            return False

    def get_files_by_persona_card_id(self, pc_id: str) -> List[PersonaCardFile]:
        """
        Get all files for a persona card.
        
        Args:
            pc_id: Persona card ID
            
        Returns:
            List of PersonaCardFile objects
        """
        try:
            files = self.db.query(PersonaCardFile).filter(
                PersonaCardFile.persona_card_id == pc_id
            ).all()
            return files
        except Exception as e:
            logger.error(f'Error getting files for persona card {pc_id}: {str(e)}')
            return []

    def delete_files_by_persona_card_id(self, pc_id: str) -> bool:
        """
        Delete all files for a persona card.
        
        Args:
            pc_id: Persona card ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.db.query(PersonaCardFile).filter(
                PersonaCardFile.persona_card_id == pc_id
            ).delete()
            self.db.commit()

            logger.info(f'Files deleted for persona card: pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error deleting files for persona card {pc_id}: {str(e)}')
            return False

    def create_upload_record(
        self,
        uploader_id: str,
        target_id: str,
        name: str,
        description: str,
        status: str = "success"
    ) -> Optional[str]:
        """
        Create upload record for persona card.
        
        Args:
            uploader_id: Uploader user ID
            target_id: Persona card ID
            name: Persona card name
            description: Persona card description
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
                target_type="persona",
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
        Delete upload records for a persona card.
        
        Args:
            target_id: Persona card ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.db.query(UploadRecord).filter(
                UploadRecord.target_id == target_id,
                UploadRecord.target_type == "persona"
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
