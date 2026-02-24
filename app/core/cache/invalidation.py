"""
缓存失效模块

提供自动缓存失效机制，在数据更新时自动清除相关缓存。
"""

import asyncio
import hashlib
from functools import wraps
from typing import Callable, Optional, List
from app.core.logging import app_logger as logger


def invalidate_persona_cache(cache_manager, pc_id: Optional[str] = None):
    """
    失效人设卡相关的缓存
    
    Args:
        cache_manager: 缓存管理器实例
        pc_id: 人设卡ID（可选），如果提供则只清除特定人设卡的缓存
    """
    try:
        # 清除公开人设卡列表的所有缓存（包括不同的查询参数组合）
        # 使用通配符模式匹配所有相关的缓存键
        patterns = [
            "maimnp:http:*persona/public*",  # 所有公开人设卡列表的缓存
        ]
        
        if pc_id:
            # 如果指定了人设卡ID，还要清除该人设卡详情的缓存
            patterns.append(f"maimnp:http:*persona/{pc_id}*")
        
        # 异步清除缓存
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for pattern in patterns:
            try:
                loop.run_until_complete(cache_manager.clear_pattern(pattern))
                logger.info(f"已清除缓存: pattern={pattern}")
            except Exception as e:
                logger.warning(f"清除缓存失败 (pattern={pattern}): {e}")
        
        loop.close()
        
    except Exception as e:
        logger.error(f"缓存失效操作失败: {e}")


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
                                    loop.run_until_complete(cache_manager.clear_pattern(pattern))
                                    logger.debug(f"自动清除缓存: pattern={pattern}")
                                except Exception as e:
                                    logger.warning(f"自动清除缓存失败 (pattern={pattern}): {e}")
                            
                            loop.close()
                    except Exception as e:
                        logger.error(f"自动缓存失效失败: {e}")
            
            return result
        
        return wrapper
    return decorator
