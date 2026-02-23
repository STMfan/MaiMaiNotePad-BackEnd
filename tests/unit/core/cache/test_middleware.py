"""
缓存中间件单元测试

测试 CacheMiddleware 的核心功能，包括：
- 请求拦截和缓存键生成
- 自动缓存 GET 请求响应
- 缓存头处理（Cache-Control、ETag）
- 降级逻辑（缓存禁用时直接转发请求）
"""

import pytest
import json
import time
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.core.cache.middleware import CacheMiddleware
from app.core.cache.manager import CacheManager
from app.core.cache.redis_client import RedisClient


@pytest.fixture
def mock_redis_client():
    """创建模拟的 Redis 客户端"""
    client = AsyncMock(spec=RedisClient)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=False)
    return client


@pytest.fixture
def cache_manager_enabled(mock_redis_client):
    """创建启用缓存的缓存管理器"""
    return CacheManager(
        redis_client=mock_redis_client,
        key_prefix="test",
        enabled=True
    )


@pytest.fixture
def cache_manager_disabled():
    """创建禁用缓存的缓存管理器"""
    return CacheManager(
        redis_client=None,
        key_prefix="test",
        enabled=False
    )


@pytest.fixture
def app_with_cache(cache_manager_enabled):
    """创建带缓存中间件的 FastAPI 应用"""
    app = FastAPI()
    
    # 添加缓存中间件
    app.add_middleware(
        CacheMiddleware,
        cache_manager=cache_manager_enabled,
        default_ttl=300
    )
    
    # 添加测试路由
    @app.get("/test")
    async def test_route():
        return {"message": "Hello, World!"}
    
    @app.get("/test-with-params")
    async def test_route_with_params(name: str = "default"):
        return {"message": f"Hello, {name}!"}
    
    @app.post("/test-post")
    async def test_post_route():
        return {"message": "POST request"}
    
    return app


@pytest.fixture
def app_without_cache(cache_manager_disabled):
    """创建不带缓存的 FastAPI 应用（降级模式）"""
    app = FastAPI()
    
    # 添加缓存中间件（但缓存已禁用）
    app.add_middleware(
        CacheMiddleware,
        cache_manager=cache_manager_disabled,
        default_ttl=300
    )
    
    # 添加测试路由
    @app.get("/test")
    async def test_route():
        return {"message": "Hello, World!"}
    
    return app


class TestCacheMiddlewareBasics:
    """测试缓存中间件的基本功能"""
    
    def test_middleware_initialization(self, cache_manager_enabled):
        """测试中间件初始化"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            default_ttl=300
        )
        
        assert middleware.cache_manager == cache_manager_enabled
        assert middleware.default_ttl == 300
        assert middleware.cache_query_params is True
        assert middleware.excluded_paths == []
    
    def test_middleware_initialization_with_options(self, cache_manager_enabled):
        """测试带选项的中间件初始化"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            default_ttl=600,
            cache_query_params=False,
            excluded_paths=["/admin", "/api/internal"]
        )
        
        assert middleware.default_ttl == 600
        assert middleware.cache_query_params is False
        assert middleware.excluded_paths == ["/admin", "/api/internal"]
    
    def test_should_cache_get_request(self, cache_manager_enabled):
        """测试 GET 请求应该被缓存"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建模拟的 GET 请求
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"
        request.headers = {}
        
        assert middleware._should_cache_request(request) is True
    
    def test_should_not_cache_post_request(self, cache_manager_enabled):
        """测试 POST 请求不应该被缓存"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建模拟的 POST 请求
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/test"
        request.headers = {}
        
        assert middleware._should_cache_request(request) is False
    
    def test_should_not_cache_excluded_path(self, cache_manager_enabled):
        """测试排除路径不应该被缓存"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            excluded_paths=["/admin", "/api/internal"]
        )
        
        # 创建模拟的 GET 请求（排除路径）
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/admin/users"
        request.headers = {}
        
        assert middleware._should_cache_request(request) is False
    
    def test_should_not_cache_with_no_cache_header(self, cache_manager_enabled):
        """测试带 no-cache 头的请求不应该被缓存"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建模拟的 GET 请求（带 no-cache 头）
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"
        request.headers = {"Cache-Control": "no-cache"}
        
        assert middleware._should_cache_request(request) is False


class TestCacheKeyGeneration:
    """测试缓存键生成"""
    
    def test_build_cache_key_simple_path(self, cache_manager_enabled):
        """测试简单路径的缓存键生成"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建模拟请求
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.url.query = ""
        
        cache_key = middleware._build_cache_key(request)
        
        # 验证缓存键格式
        assert cache_key.startswith("test:http:")
        assert len(cache_key.split(":")) == 3
    
    def test_build_cache_key_with_query_params(self, cache_manager_enabled):
        """测试带查询参数的缓存键生成"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            cache_query_params=True
        )
        
        # 创建模拟请求
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.url.query = "name=alice&age=30"
        
        cache_key = middleware._build_cache_key(request)
        
        # 验证缓存键包含查询参数的哈希
        assert cache_key.startswith("test:http:")
    
    def test_build_cache_key_ignore_query_params(self, cache_manager_enabled):
        """测试忽略查询参数的缓存键生成"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            cache_query_params=False
        )
        
        # 创建模拟请求
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.url.query = "name=alice&age=30"
        
        cache_key = middleware._build_cache_key(request)
        
        # 验证缓存键不包含查询参数
        assert cache_key.startswith("test:http:")
    
    def test_cache_key_consistency(self, cache_manager_enabled):
        """测试相同请求生成相同的缓存键"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建两个相同的模拟请求
        request1 = Mock(spec=Request)
        request1.url.path = "/test"
        request1.url.query = "name=alice&age=30"
        
        request2 = Mock(spec=Request)
        request2.url.path = "/test"
        request2.url.query = "age=30&name=alice"  # 参数顺序不同
        
        cache_key1 = middleware._build_cache_key(request1)
        cache_key2 = middleware._build_cache_key(request2)
        
        # 验证缓存键相同（参数排序后）
        assert cache_key1 == cache_key2


class TestCacheHeaders:
    """测试缓存头处理"""
    
    def test_parse_cache_control(self, cache_manager_enabled):
        """测试 Cache-Control 头解析"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建模拟响应头
        headers = {"Cache-Control": "max-age=3600, public"}
        
        directives = middleware._parse_cache_control(headers)
        
        assert directives["max-age"] == "3600"
        assert directives["public"] is True
    
    def test_get_ttl_from_response_with_max_age(self, cache_manager_enabled):
        """测试从响应中提取 TTL（max-age）"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            default_ttl=300
        )
        
        # 创建模拟响应
        response = Mock(spec=Response)
        response.headers = {"Cache-Control": "max-age=3600"}
        
        ttl = middleware._get_ttl_from_response(response)
        
        assert ttl == 3600
    
    def test_get_ttl_from_response_default(self, cache_manager_enabled):
        """测试使用默认 TTL"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled,
            default_ttl=300
        )
        
        # 创建模拟响应（无 Cache-Control）
        response = Mock(spec=Response)
        response.headers = {}
        
        ttl = middleware._get_ttl_from_response(response)
        
        assert ttl == 300
    
    def test_get_ttl_from_response_no_store(self, cache_manager_enabled):
        """测试 no-store 指令返回 None"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 创建模拟响应（no-store）
        response = Mock(spec=Response)
        response.headers = {"Cache-Control": "no-store"}
        
        ttl = middleware._get_ttl_from_response(response)
        
        assert ttl is None
    
    def test_generate_etag(self, cache_manager_enabled):
        """测试 ETag 生成"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        content = b"Hello, World!"
        etag = middleware._generate_etag(content)
        
        # 验证 ETag 是 MD5 哈希
        assert isinstance(etag, str)
        assert len(etag) == 32  # MD5 哈希长度


class TestCacheDegradation:
    """测试缓存降级逻辑"""
    
    def test_degradation_when_cache_disabled(self, app_without_cache):
        """测试缓存禁用时的降级行为"""
        client = TestClient(app_without_cache)
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证请求被绕过（不缓存）
        assert "X-Cache" not in response.headers or response.headers.get("X-Cache") == "MISS"


class TestCacheStats:
    """测试缓存统计信息"""
    
    def test_get_stats_initial(self, cache_manager_enabled):
        """测试初始统计信息"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        stats = middleware.get_stats()
        
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["errors"] == 0
        assert stats["bypassed"] == 0
        assert stats["degraded"] == 0
        assert stats["degradation_reasons"] == {}
        assert stats["total_cached_requests"] == 0
        assert stats["hit_rate"] == "0.00%"
        assert stats["cache_enabled"] is True
    
    def test_reset_stats(self, cache_manager_enabled):
        """测试重置统计信息"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 修改统计信息
        middleware._stats["hits"] = 10
        middleware._stats["misses"] = 5
        middleware._stats["degraded"] = 3
        middleware._stats["degradation_reasons"] = {"cache_disabled": 2, "redis_connection_failed": 1}
        
        # 重置统计信息
        middleware.reset_stats()
        
        stats = middleware.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["degraded"] == 0
        assert stats["degradation_reasons"] == {}
    
    def test_degradation_stats_recording(self, cache_manager_enabled):
        """测试降级统计记录"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_enabled
        )
        
        # 记录降级事件
        middleware._record_degradation("cache_disabled")
        middleware._record_degradation("cache_disabled")
        middleware._record_degradation("redis_connection_failed")
        
        stats = middleware.get_stats()
        
        assert stats["degraded"] == 3
        assert stats["degradation_reasons"]["cache_disabled"] == 2
        assert stats["degradation_reasons"]["redis_connection_failed"] == 1
    
    def test_get_stats_with_degradation(self, cache_manager_disabled):
        """测试禁用缓存时的统计信息"""
        app = FastAPI()
        middleware = CacheMiddleware(
            app=app,
            cache_manager=cache_manager_disabled
        )
        
        stats = middleware.get_stats()
        
        assert stats["cache_enabled"] is False
        assert stats["degraded"] == 0
        assert stats["degradation_reasons"] == {}


class TestCacheMiddlewareIntegration:
    """测试缓存中间件的集成场景"""
    
    @pytest.mark.asyncio
    async def test_cache_miss_and_set(self, app_with_cache, mock_redis_client):
        """测试缓存未命中并设置缓存"""
        client = TestClient(app_with_cache)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
        
        # 验证 ETag 头存在
        assert "ETag" in response.headers
        
        # 验证响应时间头存在
        assert "X-Response-Time" in response.headers
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, app_with_cache, mock_redis_client):
        """测试缓存命中"""
        client = TestClient(app_with_cache)
        
        # 模拟缓存命中
        # CacheManager.get_cached 会返回反序列化后的数据（字符串）
        cached_data = {
            "content": '{"message": "Hello, World!"}',
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "media_type": "application/json",
            "etag": "abc123",
            "cached_at": time.time()
        }
        # 模拟 redis_client.get 返回的是双重序列化的数据
        # CacheManager.get_cached 会反序列化一次，返回 JSON 字符串
        mock_redis_client.get.return_value = json.dumps(json.dumps(cached_data, ensure_ascii=False), ensure_ascii=False).encode()
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证缓存命中标识
        assert response.headers.get("X-Cache") == "HIT"
    
    @pytest.mark.asyncio
    async def test_etag_304_not_modified(self, app_with_cache, mock_redis_client):
        """测试 ETag 匹配返回 304"""
        client = TestClient(app_with_cache)
        
        # 模拟缓存命中
        cached_data = {
            "content": '{"message": "Hello, World!"}',
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "media_type": "application/json",
            "etag": "abc123",
            "cached_at": time.time()
        }
        # 模拟 redis_client.get 返回的是双重序列化的数据
        mock_redis_client.get.return_value = json.dumps(json.dumps(cached_data, ensure_ascii=False), ensure_ascii=False).encode()
        
        # 发送带 If-None-Match 头的请求
        response = client.get("/test", headers={"If-None-Match": "abc123"})
        
        # 验证返回 304
        assert response.status_code == 304
        assert "ETag" in response.headers
    
    @pytest.mark.asyncio
    async def test_cache_corrupted_data(self, app_with_cache, mock_redis_client):
        """测试缓存数据损坏的处理"""
        client = TestClient(app_with_cache)
        
        # 模拟损坏的缓存数据
        mock_redis_client.get.return_value = "invalid json data"
        mock_redis_client.delete.return_value = True
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常（降级到实际请求）
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
        
        # 验证损坏的缓存被删除
        mock_redis_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, app_with_cache, mock_redis_client):
        """测试 Redis 连接失败时的降级"""
        client = TestClient(app_with_cache)
        
        # 模拟 Redis 连接失败
        mock_redis_client.get.side_effect = Exception("Connection refused")
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常（降级到实际请求）
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
    
    @pytest.mark.asyncio
    async def test_cache_write_failure(self, app_with_cache, mock_redis_client):
        """测试缓存写入失败的处理"""
        client = TestClient(app_with_cache)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        # 模拟缓存写入失败
        mock_redis_client.set.side_effect = Exception("Write failed")
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常（即使缓存写入失败）
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
    
    @pytest.mark.asyncio
    async def test_post_request_not_cached(self, app_with_cache):
        """测试 POST 请求不被缓存"""
        client = TestClient(app_with_cache)
        
        # 发送 POST 请求
        response = client.post("/test-post")
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "POST request"}
        
        # 验证没有缓存相关的头
        assert "X-Cache" not in response.headers
    
    @pytest.mark.asyncio
    async def test_query_params_in_cache_key(self, app_with_cache, mock_redis_client):
        """测试查询参数影响缓存键"""
        client = TestClient(app_with_cache)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        
        # 发送带不同查询参数的请求
        response1 = client.get("/test-with-params?name=alice")
        response2 = client.get("/test-with-params?name=bob")
        
        # 验证两个请求都正常
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # 验证返回不同的内容
        assert response1.json() == {"message": "Hello, alice!"}
        assert response2.json() == {"message": "Hello, bob!"}
    
    @pytest.mark.asyncio
    async def test_no_cache_header_bypass(self, app_with_cache):
        """测试 no-cache 头绕过缓存"""
        client = TestClient(app_with_cache)
        
        # 发送带 no-cache 头的请求
        response = client.get("/test", headers={"Cache-Control": "no-cache"})
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
        
        # 验证没有缓存相关的头
        assert "X-Cache" not in response.headers
    
    @pytest.mark.asyncio
    async def test_cache_with_custom_ttl(self, cache_manager_enabled, mock_redis_client):
        """测试自定义 TTL"""
        app = FastAPI()
        
        # 添加缓存中间件（自定义 TTL）
        app.add_middleware(
            CacheMiddleware,
            cache_manager=cache_manager_enabled,
            default_ttl=600  # 10 分钟
        )
        
        # 添加测试路由
        @app.get("/test")
        async def test_route():
            return {"message": "Hello, World!"}
        
        client = TestClient(app)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
    
    @pytest.mark.asyncio
    async def test_excluded_path_not_cached(self, cache_manager_enabled):
        """测试排除路径不被缓存"""
        app = FastAPI()
        
        # 添加缓存中间件（排除 /admin 路径）
        app.add_middleware(
            CacheMiddleware,
            cache_manager=cache_manager_enabled,
            excluded_paths=["/admin"]
        )
        
        # 添加测试路由
        @app.get("/admin/users")
        async def admin_route():
            return {"message": "Admin page"}
        
        client = TestClient(app)
        
        # 发送 GET 请求
        response = client.get("/admin/users")
        
        # 验证响应正常
        assert response.status_code == 200
        assert response.json() == {"message": "Admin page"}
        
        # 验证没有缓存相关的头
        assert "X-Cache" not in response.headers


class TestCacheMiddlewareEdgeCases:
    """测试缓存中间件的边缘情况"""
    
    @pytest.mark.asyncio
    async def test_cache_with_no_store_directive(self, cache_manager_enabled, mock_redis_client):
        """测试 no-store 指令不缓存响应"""
        app = FastAPI()
        
        app.add_middleware(
            CacheMiddleware,
            cache_manager=cache_manager_enabled
        )
        
        # 添加测试路由（返回 no-store 头）
        @app.get("/test")
        async def test_route():
            return Response(
                content='{"message": "Hello, World!"}',
                media_type="application/json",
                headers={"Cache-Control": "no-store"}
            )
        
        client = TestClient(app)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 200
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
        
        # 验证没有调用 set（因为 no-store）
        # 注意：由于 TTL 为 None，不会调用 set
    
    @pytest.mark.asyncio
    async def test_cache_with_max_age_directive(self, cache_manager_enabled, mock_redis_client):
        """测试 max-age 指令设置 TTL"""
        app = FastAPI()
        
        app.add_middleware(
            CacheMiddleware,
            cache_manager=cache_manager_enabled,
            default_ttl=300
        )
        
        # 添加测试路由（返回 max-age 头）
        @app.get("/test")
        async def test_route():
            return Response(
                content='{"message": "Hello, World!"}',
                media_type="application/json",
                headers={"Cache-Control": "max-age=3600"}
            )
        
        client = TestClient(app)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 200
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
    
    @pytest.mark.asyncio
    async def test_cache_4xx_response_not_cached(self, cache_manager_enabled, mock_redis_client):
        """测试 4xx 响应不被缓存"""
        app = FastAPI()
        
        app.add_middleware(
            CacheMiddleware,
            cache_manager=cache_manager_enabled
        )
        
        # 添加测试路由（返回 404）
        @app.get("/test")
        async def test_route():
            return Response(
                content='{"error": "Not found"}',
                status_code=404,
                media_type="application/json"
            )
        
        client = TestClient(app)
        
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        
        # 发送 GET 请求
        response = client.get("/test")
        
        # 验证响应正常
        assert response.status_code == 404
        
        # 验证缓存未命中标识
        assert response.headers.get("X-Cache") == "MISS"
        
        # 验证没有调用 set（因为状态码不是 2xx）
        # 注意：由于状态码是 404，不会缓存
