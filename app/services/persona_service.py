"""
人设卡服务模块

包含人设卡管理相关的业务逻辑，包括增删改查、审核、收藏和下载功能。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache.decorators import cache_invalidate
from app.core.cache.invalidation import invalidate_persona_cache
from app.models.database import PersonaCard, PersonaCardFile, UploadRecord, User

logger = logging.getLogger(__name__)

# 定义人设卡相关的缓存模式
PERSONA_PUBLIC_CACHE_PATTERN = "maimnp:http:*persona/public*"


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

    def get_persona_card_by_id(self, pc_id: str, include_files: bool = False) -> PersonaCard | None:
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
            logger.error(f"获取人设卡失败 ID={pc_id}: {str(e)}")
            return None

    def get_all_persona_cards(self) -> list[PersonaCard]:
        """
        获取所有人设卡。

        Returns:
            人设卡对象列表
        """
        try:
            pcs = self.db.query(PersonaCard).all()
            return pcs
        except Exception as e:
            logger.error(f"获取所有人设卡失败: {str(e)}")
            return []

    def get_public_persona_cards(
        self,
        page: int = 1,
        page_size: int = 20,
        name: str | None = None,
        uploader_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[PersonaCard], int]:
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
                PersonaCard.is_public.is_(True), PersonaCard.is_pending.is_(False)
            )

            if name:
                query = query.filter(PersonaCard.name.ilike(f"%{name}%"))

            if uploader_id:
                query = query.filter(PersonaCard.uploader_id == uploader_id)

            total = query.count()

            sort_field_map = {
                "created_at": PersonaCard.created_at,
                "updated_at": PersonaCard.updated_at,
                "star_count": PersonaCard.star_count,
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
            logger.error(f"获取公开人设卡列表失败: {str(e)}")
            return [], 0

    def get_user_persona_cards(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        name: str | None = None,
        tag: str | None = None,
        status: str = "all",
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[PersonaCard], int]:
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
            pcs = self.db.query(PersonaCard).filter(PersonaCard.uploader_id == user_id).all()

            # 应用筛选条件
            filtered = self._filter_persona_cards(pcs, name, tag, status)

            # 排序
            sorted_pcs = self._sort_persona_cards(filtered, sort_by, sort_order)

            # 分页
            total = len(sorted_pcs)
            page_items = self._paginate_items(sorted_pcs, page, page_size)

            return page_items, total
        except Exception as e:
            logger.error(f"获取用户 {user_id} 的人设卡列表失败: {str(e)}")
            return [], 0

    def _filter_persona_cards(
        self, pcs: list[PersonaCard], name: str | None, tag: str | None, status: str
    ) -> list[PersonaCard]:
        """
        根据条件筛选人设卡列表。

        Args:
            pcs: 人设卡列表
            name: 按名称搜索（可选）
            tag: 按标签搜索（可选）
            status: 状态筛选（all/pending/approved/rejected）

        Returns:
            筛选后的人设卡列表
        """
        filtered = []
        for pc in pcs:
            if not self._match_name_filter(pc, name):
                continue
            if not self._match_tag_filter(pc, tag):
                continue
            if not self._match_status_filter(pc, status):
                continue
            filtered.append(pc)
        return filtered

    def _match_name_filter(self, pc: PersonaCard, name: str | None) -> bool:
        """检查人设卡是否匹配名称筛选条件"""
        if name and name.lower() not in pc.name.lower():
            return False
        return True

    def _match_tag_filter(self, pc: PersonaCard, tag: str | None) -> bool:
        """检查人设卡是否匹配标签筛选条件"""
        if not tag:
            return True
        tag_list = []
        if pc.tags:
            tag_list = pc.tags.split(",") if isinstance(pc.tags, str) else pc.tags
        return any(tag.lower() in t.lower() for t in tag_list)

    def _match_status_filter(self, pc: PersonaCard, status: str) -> bool:
        """检查人设卡是否匹配状态筛选条件"""
        if status == "pending":
            return pc.is_pending
        if status == "approved":
            return not pc.is_pending and pc.is_public
        if status == "rejected":
            return not pc.is_pending and (not pc.is_public)
        return True

    def _sort_persona_cards(self, pcs: list[PersonaCard], sort_by: str, sort_order: str) -> list[PersonaCard]:
        """
        对人设卡列表进行排序。

        Args:
            pcs: 人设卡列表
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            排序后的人设卡列表
        """
        sort_field_map = {
            "created_at": lambda pc: pc.created_at,
            "updated_at": lambda pc: pc.updated_at,
            "name": lambda pc: pc.name.lower(),
            "downloads": lambda pc: pc.downloads or 0,
            "star_count": lambda pc: pc.star_count or 0,
        }
        key_func = sort_field_map.get(sort_by, sort_field_map["created_at"])
        reverse = sort_order.lower() != "asc"
        return sorted(pcs, key=key_func, reverse=reverse)

    def _paginate_items(self, items: list[Any], page: int, page_size: int) -> list[Any]:
        """
        对列表进行分页。

        Args:
            items: 待分页的列表
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            当前页的项目列表
        """
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end]

    def save_persona_card(self, pc_data: dict[str, Any]) -> PersonaCard | None:
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

            # 清除人设卡相关缓存
            try:
                from app.core.cache.factory import get_cache_manager

                cache_manager = get_cache_manager()
                if cache_manager.is_enabled():
                    invalidate_persona_cache(pc.id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"人设卡已保存: pc_id={pc.id}")
            return pc
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存人设卡失败: {str(e)}")
            return None

    @cache_invalidate(key_pattern="persona:{pc_id}")
    def update_persona_card(
        self, pc_id: str, update_data: dict[str, Any], user_id: str, is_admin: bool = False, is_moderator: bool = False
    ) -> tuple[bool, str, PersonaCard | None]:
        """
        更新人设卡信息（自动失效缓存）。

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

            # 权限检查
            if not self._check_update_permission(pc, user_id, is_admin, is_moderator):
                return False, "没有权限修改此人设卡", None

            # 公开或审核中的人设卡限制修改范围
            if not self._validate_public_pc_update(pc, update_data):
                return False, "公开或审核中的人设卡仅允许修改补充说明", None

            # 清理受保护字段
            self._remove_protected_fields(update_data)

            # 检查公开状态修改权限
            if not self._validate_public_status_change(pc, update_data, is_admin, is_moderator):
                return False, "只有管理员可以直接修改公开状态", None

            # 应用更新
            self._apply_updates(pc, update_data)

            self.db.commit()
            self.db.refresh(pc)

            # 清除人设卡相关缓存
            try:
                from app.core.cache.factory import get_cache_manager

                cache_manager = get_cache_manager()
                if cache_manager.is_enabled():
                    invalidate_persona_cache(pc_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"人设卡已更新: pc_id={pc_id}, user_id={user_id}")
            return True, "人设卡更新成功", pc
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新人设卡 {pc_id} 失败: {str(e)}")
            return False, "修改人设卡失败", None

    def _check_update_permission(self, pc: PersonaCard, user_id: str, is_admin: bool, is_moderator: bool) -> bool:
        """检查用户是否有权限更新人设卡"""
        return pc.uploader_id == user_id or is_admin or is_moderator

    def _validate_public_pc_update(self, pc: PersonaCard, update_data: dict[str, Any]) -> bool:
        """验证公开或审核中的人设卡更新是否合法"""
        if not (pc.is_public or pc.is_pending):
            return True
        allowed_fields = {"content"}
        disallowed_fields = [key for key in update_data.keys() if key not in allowed_fields]
        return len(disallowed_fields) == 0

    def _remove_protected_fields(self, update_data: dict[str, Any]) -> None:
        """移除受保护的字段"""
        update_data.pop("copyright_owner", None)
        update_data.pop("name", None)

    def _validate_public_status_change(
        self, pc: PersonaCard, update_data: dict[str, Any], is_admin: bool, is_moderator: bool
    ) -> bool:
        """验证公开状态修改权限"""
        if pc.is_public or pc.is_pending:
            return True
        if "is_public" in update_data and not (is_admin or is_moderator):
            return False
        return True

    def _apply_updates(self, pc: PersonaCard, update_data: dict[str, Any]) -> None:
        """应用更新到人设卡对象"""
        for key, value in update_data.items():
            if hasattr(pc, key):
                setattr(pc, key, value)

        # 非内容字段变更时更新时间戳
        if any(field != "content" for field in update_data.keys()):
            pc.updated_at = datetime.now()

            # 非内容字段变更时更新时间戳
            if any(field != "content" for field in update_data.keys()):
                pc.updated_at = datetime.now()

    @cache_invalidate(key_pattern="persona:{pc_id}")
    def delete_persona_card(self, pc_id: str) -> bool:
        """
        从数据库删除人设卡（自动失效缓存）。

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

            # 清除人设卡相关缓存
            try:
                from app.core.cache.factory import get_cache_manager

                cache_manager = get_cache_manager()
                if cache_manager.is_enabled():
                    invalidate_persona_cache(pc_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"人设卡已删除: pc_id={pc_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除人设卡 {pc_id} 失败: {str(e)}")
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

            record = (
                self.db.query(StarRecord)
                .filter(
                    StarRecord.user_id == user_id, StarRecord.target_id == pc_id, StarRecord.target_type == "persona"
                )
                .first()
            )
            return record is not None
        except Exception as e:
            logger.error(f"检查收藏状态失败: {str(e)}")
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

            import uuid

            from app.models.database import StarRecord

            star = StarRecord(
                id=str(uuid.uuid4()), user_id=user_id, target_id=pc_id, target_type="persona", created_at=datetime.now()
            )
            self.db.add(star)

            pc = self.get_persona_card_by_id(pc_id)
            if pc:
                pc.star_count = (pc.star_count or 0) + 1

            self.db.commit()

            # 清除人设卡相关缓存（因为 star_count 变化）
            try:
                from app.core.cache.factory import get_cache_manager

                cache_manager = get_cache_manager()
                if cache_manager.is_enabled():
                    invalidate_persona_cache(pc_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"已收藏: user_id={user_id}, pc_id={pc_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"收藏人设卡失败: {str(e)}")
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

            star = (
                self.db.query(StarRecord)
                .filter(
                    StarRecord.user_id == user_id, StarRecord.target_id == pc_id, StarRecord.target_type == "persona"
                )
                .first()
            )

            if not star:
                return False

            self.db.delete(star)

            pc = self.get_persona_card_by_id(pc_id)
            if pc and pc.star_count > 0:
                pc.star_count = pc.star_count - 1

            self.db.commit()

            # 清除人设卡相关缓存（因为 star_count 变化）
            try:
                from app.core.cache.factory import get_cache_manager

                cache_manager = get_cache_manager()
                if cache_manager.is_enabled():
                    invalidate_persona_cache(pc_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"已取消收藏: user_id={user_id}, pc_id={pc_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"取消收藏人设卡失败: {str(e)}")
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

            logger.info(f"下载次数已递增: pc_id={pc_id}, count={pc.downloads}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"递增人设卡 {pc_id} 下载次数失败: {str(e)}")
            return False

    def get_files_by_persona_card_id(self, pc_id: str) -> list[PersonaCardFile]:
        """
        获取人设卡的所有文件。

        Args:
            pc_id: 人设卡 ID

        Returns:
            人设卡文件对象列表
        """
        try:
            files = self.db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).all()
            return files
        except Exception as e:
            logger.error(f"获取人设卡 {pc_id} 的文件列表失败: {str(e)}")
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
            self.db.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == pc_id).delete()
            self.db.commit()

            logger.info(f"人设卡文件已删除: pc_id={pc_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除人设卡 {pc_id} 的文件失败: {str(e)}")
            return False

    def create_upload_record(
        self, uploader_id: str, target_id: str, name: str, description: str, status: str = "success"
    ) -> str | None:
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
                created_at=datetime.now(),
            )
            self.db.add(record)
            self.db.commit()

            logger.info(f"上传记录已创建: target_id={target_id}, status={status}")
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建上传记录失败: {str(e)}")
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
                UploadRecord.target_id == target_id, UploadRecord.target_type == "persona"
            ).delete()
            self.db.commit()

            logger.info(f"上传记录已删除: target_id={target_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除上传记录失败 {target_id}: {str(e)}")
            return False

    def resolve_uploader_id(self, uploader_identifier: str) -> str | None:
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
            logger.error(f"解析上传者标识失败 {uploader_identifier}: {str(e)}")
            return None
