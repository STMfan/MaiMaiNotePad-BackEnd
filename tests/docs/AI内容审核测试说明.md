# AI 内容审核测试说明

## 测试概述

本文档说明 AI 内容审核模块的测试策略、测试用例和运行方法。

## 测试文件

### 单元测试

**文件**: `tests/unit/services/test_moderation_service.py`

测试 `ModerationService` 类的核心功能，包括：

- 服务初始化
- 审核方法
- 错误处理
- 结果验证
- 边界情况

**测试类**:

1. `TestModerationServiceInitialization` - 服务初始化测试
   - 使用 API Key 初始化
   - 从环境变量读取配置
   - 未配置 API Key 时的错误处理
   - 自定义 API 地址

2. `TestModerateMethod` - 审核方法测试
   - 正常文本审核
   - 违规文本审核
   - 不确定文本审核
   - 多种违规类型
   - 空文本处理
   - 文本类型指定
   - 自定义参数

3. `TestErrorHandling` - 错误处理测试
   - JSON 解析失败
   - 返回格式不正确
   - API 调用异常
   - 缺少必需字段

4. `TestResultValidation` - 结果验证测试
   - 有效结果验证
   - 无效决策值
   - 无效置信度
   - 无效违规类型
   - 非字典类型
   - 缺少字段

5. `TestGetModerationService` - 全局实例测试
   - 单例模式
   - 实例创建

6. `TestEdgeCases` - 边界情况测试
   - 超长文本
   - 特殊字符
   - Unicode 和 Emoji

### 集成测试

**文件**: `tests/integration/routes/test_moderation_routes.py`

测试审核 API 路由的完整流程，包括：

- API 端点功能
- 请求参数验证
- 错误处理
- 健康检查
- 缓存行为

**测试类**:

1. `TestModerationCheckEndpoint` - 审核接口测试
   - 正常文本审核
   - 违规文本审核
   - 不确定文本审核
   - 不同文本类型
   - 默认文本类型

2. `TestModerationCheckValidation` - 参数验证测试
   - 缺少 text 参数
   - 空文本
   - 无效文本类型
   - 无效 JSON

3. `TestModerationCheckErrors` - 错误处理测试
   - API Key 未配置
   - 服务异常

4. `TestModerationHealthEndpoint` - 健康检查测试
   - 健康检查成功
   - 服务未配置

5. `TestModerationCaching` - 缓存行为测试
   - Cache-Control: no-cache 头

6. `TestModerationEdgeCases` - 边界情况测试
   - 超长文本
   - 特殊字符
   - Unicode 和 Emoji

## 测试覆盖率

### 单元测试覆盖

- ✅ 服务初始化（4 个测试）
- ✅ 审核方法（8 个测试）
- ✅ 错误处理（4 个测试）
- ✅ 结果验证（6 个测试）
- ✅ 全局实例（2 个测试）
- ✅ 边界情况（3 个测试）

**总计**: 27 个单元测试

### 集成测试覆盖

- ✅ 审核接口（5 个测试）
- ✅ 参数验证（4 个测试）
- ✅ 错误处理（2 个测试）
- ✅ 健康检查（2 个测试）
- ✅ 缓存行为（1 个测试）
- ✅ 边界情况（3 个测试）

**总计**: 17 个集成测试

### 总覆盖率

**总计**: 44 个测试用例

## 运行测试

### 运行所有审核相关测试

```bash
# 激活环境
conda activate mai_notebook

# 运行单元测试
pytest tests/unit/services/test_moderation_service.py -v

# 运行集成测试
pytest tests/integration/routes/test_moderation_routes.py -v

# 运行所有审核测试
pytest tests/unit/services/test_moderation_service.py tests/integration/routes/test_moderation_routes.py -v
```

### 运行特定测试类

```bash
# 运行服务初始化测试
pytest tests/unit/services/test_moderation_service.py::TestModerationServiceInitialization -v

# 运行审核接口测试
pytest tests/integration/routes/test_moderation_routes.py::TestModerationCheckEndpoint -v
```

### 运行特定测试用例

```bash
# 运行单个测试
pytest tests/unit/services/test_moderation_service.py::TestModerateMethod::test_moderate_normal_text -v
```

### 并行运行测试

```bash
# 使用 pytest-xdist 并行运行
pytest tests/unit/services/test_moderation_service.py tests/integration/routes/test_moderation_routes.py -n auto -v
```

### 查看测试覆盖率

```bash
# 生成覆盖率报告
pytest tests/unit/services/test_moderation_service.py tests/integration/routes/test_moderation_routes.py --cov=app.services.moderation_service --cov=app.api.routes.moderation --cov-report=html

# 查看报告
open htmlcov/index.html
```

## 测试策略

### Mock 策略

所有测试都使用 Mock 来模拟 OpenAI API 调用，避免：

1. 实际的 API 调用成本
2. 网络依赖
3. 测试速度慢
4. 不稳定的测试结果

### 环境隔离

- 使用 `monkeypatch` 设置环境变量
- 每个测试重置全局服务实例
- 使用 `Cache-Control: no-cache` 避免缓存干扰

### 测试数据

测试使用各种场景的数据：

- 正常文本
- 违规文本（色情、涉政、辱骂）
- 不确定文本
- 空文本
- 超长文本
- 特殊字符
- Unicode 和 Emoji

## 测试场景

### 正常流程

1. **正常文本审核**
   - 输入：正常评论
   - 预期：decision="true", confidence<0.4

2. **违规文本审核**
   - 输入：违规内容
   - 预期：decision="false", confidence>0.8, violation_types 非空

3. **不确定文本审核**
   - 输入：疑似违规内容
   - 预期：decision="unknown", confidence 0.4-0.8

### 异常流程

1. **API Key 未配置**
   - 预期：抛出 ValueError 或返回 500 错误

2. **JSON 解析失败**
   - 预期：返回默认 unknown 结果

3. **API 调用异常**
   - 预期：返回默认 unknown 结果

4. **返回格式不正确**
   - 预期：返回默认 unknown 结果

### 边界情况

1. **空文本**
   - 预期：返回默认通过结果

2. **超长文本**
   - 预期：正常处理

3. **特殊字符**
   - 预期：正常处理

4. **Unicode 和 Emoji**
   - 预期：正常处理

## 测试最佳实践

### 1. 使用 Fixtures

```python
@pytest.fixture
def service():
    """创建测试用的服务实例"""
    return ModerationService(api_key="test-api-key")
```

### 2. Mock OpenAI 响应

```python
mock_response = Mock()
mock_choice = Mock()
mock_message = Mock()
mock_message.content = json.dumps({
    "decision": "true",
    "confidence": 0.15,
    "violation_types": []
})
mock_choice.message = mock_message
mock_response.choices = [mock_choice]
```

### 3. 重置全局实例

```python
import app.services.moderation_service as mod_service
mod_service._moderation_service = None
```

### 4. 避免缓存干扰

```python
response = client.post(
    "/api/moderation/check",
    json={"text": "测试"},
    headers={"Cache-Control": "no-cache"}
)
```

## 故障排查

### 测试失败：API Key 未配置

**问题**: 测试报错 "未找到 SILICONFLOW_API_KEY"

**解决方案**:
```python
# 在测试中使用 monkeypatch 设置环境变量
def test_example(monkeypatch):
    monkeypatch.setenv("SILICONFLOW_API_KEY", "test-key")
    # 测试代码
```

### 测试失败：缓存干扰

**问题**: 测试结果不一致，可能是缓存导致

**解决方案**:
```python
# 添加 Cache-Control 头
response = client.post(
    "/api/moderation/check",
    json={"text": "测试"},
    headers={"Cache-Control": "no-cache"}
)
```

### 测试失败：单例实例未重置

**问题**: 测试之间相互影响

**解决方案**:
```python
# 在每个测试中重置全局实例
import app.services.moderation_service as mod_service
mod_service._moderation_service = None
```

## 持续集成

### GitHub Actions 配置示例

```yaml
name: Test Moderation Module

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          pytest tests/unit/services/test_moderation_service.py tests/integration/routes/test_moderation_routes.py -v --cov
```

## 未来改进

### 短期（1-2 周）

- [ ] 添加性能测试（响应时间）
- [ ] 添加并发测试
- [ ] 添加更多边界情况测试

### 中期（1-2 月）

- [ ] 添加属性测试（Property-based testing）
- [ ] 添加压力测试
- [ ] 添加端到端测试

### 长期（3-6 月）

- [ ] 添加真实 API 集成测试（可选）
- [ ] 添加模型准确率测试
- [ ] 添加 A/B 测试框架

## 相关文档

- [AI内容审核使用指南](../../docs/guides/AI内容审核使用指南.md)
- [AI内容审核快速开始](../../docs/guides/AI内容审核快速开始.md)
- [测试说明](./测试说明.md)

---

**文档信息**

| 项目 | 内容 |
|------|------|
| 创建日期 | 2026-02-24 |
| 最后更新 | 2026-02-24 |
| 维护者 | 项目团队 |
| 状态 | ✅ 活跃 |
