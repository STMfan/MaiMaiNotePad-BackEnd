# 缓存统计API文档

> 缓存统计功能的 API 端点文档，用于监控和管理 Redis 缓存系统的运行状态

## 概述

本文档描述了缓存统计功能的 API 端点，用于监控和管理 Redis 缓存系统的运行状态。

## API 端点

### 1. 获取缓存统计信息

**端点**: `GET /api/admin/cache/stats`

**权限**: 仅限管理员

**描述**: 获取当前缓存系统的统计信息，包括命中率、降级次数、降级原因等。

**请求示例**:
```bash
curl -X GET "http://localhost:8000/api/admin/cache/stats" \
  -H "Authorization: Bearer <admin_token>"
```

**响应示例**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "hits": 150,
    "misses": 50,
    "errors": 2,
    "bypassed": 10,
    "degraded": 5,
    "degradation_reasons": {
      "cache_disabled": 3,
      "redis_connection_failed": 2
    },
    "total_cached_requests": 200,
    "hit_rate": "75.00%",
    "cache_enabled": true
  }
}
```

**响应字段说明**:
- `hits`: 缓存命中次数
- `misses`: 缓存未命中次数
- `errors`: 缓存错误次数
- `bypassed`: 绕过缓存的请求次数（如 POST 请求、排除路径等）
- `degraded`: 缓存降级次数
- `degradation_reasons`: 降级原因统计，键为降级原因，值为次数
  - `cache_disabled`: 缓存被配置禁用
  - `redis_connection_failed`: Redis 连接失败
- `total_cached_requests`: 总缓存请求次数（hits + misses）
- `hit_rate`: 缓存命中率（百分比）
- `cache_enabled`: 缓存是否启用

### 2. 重置缓存统计信息

**端点**: `POST /api/admin/cache/stats/reset`

**权限**: 仅限管理员

**描述**: 重置所有缓存统计计数器，将所有统计数据清零。

**请求示例**:
```bash
curl -X POST "http://localhost:8000/api/admin/cache/stats/reset" \
  -H "Authorization: Bearer <admin_token>"
```

**响应示例**:
```json
{
  "code": 200,
  "message": "缓存统计信息已重置",
  "data": null
}
```

## 使用场景

### 1. 监控缓存性能

定期调用 `GET /api/admin/cache/stats` 端点，监控缓存命中率和降级情况：

```python
import requests

def monitor_cache_performance():
    response = requests.get(
        "http://localhost:8000/api/admin/cache/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    stats = response.json()["data"]
    
    # 检查缓存命中率
    hit_rate = float(stats["hit_rate"].rstrip("%"))
    if hit_rate < 70:
        print(f"警告：缓存命中率过低 ({stats['hit_rate']})")
    
    # 检查降级情况
    if stats["degraded"] > 0:
        print(f"警告：发生 {stats['degraded']} 次缓存降级")
        print(f"降级原因：{stats['degradation_reasons']}")
```

### 2. 性能测试后重置统计

在进行性能测试前后，重置统计信息以获得准确的测试数据：

```python
import requests

def performance_test():
    # 重置统计信息
    requests.post(
        "http://localhost:8000/api/admin/cache/stats/reset",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # 执行性能测试
    run_performance_tests()
    
    # 获取测试结果
    response = requests.get(
        "http://localhost:8000/api/admin/cache/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    stats = response.json()["data"]
    print(f"测试结果：命中率 {stats['hit_rate']}")
```

### 3. 告警集成

将缓存统计 API 集成到监控告警系统：

```python
import requests
import time

def cache_monitoring_daemon():
    while True:
        response = requests.get(
            "http://localhost:8000/api/admin/cache/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        stats = response.json()["data"]
        
        # 检查降级频率
        if stats["degraded"] > 10:
            send_alert(
                "缓存频繁降级",
                f"降级次数：{stats['degraded']}\n"
                f"降级原因：{stats['degradation_reasons']}"
            )
        
        # 检查错误率
        total = stats["total_cached_requests"]
        if total > 0 and stats["errors"] / total > 0.05:
            send_alert(
                "缓存错误率过高",
                f"错误次数：{stats['errors']}/{total}"
            )
        
        time.sleep(60)  # 每分钟检查一次
```

## 降级原因说明

### cache_disabled
- **含义**: 缓存在配置中被禁用
- **触发条件**: `cache.enabled = false` 或缓存管理器初始化时 `enabled=False`
- **影响**: 所有请求直接访问数据库，不使用缓存
- **处理建议**: 这是预期行为，用于开发调试或故障恢复

### redis_connection_failed
- **含义**: Redis 服务器连接失败
- **触发条件**: Redis 服务不可用、网络故障、认证失败等
- **影响**: 自动降级到数据库访问，对用户透明
- **处理建议**: 
  1. 检查 Redis 服务状态
  2. 检查网络连接
  3. 验证 Redis 配置（主机、端口、密码）
  4. 查看应用日志获取详细错误信息

## 注意事项

1. **权限控制**: 这些端点仅限管理员访问，确保不要泄露管理员令牌
2. **性能影响**: 获取统计信息的操作非常轻量，可以频繁调用
3. **统计持久性**: 统计信息存储在内存中，应用重启后会重置
4. **并发安全**: 统计计数器是线程安全的，可以在高并发环境下使用
5. **降级透明性**: 缓存降级对用户完全透明，不影响业务逻辑

## 相关文档

- [缓存中间件使用指南](./缓存中间件使用指南.md)
- [缓存系统配置指南](./缓存系统配置指南.md)

---

**文档信息**

| 项目 | 内容 |
|------|------|
| 创建日期 | 2026-02-23 |
| 最后更新 | 2026-02-23 |
| 维护者 | CorrectPath, A-Dawn, cuckoo711 |
| 状态 | 📝 参考文档 |
