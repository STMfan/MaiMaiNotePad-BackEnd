# 元测试套件

## 概述

这个目录包含**元测试（Meta Tests）**，用于测试测试框架本身，而不是测试业务逻辑。

## 什么是元测试？

元测试是用来验证测试基础设施正确性的测试。它们检查：

- ✅ 并行测试的隔离性
- ✅ 缓存管理的正确性
- ✅ 事务处理的健壮性
- ✅ 依赖注入的隔离性
- ✅ 文件清理的可靠性

## 为什么单独存放？

元测试有以下特点：

1. **执行时间长**：通常需要启动多个子进程运行并行测试
2. **不测试业务逻辑**：只测试测试框架本身
3. **可能干扰常规测试**：在并行测试中运行元测试会导致嵌套并行

因此，我们将它们移到单独的目录，默认不运行。

## 如何运行元测试？

### 运行所有元测试
```bash
pytest tests/meta/ -v
```

### 运行特定的元测试
```bash
# 测试缓存隔离
pytest tests/meta/test_parallel_isolation.py::TestCacheIsolation -v

# 测试并行隔离
pytest tests/meta/test_parallel_isolation.py::TestParallelIsolation -v
```

### 使用管理脚本
```bash
# 在 manage.sh 菜单中选择相应选项
./manage.sh
# 然后输入: pytest tests/meta/ -v
```

## 何时运行元测试？

建议在以下情况下运行元测试：

- 🔧 修改了测试框架配置（pytest.ini, conftest.py）
- 🔧 升级了测试相关依赖（pytest, pytest-xdist, hypothesis）
- 🐛 遇到并行测试的奇怪问题（缓存污染、事务冲突等）
- 🚀 在 CI/CD 中定期运行（例如每周一次）

## 测试文件说明

### test_parallel_isolation.py

测试并行测试的隔离性，包括：

- **TestParallelIsolation**: 测试整体并行执行隔离
- **TestCacheIsolation**: 测试缓存隔离（使用 Hypothesis 属性测试）
- **TestTransactionManagement**: 测试事务管理
- **TestForeignKeyHandling**: 测试外键约束处理
- **TestDependencyOverrideIsolation**: 测试依赖注入隔离

## 注意事项

⚠️ **这些测试可能会失败**

元测试的目的是发现测试框架的问题。如果它们失败，说明：

1. 测试框架配置有问题
2. 并行测试存在隔离问题
3. 需要修复测试基础设施

⚠️ **不要在并行模式下运行元测试**

元测试本身会启动并行测试，如果在并行模式下运行会导致嵌套并行：

```bash
# ❌ 错误：嵌套并行
pytest tests/meta/ -n auto

# ✅ 正确：串行运行
pytest tests/meta/ -v
```

## 排除元测试

如果你想在常规测试中排除元测试目录：

### 方法 1：使用 pytest 配置
在 `pyproject.toml` 中：
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
# 排除 meta 目录
norecursedirs = ["tests/meta"]
```

### 方法 2：使用命令行
```bash
# 运行所有测试，但排除 meta 目录
pytest tests/ --ignore=tests/meta/
```

### 方法 3：使用 manage.sh
管理脚本已经配置为默认不运行 meta 测试。

## 相关文档

- [测试配置指南](../../docs/testing/测试配置指南.md)
- [测试环境设置](../../docs/testing/测试环境设置.md)
- [并行测试文档](https://pytest-xdist.readthedocs.io/)
