"""
FastAPI 缓存中间件

在 FastAPI 请求处理流程中自动处理缓存，支持自动降级。
自动缓存 GET 请求响应，处理缓存头（Cache-Control、ETag）。
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

from fastapi import Request, Response
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache.manager import CacheManager
from app.core.cache.metrics import get_cache_metrics

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """FastAPI 缓存中间件

    自动缓存 GET 请求的响应，支持缓存头处理和自动降级。

    降级行为：
    - 缓存禁用时，直接转发请求到下游处理器
    - Redis 连接失败时，自动降级，不影响请求处理
    - 降级过程对客户端透明
    """

    def __init__(
        self,
        app,
        cache_manager: CacheManager,
        default_ttl: int = 300,
        cache_query_params: bool = True,
        excluded_paths: list | None = None,
    ):
        """初始化缓存中间件

        Args:
            app: FastAPI 应用实例
            cache_manager: 缓存管理器实例
            default_ttl: 默认缓存时间（秒），默认 5 分钟
            cache_query_params: 是否将查询参数纳入缓存键
            excluded_paths: 排除的路径列表（不缓存）
        """
        super().__init__(app)
        self.cache_manager = cache_manager
        self.default_ttl = default_ttl
        self.cache_query_params = cache_query_params
        self.excluded_paths = excluded_paths or []
        self.metrics = get_cache_metrics()

        # 缓存统计信息
        self._stats: dict[str, Any] = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "bypassed": 0,
            "degraded": 0,  # 降级次数
            "degradation_reasons": {},  # 降级原因统计 {reason: count}
        }

        if not cache_manager.is_enabled():
            logger.info("缓存中间件已初始化（降级模式：缓存禁用）")
        else:
            logger.info(f"缓存中间件已初始化: default_ttl={default_ttl}s, " f"cache_query_params={cache_query_params}")

    def _record_degradation(self, reason: str) -> None:
        """记录降级事件

        Args:
            reason: 降级原因
        """
        self._stats["degraded"] += 1
        if reason not in self._stats["degradation_reasons"]:
            self._stats["degradation_reasons"][reason] = 0
        self._stats["degradation_reasons"][reason] += 1

        # 记录到 Prometheus 指标
        self.metrics.record_degradation(reason)

        logger.warning(f"缓存降级: reason={reason}, " f"total_degraded={self._stats['degraded']}")

    def _should_cache_request(self, request: Request) -> bool:
        """判断请求是否应该被缓存

        Args:
            request: FastAPI 请求对象

        Returns:
            bool: 是否应该缓存
        """
        # 只缓存 GET 请求
        if request.method != "GET":
            return False

        # 检查路径是否在排除列表中
        path = request.url.path
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return False

        # 检查请求头中的 Cache-Control
        cache_control = request.headers.get("Cache-Control", "")
        if "no-cache" in cache_control or "no-store" in cache_control:
            return False

        return True

    def _build_cache_key(self, request: Request) -> str:
        """构建缓存键

        根据请求路径和参数生成唯一的缓存键。

        Args:
            request: FastAPI 请求对象

        Returns:
            str: 缓存键
        """
        # 基础路径
        path = request.url.path

        # 查询参数
        if self.cache_query_params and request.url.query:
            # 对查询参数排序，确保相同参数生成相同的键
            query_params = sorted(request.url.query.split("&"))
            query_string = "&".join(query_params)
            cache_key_base = f"{path}?{query_string}"
        else:
            cache_key_base = path

        # 使用 MD5 哈希生成短键（避免键过长）
        key_hash = hashlib.md5(cache_key_base.encode()).hexdigest()

        # 构建标准化缓存键
        return self.cache_manager.build_key("http", key_hash)

    def _parse_cache_control(self, headers: Headers) -> dict[str, Any]:
        """解析 Cache-Control 头

        Args:
            headers: 响应头

        Returns:
            dict: 解析后的 Cache-Control 指令
        """
        cache_control = headers.get("Cache-Control", "")
        directives: dict[str, Any] = {}

        for directive in cache_control.split(","):
            directive = directive.strip()
            if "=" in directive:
                key, value = directive.split("=", 1)
                directives[key.strip()] = value.strip()
            else:
                directives[directive] = True

        return directives

    def _get_ttl_from_response(self, response: Response) -> int | None:
        """从响应头中提取 TTL

        Args:
            response: FastAPI 响应对象

        Returns:
            int: TTL（秒），如果未指定则返回 None
        """
        # 解析 Cache-Control 头
        cache_control = self._parse_cache_control(response.headers)

        # 检查是否禁止缓存
        if cache_control.get("no-store") or cache_control.get("no-cache"):
            return None

        # 提取 max-age
        if "max-age" in cache_control:
            try:
                return int(cache_control["max-age"])
            except (ValueError, TypeError):
                pass

        # 使用默认 TTL
        return self.default_ttl

    def _generate_etag(self, content: bytes) -> str:
        """生成 ETag

        Args:
            content: 响应内容

        Returns:
            str: ETag 值
        """
        return hashlib.md5(content).hexdigest()

    async def dispatch(self, request: Request, call_next):
        """处理请求，自动缓存 GET 请求响应

        降级行为：
        - 缓存禁用时，直接转发请求到下游处理器
        - Redis 连接失败时，自动降级，不影响请求处理
        - 降级过程对客户端透明

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: FastAPI 响应对象
        """
        # 检查是否应该缓存
        if not self._should_cache_request(request):
            self._stats["bypassed"] += 1
            return await call_next(request)

        # 缓存禁用，直接转发请求
        if not self.cache_manager.is_enabled():
            self._stats["bypassed"] += 1
            self._record_degradation("cache_disabled")
            return await call_next(request)

        # 构建缓存键
        cache_key = self._build_cache_key(request)

        # 尝试从缓存获取
        cached_response = await self._try_get_cached_response(request, cache_key)
        if cached_response is not None:
            return cached_response

        # 缓存未命中，执行实际请求
        return await self._handle_cache_miss(request, call_next, cache_key)

    async def _try_get_cached_response(self, request: Request, cache_key: str) -> Response | None:
        """尝试从缓存获取响应"""
        try:
            cached_data = await self.cache_manager.get_cached(cache_key)

            if cached_data is not None:
                self._stats["hits"] += 1
                self.metrics.record_cache_hit("middleware")
                return self._build_cached_response(request, cached_data, cache_key)

        except Exception as e:
            logger.warning(f"缓存读取失败，降级到正常请求处理 (key={cache_key}): {e}")
            self._stats["errors"] += 1
            self._record_degradation("redis_connection_failed")

        return None

    def _build_cached_response(self, request: Request, cached_data: str, cache_key: str) -> Response | None:
        """构建缓存的响应"""
        try:
            cached_response = json.loads(cached_data)

            # 检查 ETag
            if_none_match = request.headers.get("If-None-Match")
            etag = cached_response.get("etag")

            if if_none_match and etag and if_none_match == etag:
                return Response(status_code=304, headers={"ETag": etag})

            # 构建响应
            response = Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"],
                media_type=cached_response.get("media_type"),
            )
            response.headers["X-Cache"] = "HIT"
            logger.debug(f"缓存命中: {request.url.path}")
            return response

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"缓存数据解析失败 (key={cache_key}): {e}")
            asyncio.create_task(self.cache_manager.invalidate(cache_key))
            return None

    async def _handle_cache_miss(self, request: Request, call_next, cache_key: str) -> Response:
        """处理缓存未命中"""
        self._stats["misses"] += 1
        self.metrics.record_cache_miss("middleware")

        start_time = time.time()
        response = await call_next(request)
        response_time = time.time() - start_time

        # 只缓存成功的响应
        if 200 <= response.status_code < 300:
            response = await self._cache_response(request, response, cache_key)

        # 添加响应头
        response.headers["X-Cache"] = "MISS"
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"

        return response

    async def _cache_response(self, request: Request, response: Response, cache_key: str) -> Response:
        """缓存响应"""
        try:
            response_body = await self._read_response_body(response)
            if response_body is None:
                response.headers["X-Cache"] = "MISS"
                return response

            etag = self._generate_etag(response_body)
            ttl = self._get_ttl_from_response(response)

            if ttl is not None and ttl > 0:
                await self._save_to_cache(cache_key, response, response_body, etag, ttl, request)

            # 重新构建响应
            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
            response.headers["ETag"] = etag

        except Exception as e:
            logger.error(f"缓存响应时出错 (key={cache_key}): {e}")
            self._stats["errors"] += 1

        return response

    async def _read_response_body(self, response: Response) -> bytes | None:
        """读取响应体"""
        response_body = b""
        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk
        elif hasattr(response, "body"):
            response_body = response.body  # type: ignore
        else:
            return None
        return response_body

    async def _save_to_cache(
        self, cache_key: str, response: Response, response_body: bytes, etag: str, ttl: int, request: Request
    ) -> None:
        """保存响应到缓存"""
        cache_data = {
            "content": response_body.decode("utf-8", errors="ignore"),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "media_type": response.media_type,
            "etag": etag,
            "cached_at": time.time(),
        }

        try:
            await self.cache_manager.set_cached(cache_key, json.dumps(cache_data, ensure_ascii=False), ttl=ttl)
            logger.debug(f"响应已缓存: {request.url.path}, ttl={ttl}s, size={len(response_body)} bytes")
        except Exception as e:
            logger.warning(f"缓存写入失败 (key={cache_key}): {e}")
            self._stats["errors"] += 1

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            dict: 缓存统计信息，包含降级统计
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests * 100 if total_requests > 0 else 0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "bypassed": self._stats["bypassed"],
            "degraded": self._stats["degraded"],
            "degradation_reasons": dict(self._stats["degradation_reasons"]),
            "total_cached_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_enabled": self.cache_manager.is_enabled(),
        }

    def reset_stats(self) -> None:
        """重置缓存统计信息"""
        self._stats = {"hits": 0, "misses": 0, "errors": 0, "bypassed": 0, "degraded": 0, "degradation_reasons": {}}
        logger.info("缓存统计信息已重置")
