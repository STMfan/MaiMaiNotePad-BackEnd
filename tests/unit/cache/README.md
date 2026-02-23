# 缓存监控系统测试文档

## 概述

本目录包含 Redis 缓存机制的监控和日志系统的单元测试。测试覆盖了日志格式正确性、指标导出功能和降级事件记录。

## 测试文件结构

```
tests/
├── test_cache_logger.py              # 日志记录器单元测试
├── test_cache_manager_logging.py     # 缓存管理器日志集成测试
└── unit/cache/
    ├── test_metrics.py               # 监控指标单元测试
    └── README.md                     # 本文档
```

## 测试覆盖范围

### 1. 日志格式正确性测试 (`test_cache_logger.py`)

**测试目标**：验证结构化 JSON 日志格式的正确性

**测试用例**：
- ✅ 缓存命中日志记录
- ✅ 缓存未命中日志记录
- ✅ 缓存获取错误日志记录
- ✅ 缓存设置成功日志记录
- ✅ 缓存设置失败日志记录
- ✅ 单键失效日志记录
- ✅ 批量失效日志记录
- ✅ 缓存降级事件日志记录
- ✅ 缓存禁用事件日志记录
- ✅ 缓存启用事件日志记录
- ✅ 全局日志记录器单例模式
- ✅ JSON 格式有效性验证
- ✅ 时间戳格式验证（ISO 8601）

**覆盖的需求**：
- 需求 5.2：日志记录
- 需求 4.1：单元测试

### 2. 指标导出功能测试 (`test_metrics.py`)

**测试目标**：验证 Prometheus 指标记录和导出功能

**测试用例**：
- ✅ 全局指标记录器单例模式
- ✅ 缓存命中计数器记录
- ✅ 缓存未命中计数器记录
- ✅ 缓存降级计数器记录
- ✅ 缓存启用状态设置
- ✅ 缓存操作耗时记录
- ✅ 缓存命中率计算（无数据）
- ✅ 缓存命中率计算（有数据）
- ✅ Prometheus 指标定义验证
- ✅ 指标标签正确性验证

**覆盖的需求**：
- 需求 5.1：监控指标
- 需求 4.1：单元测试

### 3. 降级事件记录测试 (`test_cache_manager_logging.py`)

**测试目标**：验证缓存管理器与日志系统的集成

**测试用例**：
- ✅ 缓存命中时的日志记录
- ✅ 缓存未命中时的日志记录
- ✅ Redis 故障时的降级日志
- ✅ 缓存设置成功的日志记录
- ✅ 缓存设置失败的日志记录
- ✅ 缓存失效成功的日志记录
- ✅ 批量失效成功的日志记录
- ✅ 缓存禁用时的降级日志
- ✅ 缓存禁用时设置操作的日志
- ✅ 缓存禁用时失效操作的日志
- ✅ 初始化时记录缓存禁用日志

**覆盖的需求**：
- 需求 2.2：降级策略
- 需求 5.2：日志记录
- 需求 4.1：单元测试

## 运行测试

### 运行所有监控系统测试

```bash
conda activate mai_notebook
pytest tests/test_cache_logger.py tests/test_cache_manager_logging.py tests/unit/cache/test_metrics.py -v
```

### 运行单个测试文件

```bash
# 日志记录器测试
pytest tests/test_cache_logger.py -v

# 日志集成测试
pytest tests/test_cache_manager_logging.py -v

# 监控指标测试
pytest tests/unit/cache/test_metrics.py -v
```

### 运行特定测试用例

```bash
# 运行日志格式测试
pytest tests/test_cache_logger.py::TestCacheLogger::test_json_format_valid -v

# 运行降级日志测试
pytest tests/test_cache_manager_logging.py::TestCacheManagerLogging::test_get_cached_logs_degradation -v

# 运行指标记录测试
pytest tests/unit/cache/test_metrics.py::TestCacheMetrics::test_record_cache_hit -v
```

### 生成覆盖率报告

```bash
pytest tests/test_cache_logger.py tests/test_cache_manager_logging.py tests/unit/cache/test_metrics.py --cov=app.core.cache --cov-report=html
```

## 测试结果

### 最新测试运行结果

```
============================== 38 passed in 0.66s ==============================

测试覆盖率：
- app/core/cache/logger.py:  97% 覆盖率
- app/core/cache/metrics.py: 90% 覆盖率
- app/core/cache/manager.py: 73% 覆盖率（日志相关部分）
```

### 验证的功能

1. **日志格式正确性** ✅
   - JSON 格式有效性
   - 必需字段完整性
   - 时间戳格式正确性
   - 日志级别正确性

2. **指标导出功能** ✅
   - Prometheus 指标定义
   - 指标标签正确性
   - 指标值记录准确性
   - 缓存命中率计算

3. **降级事件记录** ✅
   - 缓存禁用时的降级日志
   - Redis 故障时的降级日志
   - 降级原因记录
   - 降级过程透明性

## 日志格式示例

### 缓存操作日志

```json
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": "INFO",
    "operation": "cache_get",
    "key": "user:123",
    "hit": true,
    "latency_ms": 5.2,
    "degraded": false,
    "source": "CacheManager"
}
```

### 缓存降级日志

```json
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": "WARNING",
    "operation": "cache_degradation",
    "reason": "redis_connection_failed",
    "original_operation": "get_cached",
    "key": "user:123",
    "error": "Connection timeout",
    "fallback": "database_query",
    "source": "CacheManager"
}
```

### 缓存禁用日志

```json
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": "INFO",
    "operation": "cache_disabled",
    "reason": "config_enabled_false",
    "source": "CacheManager"
}
```

## 监控指标

### Prometheus 指标列表

1. **cache_hits_total**
   - 类型：Counter
   - 标签：operation
   - 说明：缓存命中总次数

2. **cache_misses_total**
   - 类型：Counter
   - 标签：operation
   - 说明：缓存未命中总次数

3. **cache_degradation_total**
   - 类型：Counter
   - 标签：reason
   - 说明：缓存降级总次数

4. **cache_enabled_status**
   - 类型：Gauge
   - 说明：缓存启用状态（1=启用，0=禁用）

5. **cache_operation_duration_seconds**
   - 类型：Histogram
   - 标签：operation, status
   - 说明：缓存操作耗时（秒）

## 测试最佳实践

1. **使用 Mock 对象**
   - 模拟 Redis 客户端避免真实连接
   - 模拟日志记录器验证日志调用

2. **验证日志内容**
   - 解析 JSON 日志验证字段
   - 检查日志级别和操作类型
   - 验证时间戳格式

3. **测试降级场景**
   - 模拟 Redis 连接失败
   - 验证降级日志记录
   - 确保降级过程透明

4. **指标验证**
   - 验证指标定义存在
   - 检查指标标签正确性
   - 测试指标值记录

## 相关文档

- [缓存日志记录模块](../../../app/core/cache/logger.py)
- [缓存监控指标模块](../../../app/core/cache/metrics.py)

## 维护说明

### 添加新的测试用例

1. 在相应的测试文件中添加测试方法
2. 使用描述性的测试名称
3. 添加中文 docstring 说明测试目的
4. 验证测试通过后更新本文档

### 更新测试覆盖率

定期运行覆盖率报告，确保监控系统的测试覆盖率保持在 90% 以上：

```bash
pytest tests/test_cache_logger.py tests/test_cache_manager_logging.py tests/unit/cache/test_metrics.py --cov=app.core.cache.logger --cov=app.core.cache.metrics --cov-report=term-missing
```

## 任务状态

- [x] 8.3 编写监控系统测试
  - [x] 测试日志格式正确性（13 个测试用例）
  - [x] 测试指标导出功能（14 个测试用例）
  - [x] 测试降级事件记录（11 个测试用例）
  - [x] 验证需求：4.1（单元测试）

**总计**：38 个测试用例全部通过 ✅
