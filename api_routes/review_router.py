from fastapi import APIRouter, Depends, HTTPException, status as HTTPStatus, Body, Query
from typing import Optional

from api_routes.response_util import Page, Success

from models import (
    Message,
    KnowledgeBaseResponse,
    PersonaCardResponse,
    KnowledgeBasePaginatedResponse,
    PersonaCardPaginatedResponse,
    BaseResponse,
    PageResponse,
)
from database_models import sqlite_db_manager
from user_management import get_current_user
from websocket_manager import message_ws_manager

# 导入错误处理和日志记录模块
from logging_config import app_logger

# 创建路由器
review_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager


# 审核相关路由
@review_router.get(
    "/review/knowledge/pending",
    response_model=PageResponse[dict]
)
async def get_pending_knowledge_bases(
        page: int = Query(1, ge=1, description="页码，默认为1"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量，默认为10，最大100"),
        name: Optional[str] = Query(None, description="按名称搜索"),
        uploader_id: Optional[str] = Query(None, description="按上传者ID筛选"),
        sort_by: str = Query(
            "created_at", description="排序字段，可选：created_at, updated_at, star_count"),
        sort_order: str = Query("desc", description="排序方式，可选：asc, desc"),
        current_user: dict = Depends(get_current_user)
):
    """获取待审核的知识库（需要admin或moderator权限），支持分页、搜索、按上传者筛选和排序"""
    # 验证权限：admin 或 moderator（包含 super_admin）
    is_admin = bool(current_user.get("is_admin"))
    is_moderator = bool(current_user.get("is_moderator"))
    role = current_user.get("role", "user")
    if not (is_admin or is_moderator or role in ["admin", "moderator", "super_admin"]):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kbs, total = db_manager.get_pending_knowledge_bases(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return Page(
            message="获取待审核知识库成功",
            data=[kb.to_dict() for kb in kbs],
            page=page,
            page_size=page_size,
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待审核知识库失败: {str(e)}"
        )


@review_router.get(
    "/review/persona/pending",
    response_model=PageResponse[dict]
)
async def get_pending_persona_cards(
        page: int = Query(1, ge=1, description="页码，默认为1"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量，默认为10，最大100"),
        name: Optional[str] = Query(None, description="按名称搜索"),
        uploader_id: Optional[str] = Query(None, description="按上传者ID筛选"),
        sort_by: str = Query(
            "created_at", description="排序字段，可选：created_at, updated_at, star_count"),
        sort_order: str = Query("desc", description="排序方式，可选：asc, desc"),
        current_user: dict = Depends(get_current_user)
):
    """获取待审核的人设卡（需要admin或moderator权限），支持分页、搜索、按上传者筛选和排序"""
    # 验证权限：admin 或 moderator（包含 super_admin）
    is_admin = bool(current_user.get("is_admin"))
    is_moderator = bool(current_user.get("is_moderator"))
    role = current_user.get("role", "user")
    if not (is_admin or is_moderator or role in ["admin", "moderator", "super_admin"]):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pcs, total = db_manager.get_pending_persona_cards(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return Page(
            message="获取待审核人设卡成功",
            data=[pc.to_dict() for pc in pcs],
            page=page,
            page_size=page_size,
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待审核人设卡失败: {str(e)}"
        )


@review_router.post(
    "/review/knowledge/{kb_id}/approve",
    response_model=BaseResponse[None]
)
async def approve_knowledge_base(
        kb_id: str,
        current_user: dict = Depends(get_current_user)
):
    """审核通过知识库（需要admin或moderator权限）"""
    # 验证权限：admin 或 moderator（包含 super_admin）
    is_admin = bool(current_user.get("is_admin"))
    is_moderator = bool(current_user.get("is_moderator"))
    role = current_user.get("role", "user")
    if not (is_admin or is_moderator or role in ["admin", "moderator", "super_admin"]):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 更新状态
        kb.is_public = True
        kb.is_pending = False
        kb.rejection_reason = None

        updated_kb = db_manager.save_knowledge_base(kb.to_dict())
        if not updated_kb:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(kb_id, "approved")
        except Exception as e:
            app_logger.warning(
                f"Failed to update upload record status: {str(e)}")
        # 发送审核通过通知并通过 WebSocket 推送
        try:
            if kb.uploader_id:
                message = Message(
                    recipient_id=kb.uploader_id,
                    sender_id=current_user.get("id", ""),
                    title="知识库审核通过",
                    content=f"您上传的知识库《{kb.name}》已通过审核并公开至知识库广场。"
                )
                saved = db_manager.save_message(message)
                if saved:
                    await message_ws_manager.broadcast_user_update({kb.uploader_id})
        except Exception as e:
            app_logger.warning(
                f"Failed to send approve notification for knowledge base {kb_id}: {str(e)}"
            )

        return Success(message="审核通过，已发送通知")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核知识库失败: {str(e)}"
        )


@review_router.post(
    "/review/knowledge/{kb_id}/reject",
    response_model=BaseResponse[None]
)
async def reject_knowledge_base(
        kb_id: str,
        reason: str = Body(..., embed=True),
        current_user: dict = Depends(get_current_user)
):
    """审核拒绝知识库（需要admin或moderator权限）"""
    # 验证权限：admin 或 moderator（包含 super_admin）
    is_admin = bool(current_user.get("is_admin"))
    is_moderator = bool(current_user.get("is_moderator"))
    role = current_user.get("role", "user")
    if not (is_admin or is_moderator or role in ["admin", "moderator", "super_admin"]):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 更新状态
        kb.is_public = False
        kb.is_pending = False
        kb.rejection_reason = reason

        updated_kb = db_manager.save_knowledge_base(kb.to_dict())
        if not updated_kb:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(kb_id, "rejected")
        except Exception as e:
            app_logger.warning(
                f"Failed to update upload record status: {str(e)}")

        # 发送拒绝通知
        message = Message(
            recipient_id=kb.uploader_id,
            sender_id=current_user.get("id", ""),
            title="知识库审核未通过",
            content=f"您上传的知识库《{kb.name}》未通过审核。\n\n拒绝原因：{reason}"
        )

        saved = db_manager.save_message(message)

        # 通过 WebSocket 推送最新消息状态
        try:
            if saved and kb.uploader_id:
                await message_ws_manager.broadcast_user_update({kb.uploader_id})
        except Exception as e:
            app_logger.warning(
                f"Failed to send reject notification for knowledge base {kb_id}: {str(e)}"
            )

        return Success(message="审核拒绝，已发送通知")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核知识库失败: {str(e)}"
        )


@review_router.post(
    "/review/persona/{pc_id}/approve",
    response_model=BaseResponse[None]
)
async def approve_persona_card(
        pc_id: str,
        current_user: dict = Depends(get_current_user)
):
    """审核通过人设卡（需要admin或moderator权限）"""
    # 验证权限：admin 或 moderator（包含 super_admin）
    is_admin = bool(current_user.get("is_admin"))
    is_moderator = bool(current_user.get("is_moderator"))
    role = current_user.get("role", "user")
    if not (is_admin or is_moderator or role in ["admin", "moderator", "super_admin"]):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_404_NOT_FOUND,
                detail="人设卡不存在"
            )

        # 更新状态
        pc.is_public = True
        pc.is_pending = False
        pc.rejection_reason = None

        updated_pc = db_manager.save_persona_card(pc.to_dict())
        if not updated_pc:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新人设卡状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(pc_id, "approved")
        except Exception as e:
            app_logger.warning(
                f"Failed to update upload record status: {str(e)}")
        # 发送审核通过通知并通过 WebSocket 推送
        try:
            if pc.uploader_id:
                message = Message(
                    recipient_id=pc.uploader_id,
                    sender_id=current_user.get("id", ""),
                    title="人设卡审核通过",
                    content=f"您上传的人设卡《{pc.name}》已通过审核并公开至人设广场。"
                )
                saved = db_manager.save_message(message)
                if saved:
                    await message_ws_manager.broadcast_user_update({pc.uploader_id})
        except Exception as e:
            app_logger.warning(
                f"Failed to send approve notification for persona card {pc_id}: {str(e)}"
            )

        return Success(message="审核通过，已发送通知")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核人设卡失败: {str(e)}"
        )


@review_router.post(
    "/review/persona/{pc_id}/reject",
    response_model=BaseResponse[None]
)
async def reject_persona_card(
        pc_id: str,
        reason: str = Body(..., embed=True),
        current_user: dict = Depends(get_current_user)
):
    """审核拒绝人设卡（需要admin或moderator权限）"""
    # 验证权限：admin 或 moderator（包含 super_admin）
    is_admin = bool(current_user.get("is_admin"))
    is_moderator = bool(current_user.get("is_moderator"))
    role = current_user.get("role", "user")
    if not (is_admin or is_moderator or role in ["admin", "moderator", "super_admin"]):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_404_NOT_FOUND,
                detail="人设卡不存在"
            )

        # 更新状态
        pc.is_public = False
        pc.is_pending = False
        pc.rejection_reason = reason

        updated_pc = db_manager.save_persona_card(pc.to_dict())
        if not updated_pc:
            raise HTTPException(
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新人设卡状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(pc_id, "rejected")
        except Exception as e:
            app_logger.warning(
                f"Failed to update upload record status: {str(e)}")

        # 发送拒绝通知
        message = Message(
            recipient_id=pc.uploader_id,
            sender_id=current_user.get("id", ""),
            title="人设卡审核未通过",
            content=f"您上传的人设卡《{pc.name}》未通过审核。\n\n拒绝原因：{reason}"
        )

        saved = db_manager.save_message(message)

        # 通过 WebSocket 推送最新消息状态
        try:
            if saved and pc.uploader_id:
                await message_ws_manager.broadcast_user_update({pc.uploader_id})
        except Exception as e:
            app_logger.warning(
                f"Failed to send reject notification for persona card {pc_id}: {str(e)}"
            )

        return Success(message="审核拒绝，已发送通知")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核人设卡失败: {str(e)}"
        )
