# AI 内容审核快速开始

## 5 分钟快速集成

本指南帮助您在 5 分钟内完成 AI 内容审核功能的配置和测试。

## 步骤 1：获取 API Key（2 分钟）

1. 访问 [硅基流动官网](https://cloud.siliconflow.cn/)
2. 注册账号并登录
3. 进入控制台，创建 API Key
4. 复制 API Key（格式类似：`sk-xxxxxxxxxxxxxx`）

## 步骤 2：配置环境变量（1 分钟）

编辑项目根目录的 `.env` 文件，添加或修改以下配置：

```bash
# AI 内容审核配置（硅基流动）
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxx  # 替换为您的实际 API Key
```

## 步骤 3：安装依赖（1 分钟）

```bash
# 激活 Conda 环境
conda activate mai_notebook

# 安装 OpenAI 库
pip install openai==1.59.5
```

## 步骤 4：启动服务并测试（1 分钟）

### 启动后端服务

```bash
# 在项目根目录执行
conda activate mai_notebook
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 测试审核接口

打开新的终端窗口，执行以下命令：

```bash
# 测试正常文本
curl -X POST "http://localhost:8000/api/moderation/check" \
  -H "Content-Type: application/json" \
  -d '{"text": "这是一条正常的评论", "text_type": "comment"}'

# 预期响应
# {
#   "success": true,
#   "result": {
#     "decision": "true",
#     "confidence": 0.15,
#     "violation_types": []
#   },
#   "message": "审核完成"
# }
```

### 运行演示脚本

```bash
conda activate mai_notebook
python examples/moderation_demo.py
```

## 步骤 5：集成到您的代码（可选）

### Python 集成示例

```python
from app.services.moderation_service import get_moderation_service

# 获取审核服务实例
service = get_moderation_service()

# 审核文本
result = service.moderate(
    text="用户输入的内容",
    text_type="comment"  # comment/post/title/content
)

# 处理结果
if result["decision"] == "false":
    print(f"内容违规：{result['violation_types']}")
elif result["decision"] == "unknown":
    print("内容疑似违规，建议人工复审")
else:
    print("内容正常")
```

### FastAPI 路由集成示例

```python
from fastapi import APIRouter, Depends
from app.services.moderation_service import get_moderation_service, ModerationService

router = APIRouter()

@router.post("/comments")
async def create_comment(
    content: str,
    service: ModerationService = Depends(get_moderation_service)
):
    # 审核评论内容
    result = service.moderate(text=content, text_type="comment")
    
    if result["decision"] == "false":
        return {"error": "内容包含违规信息，无法发布"}
    
    # 继续处理评论创建逻辑
    # ...
    return {"success": True}
```

## 常见问题

### Q1: API Key 配置后仍然报错？

确保 `.env` 文件中的配置格式正确，没有多余的空格或引号：

```bash
# ✅ 正确
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxx

# ❌ 错误（有引号）
SILICONFLOW_API_KEY="sk-xxxxxxxxxxxxxx"

# ❌ 错误（有空格）
SILICONFLOW_API_KEY = sk-xxxxxxxxxxxxxx
```

### Q2: 如何查看审核日志？

审核服务会自动记录日志到 `logs/app.log`，您可以查看详细的审核过程：

```bash
tail -f logs/app.log | grep "ModerationService"
```

### Q3: 审核速度慢怎么办？

1. 检查网络连接是否正常
2. 降低 `temperature` 参数（默认 0.1，可设为 0.0）
3. 减少 `max_tokens` 参数（默认 100，可设为 50）

```python
result = service.moderate(
    text=content,
    temperature=0.0,  # 更快的响应
    max_tokens=50     # 减少输出长度
)
```

### Q4: 如何处理"不确定"的结果？

建议将 `decision` 为 `unknown` 的内容加入人工复审队列：

```python
if result["decision"] == "unknown":
    # 标记为待审核
    await mark_for_manual_review(content, result)
    # 可以选择暂时允许发布或暂时隐藏
```

## 下一步

- 查看 [AI内容审核使用指南](./AI内容审核使用指南.md) 了解更多功能
- 查看 [API文档](../api/API文档.md) 了解完整的 API 接口
- 实现批量审核和缓存机制以优化性能

## 技术支持

如遇到问题，请：

1. 查看 `logs/app.log` 日志文件
2. 检查 [故障排查指南](./AI内容审核使用指南.md#故障排查)
3. 提交 Issue 到项目仓库

---

**文档信息**

| 项目 | 内容 |
|------|------|
| 创建日期 | 2026-02-24 |
| 最后更新 | 2026-02-24 |
| 维护者 | 项目团队 |
| 状态 | ✅ 活跃 |
