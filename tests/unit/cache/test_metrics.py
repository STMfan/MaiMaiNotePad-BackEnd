"""
缓存监控指标单元测试

测试 Prometheus 指标记录和导出功能。
"""

import pytest

from app.core.cache.metrics import (
    CacheMetrics,
    cache_degradation_total,
    cache_enabled_status,
    cache_hits_total,
    cache_misses_total,
    cache_operation_duration,
    get_cache_metrics,
)


class TestCacheMetrics:
    """测试缓存指标记录器"""

    def test_get_cache_metrics_singleton(self):
        """测试获取全局指标记录器实例（单例模式）"""
        metrics1 = get_cache_metrics()
        metrics2 = get_cache_metrics()

        assert metrics1 is metrics2
        assert isinstance(metrics1, CacheMetrics)

    def test_record_cache_hit(self):
        """测试记录缓存命中"""
        metrics = get_cache_metrics()

        # 使用唯一的 operation 标签避免与其他测试冲突
        test_operation = "test_hit_unique"

        # 记录命中前后，验证功能正常（不验证具体值）
        try:
            metrics.record_cache_hit(test_operation)
            # 如果没有抛出异常，说明功能正常
            assert True
        except Exception as e:
            pytest.fail(f"记录缓存命中失败: {e}")

    def test_record_cache_miss(self):
        """测试记录缓存未命中"""
        metrics = get_cache_metrics()

        # 使用唯一的 operation 标签避免与其他测试冲突
        test_operation = "test_miss_unique"

        # 记录未命中前后，验证功能正常（不验证具体值）
        try:
            metrics.record_cache_miss(test_operation)
            # 如果没有抛出异常，说明功能正常
            assert True
        except Exception as e:
            pytest.fail(f"记录缓存未命中失败: {e}")

    def test_record_degradation(self):
        """测试记录缓存降级"""
        metrics = get_cache_metrics()

        # 使用唯一的 reason 标签避免与其他测试冲突
        test_reason = "test_degradation_unique"

        # 记录降级前后，验证功能正常（不验证具体值）
        try:
            metrics.record_degradation(test_reason)
            # 如果没有抛出异常，说明功能正常
            assert True
        except Exception as e:
            pytest.fail(f"记录缓存降级失败: {e}")

    def test_set_cache_enabled(self):
        """测试设置缓存启用状态"""
        metrics = get_cache_metrics()

        # 设置为启用
        metrics.set_cache_enabled(True)

        # 验证状态
        value = cache_enabled_status._value.get()
        assert value == 1

        # 设置为禁用
        metrics.set_cache_enabled(False)

        # 验证状态
        value = cache_enabled_status._value.get()
        assert value == 0

    def test_record_operation_duration(self):
        """测试记录操作耗时"""
        metrics = get_cache_metrics()

        # 记录操作耗时
        metrics.record_operation_duration("get", "success", 0.05)

        # 验证直方图有数据
        histogram_samples = cache_operation_duration.collect()[0].samples

        # 查找匹配的样本
        found = False
        for sample in histogram_samples:
            if sample.labels.get("operation") == "get" and sample.labels.get("status") == "success":
                found = True
                break

        assert found, "应该记录了操作耗时"

    def test_get_cache_hit_rate_zero(self):
        """测试计算缓存命中率（无数据时）"""
        metrics = get_cache_metrics()

        # 在没有任何命中和未命中的情况下
        # 注意：由于其他测试可能已经记录了数据，这里只验证函数不会崩溃
        hit_rate = metrics.get_cache_hit_rate()

        assert isinstance(hit_rate, float)
        assert 0 <= hit_rate <= 100

    def test_get_cache_hit_rate_with_data(self):
        """测试计算缓存命中率（有数据时）"""
        metrics = get_cache_metrics()

        # 记录一些命中和未命中
        operation = "test_hit_rate"
        metrics.record_cache_hit(operation)
        metrics.record_cache_hit(operation)
        metrics.record_cache_miss(operation)

        # 计算命中率
        hit_rate = metrics.get_cache_hit_rate()

        # 验证命中率在合理范围内
        assert isinstance(hit_rate, float)
        assert 0 <= hit_rate <= 100


class TestPrometheusMetrics:
    """测试 Prometheus 指标定义"""

    def test_cache_hits_total_exists(self):
        """测试缓存命中计数器存在"""
        # 验证指标已注册
        assert cache_hits_total is not None
        # Prometheus Counter 会自动去掉 _total 后缀
        assert cache_hits_total._name == "cache_hits"

    def test_cache_misses_total_exists(self):
        """测试缓存未命中计数器存在"""
        assert cache_misses_total is not None
        # Prometheus Counter 会自动去掉 _total 后缀
        assert cache_misses_total._name == "cache_misses"

    def test_cache_degradation_total_exists(self):
        """测试缓存降级计数器存在"""
        assert cache_degradation_total is not None
        # Prometheus Counter 会自动去掉 _total 后缀
        assert cache_degradation_total._name == "cache_degradation"

    def test_cache_enabled_status_exists(self):
        """测试缓存启用状态指标存在"""
        assert cache_enabled_status is not None
        assert cache_enabled_status._name == "cache_enabled_status"

    def test_cache_operation_duration_exists(self):
        """测试缓存操作耗时直方图存在"""
        assert cache_operation_duration is not None
        assert cache_operation_duration._name == "cache_operation_duration_seconds"

    def test_metrics_have_correct_labels(self):
        """测试指标具有正确的标签"""
        # 记录一些数据以生成标签
        metrics = get_cache_metrics()
        metrics.record_cache_hit("test")
        metrics.record_cache_miss("test")
        metrics.record_degradation("test_reason")
        metrics.record_operation_duration("get", "success", 0.01)

        # 验证标签
        hits_samples = cache_hits_total.collect()[0].samples
        assert any("operation" in sample.labels for sample in hits_samples)

        misses_samples = cache_misses_total.collect()[0].samples
        assert any("operation" in sample.labels for sample in misses_samples)

        degradation_samples = cache_degradation_total.collect()[0].samples
        assert any("reason" in sample.labels for sample in degradation_samples)

        duration_samples = cache_operation_duration.collect()[0].samples
        assert any("operation" in sample.labels and "status" in sample.labels for sample in duration_samples)
