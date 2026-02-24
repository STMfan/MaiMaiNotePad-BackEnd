"""
缓存失效模块

提供通用的自动缓存失效机制，在数据更新时自动清除相关缓存。
支持同步和异步环境。
"""

import asyncio
from typing import Optional, List
from app.core.logging import app_logger as logger


def invalidate_cache_sync(cache_manager, patterns: List[str]):
    """
    同步方式失效缓存（用于同步代码中）
    
    Args:
        cache_manager: 缓存管理器实例
        patterns: 要失效的缓存模式列表
    """
    try:
        # 尝试获取当前运行的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用 create_task 异步执行
            for pattern in patterns:
                asyncio.create_task(_async_invalidate_pattern(cache_manager, pattern))
        except RuntimeError:
            # 没有运行的事件循环，创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            for pattern in patterns:
                try:
                    loop.run_until_complete(cache_manager.invalidate_pattern(pattern))
                    logger.info(f"已清除缓存: pattern={pattern}")
                except Exception as e:
                    logger.warning(f"清除缓存失败 (pattern={pattern}): {e}")
            
            loop.close()
        
    except Exception as e:
        logger.error(f"缓存失效操作失败: {e}")


async def _async_invalidate_pattern(cache_manager, pattern: str):
    """
    异步清除缓存模式（内部辅助函数）
    
    Args:
        cache_manager: 缓存管理器实例
        pattern: 缓存模式
    """
    try:
        await cache_manager.invalidate_pattern(pattern)
        logger.info(f"已清除缓存: pattern={pattern}")
    except Exception as e:
        logger.warning(f"清除缓存失败 (pattern={pattern}): {e}")


# ============================================================================
# 业务特定的缓存失效函数
# ============================================================================

def invalidate_persona_cache(pc_id: Optional[str] = None):
    """
    失效人设卡相关的缓存
    
    Args:
        pc_id: 人设卡ID（可选），如果提供则只清除特定人设卡的缓存
    """
    from app.core.cache.factory import get_cache_manager
    
    cache_manager = get_cache_manager()
    if not cache_manager.is_enabled():
        return
    
    patterns = [
        "maimnp:http:*persona/public*",  # 所有公开人设卡列表的缓存
    ]
    
    if pc_id:
        # 如果指定了人设卡ID，还要清除该人设卡详情的缓存
        patterns.append(f"maimnp:http:*persona/{pc_id}*")
    
    invalidate_cache_sync(cache_manager, patterns)


def invalidate_knowledge_cache(kb_id: Optional[str] = None, uploader_id: Optional[str] = None):
    """
    失效知识库相关的缓存
    
    Args:
        kb_id: 知识库ID（可选），如果提供则清除特定知识库的缓存
        uploader_id: 上传者ID（可选），如果提供则清除该用户的知识库列表缓存
    """
    from app.core.cache.factory import get_cache_manager
    
    cache_manager = get_cache_manager()
    if not cache_manager.is_enabled():
        return
    
    patterns = [
        "maimnp:kb:public:*",  # 公开知识库列表的缓存
    ]
    
    if kb_id:
        # 清除特定知识库详情的缓存
        patterns.append(f"maimnp:http:*knowledge/{kb_id}*")
    
    if uploader_id:
        # 清除用户知识库列表的缓存
        patterns.append(f"maimnp:kb:user:{uploader_id}:*")
    
    invalidate_cache_sync(cache_manager, patterns)


def invalidate_user_cache(user_id: Optional[str] = None):
    """
    失效用户相关的缓存
    
    Args:
        user_id: 用户ID（可选），如果不提供则清除所有用户相关缓存
    """
    from app.core.cache.factory import get_cache_manager
    
    cache_manager = get_cache_manager()
    if not cache_manager.is_enabled():
        return
    
    patterns = []
    
    if user_id:
        patterns.extend([
            f"maimnp:http:*users/{user_id}*",  # 用户详情的缓存
            f"user:{user_id}",  # 用户数据的缓存
        ])
    else:
        # 清除所有用户相关缓存
        patterns.extend([
            "maimnp:http:*users*",
            "user:*",
        ])
    
    invalidate_cache_sync(cache_manager, patterns)


def invalidate_message_cache(message_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    失效消息相关的缓存
    
    Args:
        message_id: 消息ID（可选）
        user_id: 用户ID（可选），清除该用户的消息列表缓存
    """
    from app.core.cache.factory import get_cache_manager
    
    cache_manager = get_cache_manager()
    if not cache_manager.is_enabled():
        return
    
    patterns = [
        "maimnp:http:*messages*",  # 清除所有消息相关缓存
    ]
    
    if message_id:
        patterns.append(f"maimnp:http:*messages/{message_id}*")
    
    if user_id:
        patterns.append(f"maimnp:http:*messages*user_id={user_id}*")
    
    invalidate_cache_sync(cache_manager, patterns)


def invalidate_comment_cache(comment_id: Optional[str] = None, target_id: Optional[str] = None):
    """
    失效评论相关的缓存
    
    Args:
        comment_id: 评论ID（可选）
        target_id: 目标ID（可选），清除该目标的评论列表缓存
    """
    from app.core.cache.factory import get_cache_manager
    
    cache_manager = get_cache_manager()
    if not cache_manager.is_enabled():
        return
    
    patterns = [
        "maimnp:http:*comments*",  # 清除所有评论相关缓存
    ]
    
    if comment_id:
        patterns.append(f"maimnp:http:*comments/{comment_id}*")
    
    if target_id:
        patterns.append(f"maimnp:http:*comments*target_id={target_id}*")
    
    invalidate_cache_sync(cache_manager, patterns)


def auto_invalidate_cache(cache_patterns: List[str]):
    """
    装饰器：在函数执行成功后自动失效指定模式的缓存
    
    Args:
        cache_patterns: 要失效的缓存模式列表
        
    Example:
        @auto_invalidate_cache(["maimnp:http:*persona/public*"])
        def update_persona_card(self, pc_id: str, data: dict):
            # 更新逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 如果函数执行成功，清除缓存
            # 对于返回 (success, message, data) 的函数
            if isinstance(result, tuple) and len(result) >= 1:
                success = result[0]
                if success:
                    try:
                        from app.core.cache.factory import get_cache_manager
                        cache_manager = get_cache_manager()
                        
                        if cache_manager.is_enabled():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            for pattern in cache_patterns:
                                try:
                                    loop.run_until_complete(cache_manager.invalidate_pattern(pattern))
                                    logger.debug(f"自动清除缓存: pattern={pattern}")
                                except Exception as e:
                                    logger.warning(f"自动清除缓存失败 (pattern={pattern}): {e}")
                            
                            loop.close()
                    except Exception as e:
                        logger.error(f"自动缓存失效失败: {e}")
            
            return result
        
        return wrapper
    return decorator
