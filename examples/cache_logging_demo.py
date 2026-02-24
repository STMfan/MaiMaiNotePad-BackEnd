"""
缓存日志记录演示

展示如何使用缓存日志记录功能，包括各种操作的日志输出。
"""

import asyncio
import json
import logging

from app.core.cache import CacheManager, RedisClient


# 配置 JSON 格式的日志输出
class JsonFormatter(logging.Formatter):
    """JSON 格式的日志格式化器"""

    def format(self, record):
        # 如果日志消息已经是 JSON 格式，直接返回
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            # 否则使用标准格式
            return super().format(record)


def setup_logging():
    """配置日志系统"""
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())

    # 配置缓存日志记录器
    cache_logger = logging.getLogger("app.core.cache")
    cache_logger.addHandler(console_handler)
    cache_logger.setLevel(logging.INFO)

    print("=" * 80)
    print("缓存日志记录演示")
    print("=" * 80)
    print()


async def demo_cache_operations():
    """演示缓存操作的日志记录"""

    print("场景 1: 缓存启用 - 正常操作")
    print("-" * 80)

    # 创建 Redis 客户端（假设 Redis 正在运行）
    try:
        redis_client = RedisClient(host="localhost", port=6379)
        cache_manager = CacheManager(
            redis_client=redis_client,
            key_prefix="demo",
            enabled=True
        )

        # 1. 缓存设置
        print("\n1. 设置缓存:")
        await cache_manager.set_cached(
            "user:123",
            {"id": "123", "name": "Alice"},
            ttl=3600
        )

        # 2. 缓存命中
        print("\n2. 缓存命中:")
        await cache_manager.get_cached("user:123")

        # 3. 缓存未命中（带 fetch_func）
        print("\n3. 缓存未命中（自动获取数据）:")
        async def fetch_user():
            return {"id": "456", "name": "Bob"}

        await cache_manager.get_cached(
            "user:456",
            fetch_func=fetch_user,
            ttl=3600
        )

        # 4. 缓存失效
        print("\n4. 单键失效:")
        await cache_manager.invalidate("user:123")

        # 5. 批量失效
        print("\n5. 批量失效:")
        await cache_manager.invalidate_pattern("demo:user:*")

        # 清理
        await redis_client.close()

    except Exception as e:
        print(f"\n注意: Redis 连接失败 ({e})")
        print("这将演示降级场景...")

    print("\n" + "=" * 80)
    print("场景 2: 缓存禁用 - 降级模式")
    print("-" * 80)

    # 创建禁用的缓存管理器
    cache_manager_disabled = CacheManager(
        redis_client=None,
        key_prefix="demo",
        enabled=False
    )

    # 6. 缓存禁用时的操作
    print("\n6. 缓存禁用时获取数据:")
    async def fetch_data():
        return {"id": "789", "name": "Charlie"}

    await cache_manager_disabled.get_cached(
        "user:789",
        fetch_func=fetch_data
    )

    print("\n7. 缓存禁用时设置缓存:")
    await cache_manager_disabled.set_cached(
        "user:789",
        {"id": "789", "name": "Charlie"}
    )

    print("\n8. 缓存禁用时失效缓存:")
    await cache_manager_disabled.invalidate("user:789")

    print("\n" + "=" * 80)
    print("场景 3: Redis 故障 - 自动降级")
    print("-" * 80)

    # 创建一个会失败的 Redis 客户端
    redis_client_fail = RedisClient(host="invalid-host", port=9999)
    cache_manager_fail = CacheManager(
        redis_client=redis_client_fail,
        key_prefix="demo",
        enabled=True
    )

    print("\n9. Redis 故障时获取数据（自动降级）:")
    await cache_manager_fail.get_cached(
        "user:999",
        fetch_func=fetch_data
    )

    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


async def demo_log_analysis():
    """演示日志分析"""
    print("\n\n" + "=" * 80)
    print("日志分析示例")
    print("=" * 80)

    print("""
日志分析命令示例：

1. 查看所有降级事件：
   cat logs/cache.log | jq 'select(.operation == "cache_degradation")'

2. 统计缓存命中率：
   cat logs/cache.log | jq 'select(.operation == "cache_get") | .hit' | \\
     awk '{hit+=$1; total++} END {print "命中率:", hit/total*100"%"}'

3. 查看平均延迟：
   cat logs/cache.log | jq 'select(.latency_ms) | .latency_ms' | \\
     awk '{sum+=$1; count++} END {print "平均延迟:", sum/count, "ms"}'

4. 查看降级原因统计：
   cat logs/cache.log | jq -r 'select(.operation == "cache_degradation") | .reason' | \\
     sort | uniq -c | sort -rn

5. 查看错误日志：
   cat logs/cache.log | jq 'select(.level == "WARNING" or .level == "ERROR")'
""")


def main():
    """主函数"""
    # 配置日志
    setup_logging()

    # 运行演示
    asyncio.run(demo_cache_operations())
    asyncio.run(demo_log_analysis())


if __name__ == "__main__":
    main()
