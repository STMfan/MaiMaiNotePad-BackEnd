"""
知识库服务模块

包含知识库管理相关的业务逻辑，包括增删改查、审核、收藏和下载功能。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.database import KnowledgeBase, KnowledgeBaseFile, UploadRecord, User

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    知识库管理服务类。
    处理知识库的增删改查、审核、收藏和下载功能。
    """

    def __init__(self, db: Session):
        """
        初始化知识库服务。

        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db

        # 导入缓存管理器
        from app.core.cache.factory import get_cache_manager

        self.cache_manager = get_cache_manager()

    def get_knowledge_base_by_id(self, kb_id: str, include_files: bool = False) -> KnowledgeBase | None:
        """
        根据 ID 获取知识库。

        Args:
            kb_id: 知识库 ID
            include_files: 是否包含文件信息

        Returns:
            找到返回知识库对象，否则返回 None
        """
        try:
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            return kb
        except Exception as e:
            logger.error(f"获取知识库失败 ID={kb_id}: {str(e)}")
            return None

    def get_public_knowledge_bases(
        self,
        page: int = 1,
        page_size: int = 20,
        name: str | None = None,
        uploader_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[KnowledgeBase], int]:
        """
        获取公开知识库列表，支持分页、搜索和排序。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            name: 按名称搜索（可选）
            uploader_id: 按上传者 ID 筛选（可选）
            sort_by: 排序字段（created_at、updated_at、star_count）
            sort_order: 排序方向（asc、desc）

        Returns:
            (知识库对象列表, 总数) 元组
        """
        try:
            query = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.is_public.is_(True), KnowledgeBase.is_pending.is_(False)
            )

            # 应用筛选条件
            if name:
                query = query.filter(KnowledgeBase.name.ilike(f"%{name}%"))

            if uploader_id:
                query = query.filter(KnowledgeBase.uploader_id == uploader_id)

            # 分页前获取总数
            total = query.count()

            # 应用排序
            sort_field_map = {
                "created_at": KnowledgeBase.created_at,
                "updated_at": KnowledgeBase.updated_at,
                "star_count": KnowledgeBase.star_count,
            }
            sort_field = sort_field_map.get(sort_by, KnowledgeBase.created_at)

            if sort_order.lower() == "asc":
                query = query.order_by(sort_field.asc())
            else:
                query = query.order_by(sort_field.desc())

            # 应用分页
            offset = (page - 1) * page_size
            kbs = query.offset(offset).limit(page_size).all()

            return kbs, total
        except Exception as e:
            logger.error(f"获取公开知识库列表失败: {str(e)}")
            return [], 0

    def get_user_knowledge_bases(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        name: str | None = None,
        tag: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[KnowledgeBase], int]:
        """
        获取用户的知识库列表，支持分页、筛选和排序。

        Args:
            user_id: 用户 ID
            page: 页码（从 1 开始）
            page_size: 每页数量
            status: 状态筛选（pending、public、private）
            name: 按名称搜索（可选）
            tag: 按标签筛选（可选）
            sort_by: 排序字段（created_at、updated_at、star_count）
            sort_order: 排序方向（asc、desc）

        Returns:
            (知识库对象列表, 总数) 元组
        """
        try:
            # 获取用户的所有知识库
            kbs = self.db.query(KnowledgeBase).filter(KnowledgeBase.uploader_id == user_id).all()

            # 应用筛选
            filtered_kbs = self._filter_knowledge_bases(kbs, name, tag, status)

            # 获取总数
            total = len(filtered_kbs)

            # 应用排序
            sorted_kbs = self._sort_knowledge_bases(filtered_kbs, sort_by, sort_order)

            # 应用分页
            paginated_kbs = self._paginate_items(sorted_kbs, page, page_size)

            return paginated_kbs, total
        except Exception as e:
            logger.error(f"获取用户知识库列表失败 user_id={user_id}: {str(e)}")
            return [], 0

    def _filter_knowledge_bases(
        self, kbs: list[KnowledgeBase], name: str | None, tag: str | None, status: str
    ) -> list[KnowledgeBase]:
        """
        根据条件筛选知识库列表。

        Args:
            kbs: 知识库列表
            name: 按名称搜索（可选）
            tag: 按标签搜索（可选）
            status: 状态筛选（all/pending/approved/rejected）

        Returns:
            筛选后的知识库列表
        """
        filtered = []
        for kb in kbs:
            if not self._match_name_filter(kb, name):
                continue
            if not self._match_tag_filter(kb, tag):
                continue
            if not self._match_status_filter(kb, status):
                continue
            filtered.append(kb)
        return filtered

    def _match_name_filter(self, kb: KnowledgeBase, name: str | None) -> bool:
        """检查知识库是否匹配名称筛选条件"""
        if name and name.lower() not in kb.name.lower():
            return False
        return True

    def _match_tag_filter(self, kb: KnowledgeBase, tag: str | None) -> bool:
        """检查知识库是否匹配标签筛选条件"""
        if not tag:
            return True
        tag_list = []
        if kb.tags:
            tag_list = kb.tags.split(",") if isinstance(kb.tags, str) else kb.tags
        return any(tag.lower() in t.lower() for t in tag_list)

    def _match_status_filter(self, kb: KnowledgeBase, status: str) -> bool:
        """检查知识库是否匹配状态筛选条件"""
        if status == "pending":
            return kb.is_pending
        if status == "approved":
            return not kb.is_pending and kb.is_public
        if status == "rejected":
            return not kb.is_pending and (not kb.is_public)
        return True

    def _sort_knowledge_bases(self, kbs: list[KnowledgeBase], sort_by: str, sort_order: str) -> list[KnowledgeBase]:
        """
        对知识库列表进行排序。

        Args:
            kbs: 知识库列表
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            排序后的知识库列表
        """
        sort_field_map = {
            "created_at": lambda kb: kb.created_at,
            "updated_at": lambda kb: kb.updated_at,
            "name": lambda kb: kb.name.lower(),
            "downloads": lambda kb: kb.downloads or 0,
            "star_count": lambda kb: kb.star_count or 0,
        }
        key_func = sort_field_map.get(sort_by, sort_field_map["created_at"])
        reverse = sort_order.lower() != "asc"
        return sorted(kbs, key=key_func, reverse=reverse)

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

    def save_knowledge_base(self, kb_data: dict[str, Any]) -> KnowledgeBase | None:
        """
        保存或更新知识库。

        Args:
            kb_data: 知识库数据字典

        Returns:
            成功返回知识库对象，否则返回 None
        """
        try:
            kb_id = kb_data.get("id")

            if kb_id:
                # 更新已有知识库
                kb = self.get_knowledge_base_by_id(kb_id)
                if not kb:
                    return None

                for key, value in kb_data.items():
                    if hasattr(kb, key) and key not in ["id", "created_at"]:
                        setattr(kb, key, value)
            else:
                # 创建新知识库
                kb = KnowledgeBase(**kb_data)
                self.db.add(kb)

            self.db.commit()
            self.db.refresh(kb)

            # 清除知识库相关缓存
            try:
                from app.core.cache.invalidation import invalidate_knowledge_cache

                if self.cache_manager.is_enabled():
                    invalidate_knowledge_cache(kb_id=kb.id, uploader_id=kb.uploader_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"知识库已保存: kb_id={kb.id}")
            return kb
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存知识库失败: {str(e)}")
            return None

    def check_duplicate_name(self, user_id: str, name: str, exclude_kb_id: str | None = None) -> bool:
        """
        检查用户是否已有同名知识库。

        Args:
            user_id: 用户 ID
            name: 知识库名称
            exclude_kb_id: 排除的知识库 ID（用于更新时）

        Returns:
            存在重复返回 True，否则返回 False
        """
        try:
            query = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.uploader_id == user_id, KnowledgeBase.name == name
            )

            if exclude_kb_id:
                query = query.filter(KnowledgeBase.id != exclude_kb_id)

            return query.first() is not None
        except Exception as e:
            logger.error(f"检查知识库重名失败: {str(e)}")
            return False

    def update_knowledge_base(
        self, kb_id: str, update_data: dict[str, Any], user_id: str, is_admin: bool = False, is_moderator: bool = False
    ) -> tuple[bool, str, KnowledgeBase | None]:
        """
        更新知识库信息。

        Args:
            kb_id: 知识库 ID
            update_data: 要更新的字段字典
            user_id: 操作用户 ID
            is_admin: 是否为管理员
            is_moderator: 是否为审核员

        Returns:
            (是否成功, 提示消息, 知识库对象) 元组
        """
        try:
            # 直接从数据库查询，不使用缓存
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return False, "知识库不存在", None

            # 权限检查
            if not self._check_update_permission(kb, user_id, is_admin, is_moderator):
                return False, "是你的知识库吗你就改", None

            # 公开或审核中的知识库限制修改范围
            if not self._validate_public_kb_update(kb, update_data):
                return False, "公开或审核中的知识库仅允许修改补充说明", None

            # 清理受保护字段
            self._remove_protected_fields(update_data)

            # 检查公开状态修改权限
            if not self._validate_public_status_change(kb, update_data, is_admin, is_moderator):
                return False, "只有管理员可以直接修改公开状态", None

            # 应用更新
            self._apply_updates(kb, update_data)

            self.db.commit()
            self.db.refresh(kb)

            # 清除知识库相关缓存
            try:
                from app.core.cache.invalidation import invalidate_knowledge_cache

                if self.cache_manager.is_enabled():
                    invalidate_knowledge_cache(kb_id=kb_id, uploader_id=kb.uploader_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"知识库已更新: kb_id={kb_id}, user_id={user_id}")
            return True, "修改知识库成功", kb
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新知识库 {kb_id} 失败: {str(e)}")
            return False, "修改知识库失败", None

    def _check_update_permission(self, kb: KnowledgeBase, user_id: str, is_admin: bool, is_moderator: bool) -> bool:
        """检查用户是否有权限更新知识库"""
        return kb.uploader_id == user_id or is_admin or is_moderator

    def _validate_public_kb_update(self, kb: KnowledgeBase, update_data: dict[str, Any]) -> bool:
        """验证公开或审核中的知识库更新是否合法"""
        if not (kb.is_public or kb.is_pending):
            return True
        allowed_fields = {"content"}
        disallowed_fields = [key for key in update_data.keys() if key not in allowed_fields]
        return len(disallowed_fields) == 0

    def _remove_protected_fields(self, update_data: dict[str, Any]) -> None:
        """移除受保护的字段"""
        update_data.pop("copyright_owner", None)
        update_data.pop("name", None)

    def _validate_public_status_change(
        self, kb: KnowledgeBase, update_data: dict[str, Any], is_admin: bool, is_moderator: bool
    ) -> bool:
        """验证公开状态修改权限"""
        if kb.is_public or kb.is_pending:
            return True
        if "is_public" in update_data and not (is_admin or is_moderator):
            return False
        return True

    def _apply_updates(self, kb: KnowledgeBase, update_data: dict[str, Any]) -> None:
        """应用更新到知识库对象"""
        for key, value in update_data.items():
            if hasattr(kb, key):
                setattr(kb, key, value)

        # 非内容字段变更时更新时间戳
        if any(field != "content" for field in update_data.keys()):
            kb.updated_at = datetime.now()

    def delete_knowledge_base(self, kb_id: str) -> bool:
        """
        从数据库删除知识库。

        Args:
            kb_id: 知识库 ID

        Returns:
            成功返回 True，否则返回 False
        """
        try:
            # 直接从数据库查询，不使用缓存
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return False

            uploader_id = kb.uploader_id
            self.db.delete(kb)
            self.db.commit()

            # 清除知识库相关缓存
            try:
                from app.core.cache.invalidation import invalidate_knowledge_cache

                if self.cache_manager.is_enabled():
                    invalidate_knowledge_cache(kb_id=kb_id, uploader_id=uploader_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"知识库已删除: kb_id={kb_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除知识库 {kb_id} 失败: {str(e)}")
            return False

    def is_starred(self, user_id: str, kb_id: str) -> bool:
        """
        检查用户是否已收藏该知识库。

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            已收藏返回 True，否则返回 False
        """
        try:
            from app.models.database import StarRecord

            record = (
                self.db.query(StarRecord)
                .filter(
                    StarRecord.user_id == user_id, StarRecord.target_id == kb_id, StarRecord.target_type == "knowledge"
                )
                .first()
            )
            return record is not None
        except Exception as e:
            logger.error(f"检查收藏状态失败: {str(e)}")
            return False

    def add_star(self, user_id: str, kb_id: str) -> bool:
        """
        收藏知识库。

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            成功返回 True，已收藏返回 False
        """
        try:
            # 检查是否已收藏
            if self.is_starred(user_id, kb_id):
                return False

            import uuid

            from app.models.database import StarRecord

            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_id=kb_id,
                target_type="knowledge",
                created_at=datetime.now(),
            )
            self.db.add(star)

            # 递增收藏数
            kb = self.get_knowledge_base_by_id(kb_id)
            if kb:
                kb.star_count = (kb.star_count or 0) + 1

            self.db.commit()

            # 清除知识库相关缓存（因为 star_count 变化）
            try:
                from app.core.cache.invalidation import invalidate_knowledge_cache

                if self.cache_manager.is_enabled():
                    invalidate_knowledge_cache(kb_id=kb_id, uploader_id=kb.uploader_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"已收藏: user_id={user_id}, kb_id={kb_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"收藏知识库失败: {str(e)}")
            return False

    def remove_star(self, user_id: str, kb_id: str) -> bool:
        """
        取消收藏知识库。

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            成功返回 True，未收藏返回 False
        """
        try:
            from app.models.database import StarRecord

            star = (
                self.db.query(StarRecord)
                .filter(
                    StarRecord.user_id == user_id, StarRecord.target_id == kb_id, StarRecord.target_type == "knowledge"
                )
                .first()
            )

            if not star:
                return False

            self.db.delete(star)

            # 递减收藏数
            kb = self.get_knowledge_base_by_id(kb_id)
            if kb and kb.star_count > 0:
                kb.star_count = kb.star_count - 1

            self.db.commit()

            # 清除知识库相关缓存（因为 star_count 变化）
            try:
                from app.core.cache.invalidation import invalidate_knowledge_cache

                if self.cache_manager.is_enabled():
                    invalidate_knowledge_cache(kb_id=kb_id, uploader_id=kb.uploader_id)
            except Exception as cache_error:
                logger.warning(f"清除缓存失败: {cache_error}")

            logger.info(f"已取消收藏: user_id={user_id}, kb_id={kb_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"取消收藏知识库失败: {str(e)}")
            return False

    def increment_downloads(self, kb_id: str) -> bool:
        """
        递增知识库下载次数。

        Args:
            kb_id: 知识库 ID

        Returns:
            成功返回 True，否则返回 False
        """
        try:
            kb = self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return False

            kb.downloads = (kb.downloads or 0) + 1
            self.db.commit()

            logger.info(f"下载次数已递增: kb_id={kb_id}, count={kb.downloads}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"递增知识库 {kb_id} 下载次数失败: {str(e)}")
            return False

    def get_files_by_knowledge_base_id(self, kb_id: str) -> list[KnowledgeBaseFile]:
        """
        获取知识库的所有文件。

        Args:
            kb_id: 知识库 ID

        Returns:
            知识库文件对象列表
        """
        try:
            files = self.db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).all()
            return files
        except Exception as e:
            logger.error(f"获取知识库 {kb_id} 的文件列表失败: {str(e)}")
            return []

    def create_upload_record(
        self, uploader_id: str, target_id: str, name: str, description: str, status: str = "success"
    ) -> str | None:
        """
        创建知识库上传记录。

        Args:
            uploader_id: 上传者用户 ID
            target_id: 知识库 ID
            name: 知识库名称
            description: 知识库描述
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
                target_type="knowledge",
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
        删除知识库的上传记录。

        Args:
            target_id: 知识库 ID

        Returns:
            成功返回 True，否则返回 False
        """
        try:
            self.db.query(UploadRecord).filter(
                UploadRecord.target_id == target_id, UploadRecord.target_type == "knowledge"
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
            # 先按 ID 查找
            user = self.db.query(User).filter(User.id == uploader_identifier).first()
            if user:
                return user.id

            # 再按用户名查找
            user = self.db.query(User).filter(User.username == uploader_identifier).first()
            if user:
                return user.id

            return None
        except Exception as e:
            logger.error(f"解析上传者标识失败 {uploader_identifier}: {str(e)}")
            return None

    async def _invalidate_knowledge_base_list_cache(self, uploader_id: str) -> None:
        """
        使知识库列表缓存失效。

        当知识库被更新或删除时，需要清除相关的列表缓存。

        Args:
            uploader_id: 上传者用户 ID
        """
        try:
            # 使用户知识库列表缓存失效（所有分页和筛选条件）
            await self.cache_manager.invalidate_pattern(f"maimnp:kb:user:{uploader_id}:*")

            # 使公开知识库列表缓存失效（所有分页和筛选条件）
            await self.cache_manager.invalidate_pattern("maimnp:kb:public:*")

            logger.debug(f"知识库列表缓存已失效: uploader_id={uploader_id}")
        except Exception as e:
            logger.warning(f"使知识库列表缓存失效失败: {e}")
