"""
内容审核 API 路由

提供基于 AI 的内容安全审核接口。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.response_util import Error, Success
from app.models.schemas import ModerationRequest, ModerationResponse, ModerationResult
from app.services.moderation_service import ModerationService, get_moderation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moderation", tags=["内容审核"])


@router.post(
    "/check", response_model=ModerationResponse, summary="内容审核", description="对用户生成的文本进行内容安全审核"
)
async def check_content(request: ModerationRequest, service: ModerationService = Depends(get_moderation_service)):
    """
    内容审核接口

    对用户提交的文本进行 AI 审核，判断是否包含违规内容（色情、涉政、辱骂）。

    Args:
        request: 审核请求，包含待审核文本和文本类型

    Returns:
        审核结果，包含决策、置信度和违规类型
    """
    try:
        logger.info(f"收到审核请求 - 文本类型: {request.text_type}, 文本长度: {len(request.text)}")

        # 调用审核服务
        result = service.moderate(text=request.text, text_type=request.text_type)

        # 构建响应
        moderation_result = ModerationResult(
            decision=result["decision"], confidence=result["confidence"], violation_types=result["violation_types"]
        )

        return ModerationResponse(success=True, result=moderation_result, message="审核完成")

    except ValueError as e:
        logger.error(f"审核服务配置错误: {e}")
        raise HTTPException(status_code=500, detail=f"审核服务配置错误: {str(e)}") from e

    except Exception as e:
        logger.error(f"审核过程发生异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"审核失败: {str(e)}") from e


@router.get("/health", summary="健康检查", description="检查审核服务是否正常运行")
async def health_check():
    """
    审核服务健康检查

    Returns:
        服务状态信息
    """
    try:
        service = get_moderation_service()
        return Success(data={"status": "healthy", "model": service.model, "base_url": service.base_url})
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return Error(message=f"服务异常: {str(e)}")
