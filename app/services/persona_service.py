"""
人设卡服务模块

包含人设卡管理相关的业务逻辑，包括增删改查、审核、收藏和下载功能。
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.database import PersonaCard, PersonaCardFile, User, UploadRecord

logger = logging.getLogger(__name__)


class PersonaService:
    """
    人设卡管理服务类。
    处理人设卡的增删改查、审核、收藏和下载功能。
    """

    def __init__(self, db: Session):
        """
        初始化人设卡服务。
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db

    def get_persona_card_by_id(self, pc_id: str, include_files: bool = False) -> Optional[PersonaCard]:
        """
        根据 ID 获取人设卡。
        
        Args:
            pc_id: 人设卡 ID
            include_files: 是否包含文件信息
            
        Returns:
            找到返回人设卡对象，否则返回 None
        """
        try:
            pc = self.db.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
            return pc
        except Exception as e:
            logger.error(f'获取人设卡失败 ID={pc_id}: {str(e)}')
            return None

    def get_all_persona_cards(self) -> List[PersonaCard]:
        """
        获取所有人设卡。
        
        Returns:
            人设卡对象列表
        """
        try:
            pcs = self.db.query(PersonaCard).all()
            return pcs
        except Exception as e:
            logger.error(f'获取所有人设卡失败: {str(e)}')
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
        获取公开人设卡列表，支持分页、搜索和排序。
        
        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            name: 按名称搜索（可选）
            uploader_id: 按上传者 ID 筛选（可选）
            sort_by: 排序字段（created_at、updated_at、star_count）
            sort_order: 排序方向（asc、desc）
            
        Returns:
            (人设卡列表, 总数) 元组
        """
        try:
            query = self.db.query(PersonaCard).filter(
                PersonaCard.is_public == True,
                PersonaCard.is_pending == False
            )

            if name:
                query = query.filter(PersonaCard.name.ilike(f"%{name}%"))
            
            if uploader_id:
                query = query.filter(PersonaCard.uploader_id == uploader_id)

            total = query.count()

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

            offset = (page - 1) * page_size
            pcs = query.offset(offset).limit(page_size).all()

            return pcs, total
        except Exception as e:
            logger.error(f'获取公开人设卡列表失败: {str(e)}')
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
        获取指定用户上传的人设卡列表。
        
        Args:
            user_id: 用户 ID
            page: 页码（从 1 开始）
            page_size: 每页数量
            name: 按名称搜索（可选）
            tag: 按标签搜索（可选）
            status: 状态筛选（all/pending/approved/rejected）
            sort_by: 排序字段（created_at/updated_at/name/downloads/star_count）
            sort_order: 排序方向（asc/desc）
            
        Returns:
            (人设卡列表, 总数) 元组
        """
        try:
            pcs = self.db.query(PersonaCard).filter(
                PersonaCard.uploader_id == user_id
            ).all()

            def match_status(pc):
                if status == "pending":
                    return pc.is_pending
                if status == "approved":
                    return not pc.is_pending and pc.is_public
                if status == "rejected":
                    return not pc.is_pending and (not pc.is_public)
                return True

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
            logger.error(f'获取用户 {user_id} 的人设卡列表失败: {str(e)}')
            return [], 0

    def save_persona_card(self, pc_data: Dict[str, Any]) -> Optional[PersonaCard]:
        """
        保存或更新人设卡。
        
        Args:
            pc_data: 人设卡数据字典
            
        Returns:
            成功返回人设卡对象，否则返回 None
        """
        try:
            pc_id = pc_data.get("id")
            
            if pc_id:
                pc = self.get_persona_card_by_id(pc_id)
                if not pc:
                    return None
                
                for key, value in pc_data.items():
                    if hasattr(pc, key) and key not in ["id", "created_at"]:
                        setattr(pc, key, value)
            else:
                pc = PersonaCard(**pc_data)
                self.db.add(pc)
            
            self.db.commit()
            self.db.refresh(pc)
            
            logger.info(f'人设卡已保存: pc_id={pc.id}')
            return pc
        except Exception as e:
            self.db.rollback()
            logger.error(f'保存人设卡失败: {str(e)}')
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
        更新人设卡信息。
        
        Args:
            pc_id: 人设卡 ID
            update_data: 要更新的字段字典
            user_id: 操作用户 ID
            is_admin: 是否为管理员
            is_moderator: 是否为审核员
            
        Returns:
            (是否成功, 提示消息, 人设卡对象) 元组
        """
        try:
            pc = self.get_persona_card_by_id(pc_id)
            if not pc:
                return False, "人设卡不存在", None

            if pc.uploader_id != user_id and not is_admin and not is_moderator:
                return False, "没有权限修改此人设卡", None

            if pc.is_public or pc.is_pending:
                allowed_fields = {"content"}
                disallowed_fields = [key for key in update_data.keys() if key not in allowed_fields]
                if disallowed_fields:
                    return False, "公开或审核中的人设卡仅允许修改补充说明", None

            update_data.pop("copyright_owner", None)
            update_data.pop("name", None)

            if not (pc.is_public or pc.is_pending):
                if "is_public" in update_data and not (is_admin or is_moderator):
                    return False, "只有管理员可以直接修改公开状态", None

            for key, value in update_data.items():
                if hasattr(pc, key):
                    setattr(pc, key, value)

            if any(field != "content" for field in update_data.keys()):
                pc.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(pc)

            logger.info(f'人设卡已更新: pc_id={pc_id}, user_id={user_id}')
            return True, "人设卡更新成功", pc
        except Exception as e:
            self.db.rollback()
            logger.error(f'更新人设卡 {pc_id} 失败: {str(e)}')
            return False, "修改人设卡失败", None

    def delete_persona_card(self, pc_id: str) -> bool:
        """
        从数据库删除人设卡。
        
        Args:
            pc_id: 人设卡 ID
            
        Returns:
            成功返回 True，否则返回 False
        """
        try:
            pc = self.get_persona_card_by_id(pc_id)
            if not pc:
                return False

            self.db.delete(pc)
            self.db.commit()

            logger.info(f'人设卡已删除: pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'删除人设卡 {pc_id} 失败: {str(e)}')
            return False

    def is_starred(self, user_id: str, pc_id: str) -> bool:
        """
        检查用户是否已收藏该人设卡。
        
        Args:
            user_id: 用户 ID
            pc_id: 人设卡 ID
            
        Returns:
            已收藏返回 True，否则返回 False
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
            logger.error(f'检查收藏状态失败: {str(e)}')
            return False

    def add_star(self, user_id: str, pc_id: str) -> bool:
        """
        收藏人设卡。
        
        Args:
            user_id: 用户 ID
            pc_id: 人设卡 ID
            
        Returns:
            成功返回 True，已收藏返回 False
        """
        try:
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

            pc = self.get_persona_card_by_id(pc_id)
            if pc:
                pc.star_count = (pc.star_count or 0) + 1

            self.db.commit()

            logger.info(f'已收藏: user_id={user_id}, pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'收藏人设卡失败: {str(e)}')
            return False

    def remove_star(self, user_id: str, pc_id: str) -> bool:
        """
        取消收藏人设卡。
        
        Args:
            user_id: 用户 ID
            pc_id: 人设卡 ID
            
        Returns:
            成功返回 True，未收藏返回 False
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

            pc = self.get_persona_card_by_id(pc_id)
            if pc and pc.star_count > 0:
                pc.star_count = pc.star_count - 1

            self.db.commit()

            logger.info(f'已取消收藏: user_id={user_id}, pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'取消收藏人设卡失败: {str(e)}')
            return False

    def increment_downloads(self, pc_id: str) -> bool:
        """
        递增人设卡下载次数。
        
        Args:
            pc_id: 人设卡 ID
            
        Returns:
            成功返回 True，否则返回 False
        """
        try:
            pc = self.get_persona_card_by_id(pc_id)
            if not pc:
                return False

            pc.downloads = (pc.downloads or 0) + 1
            self.db.commit()

            logger.info(f'下载次数已递增: pc_id={pc_id}, count={pc.downloads}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'递增人设卡 {pc_id} 下载次数失败: {str(e)}')
            return False

    def get_files_by_persona_card_id(self, pc_id: str) -> List[PersonaCardFile]:
        """
        获取人设卡的所有文件。
        
        Args:
            pc_id: 人设卡 ID
            
        Returns:
            人设卡文件对象列表
        """
        try:
            files = self.db.query(PersonaCardFile).filter(
                PersonaCardFile.persona_card_id == pc_id
            ).all()
            return files
        except Exception as e:
            logger.error(f'获取人设卡 {pc_id} 的文件列表失败: {str(e)}')
            return []

    def delete_files_by_persona_card_id(self, pc_id: str) -> bool:
        """
        删除人设卡的所有文件记录。
        
        Args:
            pc_id: 人设卡 ID
            
        Returns:
            成功返回 True，否则返回 False
        """
        try:
            self.db.query(PersonaCardFile).filter(
                PersonaCardFile.persona_card_id == pc_id
            ).delete()
            self.db.commit()

            logger.info(f'人设卡文件已删除: pc_id={pc_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'删除人设卡 {pc_id} 的文件失败: {str(e)}')
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
        创建人设卡上传记录。
        
        Args:
            uploader_id: 上传者用户 ID
            target_id: 人设卡 ID
            name: 人设卡名称
            description: 人设卡描述
            status: 上传状态（success/pending）
            
        Returns:
            成功返回上传记录 ID，否则返回 None
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

            logger.info(f'上传记录已创建: target_id={target_id}, status={status}')
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f'创建上传记录失败: {str(e)}')
            return None

    def delete_upload_records_by_target(self, target_id: str) -> bool:
        """
        删除人设卡的上传记录。
        
        Args:
            target_id: 人设卡 ID
            
        Returns:
            成功返回 True，否则返回 False
        """
        try:
            self.db.query(UploadRecord).filter(
                UploadRecord.target_id == target_id,
                UploadRecord.target_type == "persona"
            ).delete()
            self.db.commit()

            logger.info(f'上传记录已删除: target_id={target_id}')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'删除上传记录失败 {target_id}: {str(e)}')
            return False

    def resolve_uploader_id(self, uploader_identifier: str) -> Optional[str]:
        """
        将上传者标识解析为用户 ID。
        支持用户 ID 或用户名。
        
        Args:
            uploader_identifier: 用户 ID 或用户名
            
        Returns:
            找到返回用户 ID，否则返回 None
        """
        try:
            user = self.db.query(User).filter(User.id == uploader_identifier).first()
            if user:
                return user.id
            
            user = self.db.query(User).filter(User.username == uploader_identifier).first()
            if user:
                return user.id
            
            return None
        except Exception as e:
            logger.error(f'解析上传者标识失败 {uploader_identifier}: {str(e)}')
            return None
