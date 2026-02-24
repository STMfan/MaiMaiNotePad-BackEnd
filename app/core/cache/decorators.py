"""
缓存装饰器

提供声明式缓存，简化服务层集成，支持自动降级。
"""

import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def cached(key_pattern: str, ttl: int = 3600, key_builder: Callable | None = None):
    """缓存装饰器

    自动缓存函数返回值，支持参数化键生成和自动降级。

    降级行为：
    - 缓存禁用时，直接执行被装饰的函数
    - Redis 连接失败时，自动降级到原函数
    - 对被装饰函数的调用方完全透明

    Args:
        key_pattern: 缓存键模板，如 "user:{user_id}"
        ttl: 过期时间（秒），默认 3600（1小时）
        key_builder: 自定义键构建函数，接收函数参数并返回缓存键

    Returns:
        装饰器函数

    Example:
        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user_by_id(user_id: str) -> Optional[User]:
            return db.query(User).filter(User.id == user_id).first()
    """

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            return _create_async_cached_wrapper(func, key_pattern, ttl, key_builder)
        else:
            return _create_sync_cached_wrapper(func)

    return decorator


def _create_async_cached_wrapper(func: Callable, key_pattern: str, ttl: int, key_builder: Callable | None) -> Callable:
    """创建异步缓存包装器"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        from app.core.cache.factory import get_cache_manager

        cache_manager = get_cache_manager()

        # 缓存禁用，直接执行原函数
        if not cache_manager.is_enabled():
            return await func(*args, **kwargs)

        # 构建缓存键
        cache_key = _safe_build_cache_key(key_pattern, key_builder, func, args, kwargs)
        if cache_key is None:
            return await func(*args, **kwargs)

        # 尝试从缓存获取
        cached_result = await _try_get_from_cache(cache_manager, cache_key)
        if cached_result is not None:
            return cached_result

        # 执行原函数并缓存结果
        result = await func(*args, **kwargs)
        await _try_cache_result(cache_manager, cache_key, result, ttl)

        return result

    return async_wrapper


def _create_sync_cached_wrapper(func: Callable) -> Callable:
    """创建同步函数包装器（不支持缓存）"""

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        logger.warning(f"@cached 装饰器不支持同步函数 ({func.__name__})，请将函数改为异步函数")
        return func(*args, **kwargs)

    return sync_wrapper


def _safe_build_cache_key(
    key_pattern: str, key_builder: Callable | None, func: Callable, args: tuple, kwargs: dict
) -> str | None:
    """安全地构建缓存键"""
    try:
        if key_builder is not None:
            return key_builder(*args, **kwargs)
        else:
            return _build_cache_key(key_pattern, func, args, kwargs)
    except Exception as e:
        logger.warning(f"缓存键构建失败，降级到原函数: {e}")
        return None


async def _try_get_from_cache(cache_manager, cache_key: str) -> Any | None:
    """尝试从缓存获取数据"""
    try:
        cached_result = await cache_manager.get_cached(cache_key)
        if cached_result is not None:
            logger.debug(f"缓存命中: {cache_key}")
            return cached_result
    except Exception as e:
        logger.warning(f"缓存读取失败，降级到原函数 (key={cache_key}): {e}")
    return None


async def _try_cache_result(cache_manager, cache_key: str, result: Any, ttl: int) -> None:
    """尝试缓存结果"""
    try:
        await cache_manager.set_cached(cache_key, result, ttl)
        logger.debug(f"缓存写入成功: {cache_key}")
    except Exception as e:
        logger.warning(f"缓存写入失败 (key={cache_key}): {e}")


def cache_invalidate(key_pattern: str, key_builder: Callable | None = None):
    """缓存失效装饰器

    在函数执行后自动使缓存失效。

    降级行为：
    - 缓存禁用时，跳过失效操作
    - Redis 连接失败时，记录日志但不影响函数执行

    Args:
        key_pattern: 缓存键模板，如 "user:{user_id}"
        key_builder: 自定义键构建函数，接收函数参数并返回缓存键

    Returns:
        装饰器函数

    Example:
        @cache_invalidate(key_pattern="user:{user_id}")
        async def update_user(user_id: str, data: dict) -> User:
            user = db.query(User).filter(User.id == user_id).first()
            for key, value in data.items():
                setattr(user, key, value)
            db.commit()
            return user
    """

    def decorator(func: Callable) -> Callable:
        # 检查是否为异步函数
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                # 延迟导入以避免循环依赖
                from app.core.cache.factory import get_cache_manager

                # 执行原函数
                result = await func(*args, **kwargs)

                cache_manager = get_cache_manager()

                # 步骤 0: 检查缓存是否启用
                if not cache_manager.is_enabled():
                    # 缓存禁用，跳过失效操作
                    return result

                # 步骤 1: 构建缓存键
                try:
                    if key_builder is not None:
                        # 使用自定义键构建函数
                        cache_key = key_builder(*args, **kwargs)
                    else:
                        # 使用默认键构建逻辑
                        cache_key = _build_cache_key(key_pattern, func, args, kwargs)

                    # 步骤 2: 使缓存失效
                    await cache_manager.invalidate(cache_key)
                    logger.debug(f"缓存失效成功: {cache_key}")

                except Exception as e:
                    # 缓存失效失败，记录日志但不影响返回结果
                    logger.warning(f"缓存失效失败: {e}")

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                # 同步函数不支持缓存失效（因为 Redis 操作是异步的）
                logger.warning(f"@cache_invalidate 装饰器不支持同步函数 ({func.__name__})，" "请将函数改为异步函数")
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


def _build_cache_key(key_pattern: str, func: Callable, args: tuple, kwargs: dict) -> str:
    """构建缓存键

    根据 key_pattern 和函数参数构建缓存键。
    支持位置参数和关键字参数。

    Args:
        key_pattern: 缓存键模板，如 "user:{user_id}"
        func: 被装饰的函数
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        str: 构建的缓存键

    Raises:
        ValueError: 如果无法从参数中提取所需的值
    """
    # 获取函数签名
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())

    # 检测是否是绑定方法（bound method）
    # 如果是绑定方法，args 的第一个元素是 self，但签名中已经不包含 self
    # 需要跳过 args 的第一个元素
    is_bound_method = hasattr(func, "__self__") or (  # 绑定方法有 __self__ 属性
        len(args) > 0 and len(param_names) > 0 and len(args) > len(param_names)
    )  # args 比参数多（可能包含 self）

    # 如果是绑定方法且 args 第一个元素看起来像 self，跳过它
    if is_bound_method and len(args) > len(param_names):
        args = args[1:]  # 跳过第一个参数（self 或 cls）

    # 构建参数字典（合并位置参数和关键字参数）
    bound_args = {}

    # 处理位置参数
    for i, arg_value in enumerate(args):
        if i < len(param_names):
            param_name = param_names[i]
            bound_args[param_name] = arg_value

    # 处理关键字参数
    bound_args.update(kwargs)

    # 使用参数字典格式化 key_pattern
    try:
        cache_key = key_pattern.format(**bound_args)
        return cache_key
    except KeyError as e:
        raise ValueError(
            f"无法构建缓存键：key_pattern '{key_pattern}' 中的占位符 {e} "
            f"在函数参数中不存在。可用参数：{list(bound_args.keys())}"
        ) from e
