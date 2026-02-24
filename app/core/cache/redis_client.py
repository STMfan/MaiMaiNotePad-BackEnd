"""
Redis 客户端封装

提供统一的 Redis 连接管理和基础操作接口，支持异步操作和自动重连。
"""

import logging

from redis import asyncio as aioredis
from redis.exceptions import (
    AuthenticationError,
    RedisError,
)
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)
from redis.exceptions import (
    TimeoutError as RedisTimeoutError,
)

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装类

    提供异步 Redis 操作接口，支持连接池管理、健康检查和自动重连。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        max_connections: int = 10,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        decode_responses: bool = True,
    ):
        """初始化 Redis 客户端

        Args:
            host: Redis 服务器地址
            port: Redis 服务器端口
            db: Redis 数据库编号
            password: Redis 密码（可选）
            max_connections: 连接池最大连接数
            socket_timeout: Socket 超时时间（秒）
            socket_connect_timeout: 连接超时时间（秒）
            retry_on_timeout: 超时时是否重试
            decode_responses: 是否自动解码响应为字符串
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.decode_responses = decode_responses

        self._client: aioredis.Redis | None = None
        self._connection_pool: aioredis.ConnectionPool | None = None
        self._is_connected = False

        logger.info(f"Redis 客户端初始化: {host}:{port}, db={db}, " f"max_connections={max_connections}")

    async def _ensure_connection(self) -> None:
        """确保 Redis 连接已建立

        如果连接未建立或已断开，则创建新连接。

        Raises:
            ConnectionError: 连接失败
            AuthenticationError: 认证失败
        """
        if self._client is not None and self._is_connected:
            return

        try:
            # 创建连接池
            self._connection_pool = aioredis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=self.decode_responses,
            )

            # 创建 Redis 客户端
            self._client = aioredis.Redis(connection_pool=self._connection_pool)

            # 测试连接
            await self._client.ping()
            self._is_connected = True

            logger.info(f"Redis 连接成功: {self.host}:{self.port}")

        except AuthenticationError as e:
            logger.error(f"Redis 认证失败: {e}")
            self._is_connected = False
            raise
        except RedisConnectionError as e:
            logger.error(f"Redis 连接失败: {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis 连接异常: {e}")
            self._is_connected = False
            raise RedisConnectionError(f"Redis 连接失败: {e}") from e

    async def get(self, key: str) -> str | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在则返回 None

        Raises:
            ConnectionError: 连接失败
            TimeoutError: 操作超时
        """
        try:
            await self._ensure_connection()
            value = await self._client.get(key)
            return value
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis GET 操作失败 (key={key}): {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis GET 操作异常 (key={key}): {e}")
            raise RedisError(f"GET 操作失败: {e}") from e

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 表示永不过期

        Returns:
            操作是否成功

        Raises:
            ConnectionError: 连接失败
            TimeoutError: 操作超时
        """
        try:
            await self._ensure_connection()

            if ttl is not None:
                result = await self._client.setex(key, ttl, value)
            else:
                result = await self._client.set(key, value)

            return bool(result)
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis SET 操作失败 (key={key}): {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis SET 操作异常 (key={key}): {e}")
            raise RedisError(f"SET 操作失败: {e}") from e

    async def delete(self, key: str) -> bool:
        """删除缓存键

        Args:
            key: 缓存键

        Returns:
            操作是否成功（键存在且被删除返回 True）

        Raises:
            ConnectionError: 连接失败
            TimeoutError: 操作超时
        """
        try:
            await self._ensure_connection()
            result = await self._client.delete(key)
            return result > 0
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis DELETE 操作失败 (key={key}): {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis DELETE 操作异常 (key={key}): {e}")
            raise RedisError(f"DELETE 操作失败: {e}") from e

    async def exists(self, key: str) -> bool:
        """检查键是否存在

        Args:
            key: 缓存键

        Returns:
            键是否存在

        Raises:
            ConnectionError: 连接失败
            TimeoutError: 操作超时
        """
        try:
            await self._ensure_connection()
            result = await self._client.exists(key)
            return result > 0
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis EXISTS 操作失败 (key={key}): {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis EXISTS 操作异常 (key={key}): {e}")
            raise RedisError(f"EXISTS 操作失败: {e}") from e

    async def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间

        Args:
            key: 缓存键
            ttl: 过期时间（秒）

        Returns:
            操作是否成功（键存在且设置成功返回 True）

        Raises:
            ConnectionError: 连接失败
            TimeoutError: 操作超时
        """
        try:
            await self._ensure_connection()
            result = await self._client.expire(key, ttl)
            return bool(result)
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis EXPIRE 操作失败 (key={key}): {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis EXPIRE 操作异常 (key={key}): {e}")
            raise RedisError(f"EXPIRE 操作失败: {e}") from e

    async def delete_pattern(self, pattern: str) -> int:
        """批量删除匹配模式的键

        使用 SCAN 命令遍历键，避免阻塞 Redis。

        Args:
            pattern: 键模式（支持 * 通配符）

        Returns:
            删除的键数量

        Raises:
            ConnectionError: 连接失败
            TimeoutError: 操作超时
        """
        try:
            await self._ensure_connection()

            deleted_count = 0
            cursor = 0

            # 使用 SCAN 命令遍历匹配的键
            while True:
                cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)

                if keys:
                    # 批量删除键
                    batch_deleted = await self._client.delete(*keys)
                    deleted_count += batch_deleted

                # cursor 为 0 表示遍历完成
                if cursor == 0:
                    break

            logger.info(f"批量删除缓存: pattern={pattern}, count={deleted_count}")
            return deleted_count

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis DELETE_PATTERN 操作失败 (pattern={pattern}): {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN 操作异常 (pattern={pattern}): {e}")
            raise RedisError(f"DELETE_PATTERN 操作失败: {e}") from e

    async def ping(self) -> bool:
        """健康检查

        Returns:
            连接是否正常
        """
        try:
            await self._ensure_connection()
            result = await self._client.ping()
            return result is True
        except Exception as e:
            logger.warning(f"Redis PING 失败: {e}")
            self._is_connected = False
            return False

    async def close(self) -> None:
        """关闭连接

        释放连接池资源。
        """
        if self._client is not None:
            try:
                await self._client.aclose()  # 使用 aclose() 替代 close()
                logger.info("Redis 连接已关闭")
            except Exception as e:
                logger.error(f"关闭 Redis 连接时出错: {e}")
            finally:
                self._client = None
                self._is_connected = False

        if self._connection_pool is not None:
            try:
                await self._connection_pool.disconnect()
            except Exception as e:
                logger.error(f"关闭 Redis 连接池时出错: {e}")
            finally:
                self._connection_pool = None

    def __del__(self):
        """析构函数，确保连接被关闭"""
        if self._client is not None or self._connection_pool is not None:
            # 注意：在析构函数中不能使用 await
            # 这里只是记录警告，实际关闭应该在应用关闭时显式调用 close()
            logger.warning("Redis 客户端未正确关闭，请在应用关闭时调用 close()")
