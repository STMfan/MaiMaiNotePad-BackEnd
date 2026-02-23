#!/usr/bin/env python3
"""
缓存配置验证脚本

用于验证缓存配置文件的正确性和合理性。
可以在部署前或配置修改后运行此脚本进行验证。

使用方法：
    python scripts/python/validate_cache_config.py [config_file]
    
示例：
    python scripts/python/validate_cache_config.py configs/config.dev.toml
    python scripts/python/validate_cache_config.py configs/config.prod.toml
    python scripts/python/validate_cache_config.py configs/config.degraded.toml
"""

import sys
import os
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def validate_config_file(config_file: str) -> bool:
    """验证配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        bool: 验证是否成功
    """
    from app.core.config_manager import ConfigManager
    from app.core.cache.config import CacheConfig, validate_cache_config
    
    print(f"\n{'='*70}")
    print(f"验证配置文件: {config_file}")
    print(f"{'='*70}\n")
    
    # 检查文件是否存在
    if not os.path.exists(config_file):
        print(f"❌ 错误: 配置文件不存在: {config_file}")
        return False
    
    try:
        # 加载配置文件
        config_manager = ConfigManager(config_file)
        
        # 提取缓存配置
        cache_config_dict = {
            "enabled": config_manager.get_bool("cache.enabled", True),
            "host": config_manager.get("cache.host", "localhost"),
            "port": config_manager.get_int("cache.port", 6379),
            "db": config_manager.get_int("cache.db", 0),
            "password": config_manager.get("cache.password", None),
            "key_prefix": config_manager.get("cache.key_prefix", "maimnp"),
            "default_ttl": config_manager.get_int("cache.default_ttl", 3600),
            "max_connections": config_manager.get_int("cache.max_connections", 10),
            "socket_timeout": config_manager.get_int("cache.socket_timeout", 5),
            "socket_connect_timeout": config_manager.get_int("cache.socket_connect_timeout", 5),
            "retry_on_timeout": config_manager.get_bool("cache.retry_on_timeout", True),
        }
        
        # 创建缓存配置实例
        cache_config = CacheConfig(**cache_config_dict)
        
        # 显示配置信息
        print("📋 缓存配置信息:")
        print(f"  - 缓存状态: {'✅ 启用' if cache_config.enabled else '⚠️  禁用（降级模式）'}")
        print(f"  - Redis 地址: {cache_config.host}:{cache_config.port}")
        print(f"  - 数据库编号: {cache_config.db}")
        print(f"  - 键前缀: {cache_config.key_prefix}")
        print(f"  - 默认 TTL: {cache_config.default_ttl} 秒")
        print(f"  - 最大连接数: {cache_config.max_connections}")
        print(f"  - Socket 超时: {cache_config.socket_timeout} 秒")
        print(f"  - 连接超时: {cache_config.socket_connect_timeout} 秒")
        print(f"  - 超时重试: {'是' if cache_config.retry_on_timeout else '否'}")
        print(f"  - 密码保护: {'是' if cache_config.password else '否'}")
        print()
        
        # 执行验证
        is_valid, warnings = validate_cache_config(cache_config)
        
        if not is_valid:
            print("❌ 配置验证失败")
            return False
        
        # 显示验证结果
        if warnings:
            print(f"⚠️  发现 {len(warnings)} 个警告:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
            print()
        else:
            print("✅ 配置验证通过，无警告")
            print()
        
        # 显示建议
        print("💡 配置建议:")
        if cache_config.enabled:
            print("  - 缓存已启用，确保 Redis 服务正常运行")
            print("  - 生产环境建议设置 REDIS_PASSWORD 环境变量")
            print("  - 定期监控缓存命中率和内存使用情况")
        else:
            print("  - 缓存已禁用，系统将直接访问数据库")
            print("  - 降级模式适用于调试或 Redis 故障时使用")
            print("  - 启用缓存可显著提升系统性能")
        print()
        
        print(f"{'='*70}")
        print("✅ 验证完成")
        print(f"{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 解析命令行参数
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        # 默认验证当前配置文件
        config_file = "configs/config.toml"
    
    # 验证配置文件
    success = validate_config_file(config_file)
    
    # 如果提供了多个配置文件，依次验证
    if len(sys.argv) > 2:
        for config_file in sys.argv[2:]:
            success = validate_config_file(config_file) and success
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
