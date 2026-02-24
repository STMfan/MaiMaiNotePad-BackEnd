"""
监控指标路由

提供 Prometheus 格式的监控指标导出端点。
"""

import logging
from typing import Any

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.cache import get_cache_manager, get_cache_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["监控"])


@router.get(
    "/prometheus",
    response_class=Response,
    summary="导出 Prometheus 指标",
    description="以 Prometheus 格式导出所有监控指标",
)
async def prometheus_metrics():
    """导出 Prometheus 格式的监控指标

    Returns:
        Response: Prometheus 格式的指标数据
    """
    try:
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"导出 Prometheus 指标失败: {e}")
        return Response(content=f"# 导出指标失败: {str(e)}\n", media_type=CONTENT_TYPE_LATEST, status_code=500)


@router.get(
    "/cache",
    response_model=dict[str, Any],
    summary="获取缓存统计信息",
    description="获取缓存的详细统计信息，包括命中率、降级次数等",
)
async def cache_metrics():
    """获取缓存统计信息

    Returns:
        dict: 缓存统计信息
    """
    try:
        cache_manager = get_cache_manager()
        metrics = get_cache_metrics()

        # 获取缓存命中率
        hit_rate = metrics.get_cache_hit_rate()

        # 获取缓存启用状态
        cache_enabled = cache_manager.is_enabled()

        return {
            "cache_enabled": cache_enabled,
            "hit_rate": f"{hit_rate:.2f}%",
            "hit_rate_value": hit_rate,
            "metrics": {
                "hits_total": sum(sample.value for sample in metrics.cache_hits_total.collect()[0].samples),
                "misses_total": sum(sample.value for sample in metrics.cache_misses_total.collect()[0].samples),
                "degradation_total": sum(
                    sample.value for sample in metrics.cache_degradation_total.collect()[0].samples
                ),
                "enabled_status": cache_enabled,
            },
        }
    except Exception as e:
        logger.error(f"获取缓存统计信息失败: {e}")
        return {"error": str(e), "cache_enabled": False, "hit_rate": "0.00%", "hit_rate_value": 0.0}


@router.get("/health", response_model=dict[str, Any], summary="健康检查", description="检查缓存系统的健康状态")
async def health_check():
    """健康检查端点

    Returns:
        dict: 健康状态信息
    """
    try:
        cache_manager = get_cache_manager()

        # 检查缓存是否启用
        cache_enabled = cache_manager.is_enabled()

        # 检查 Redis 连接（如果启用）
        redis_healthy = False
        if cache_enabled and cache_manager.redis_client:
            try:
                redis_healthy = await cache_manager.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis 健康检查失败: {e}")
                redis_healthy = False

        status = "healthy" if (not cache_enabled or redis_healthy) else "degraded"

        return {
            "status": status,
            "cache_enabled": cache_enabled,
            "redis_healthy": redis_healthy if cache_enabled else None,
            "message": "缓存系统运行正常" if status == "healthy" else "缓存系统已降级",
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "cache_enabled": False,
            "redis_healthy": False,
            "message": f"健康检查失败: {str(e)}",
        }
