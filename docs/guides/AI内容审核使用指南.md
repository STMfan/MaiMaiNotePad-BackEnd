# AI 内容审核使用指南

## 概述

本项目集成了基于硅基流动 Qwen/Qwen2.5-7B-Instruct 模型的 AI 内容审核功能，用于自动检测用户生成内容中的违规信息。

## 审核范围

审核系统会检测以下三类违规内容：

1. **色情（porn）**：露骨的性行为描写、色情词汇（不包含软色情或性暗示）
2. **涉政（politics）**：中国国内政治敏感内容，包括对领导人的负面评价、敏感历史事件、领土分裂言论等
3. **辱骂（abuse）**：粗口脏话（不包含隐晦的人身攻击或歧视性言论）

## 配置步骤

### 1. 获取 API Key

访问 [硅基流动官网](https://cloud.siliconflow.cn/) 注册账号并获取 API Key。

### 2. 配置环境变量

在项目根目录的 `.env` 文件中添加：

```bash
# AI 内容审核配置（硅基流动）
SILICONFLOW_API_KEY=your_api_key_here
```

将 `your_api_key_here` 替换为您的实际 API Key。

### 3. 安装依赖

确保已安装 OpenAI Python 库：

```bash
conda activate mai_notebook
pip install openai
```

## API 使用

### 端点信息

- **基础路径**：`/api/moderation`
- **认证方式**：无需认证（可根据需要添加）

### 1. 内容审核接口

**请求**

```http
POST /api/moderation/check
Content-Type: application/json

{
  "text": "待审核的文本内容",
  "text_type": "comment"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 待审核的文本内容 |
| text_type | string | 否 | 文本类型，可选值：`comment`（评论）、`post`（帖子）、`title`（标题）、`content`（正文），默认为 `comment` |

**响应示例**

```json
{
  "success": true,
  "result": {
    "decision": "false",
    "confidence": 0.92,
    "violation_types": ["abuse"]
  },
  "message": "审核完成"
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 请求是否成功 |
| result.decision | string | 审核决策：`"true"`（通过）、`"false"`（拒绝）、`"unknown"`（不确定） |
| result.confidence | float | 违规置信度，0~1 之间，越接近 1 越确信违规 |
| result.violation_types | array | 违规类型列表，可包含 `"porn"`、`"politics"`、`"abuse"` |
| message | string | 附加消息 |

### 2. 健康检查接口

**请求**

```http
GET /api/moderation/health
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "base_url": "https://api.siliconflow.cn/v1"
  }
}
```

## 判断逻辑

审核系统根据置信度返回不同的决策：

| 置信度范围 | 决策 | 说明 |
|-----------|------|------|
| > 0.8 | `false` | 明确违规，拒绝内容 |
| 0.4 ~ 0.8 | `unknown` | 不确定，建议人工复审 |
| < 0.4 | `true` | 明确正常，通过内容 |

## 代码集成示例

### Python 示例

```python
import requests

# 审核文本
def moderate_content(text: str, text_type: str = "comment"):
    url = "http://localhost:8000/api/moderation/check"
    payload = {
        "text": text,
        "text_type": text_type
    }
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    if result["success"]:
        decision = result["result"]["decision"]
        confidence = result["result"]["confidence"]
        violations = result["result"]["violation_types"]
        
        if decision == "false":
            print(f"内容违规！置信度: {confidence}, 违规类型: {violations}")
            return False
        elif decision == "unknown":
            print(f"内容疑似违规，建议人工复审。置信度: {confidence}")
            return None
        else:
            print(f"内容正常。置信度: {confidence}")
            return True
    else:
        print("审核失败")
        return None

# 使用示例
moderate_content("这是一条正常的评论")
```

### JavaScript 示例

```javascript
async function moderateContent(text, textType = 'comment') {
  const response = await fetch('http://localhost:8000/api/moderation/check', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: text,
      text_type: textType
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    const { decision, confidence, violation_types } = result.result;
    
    if (decision === 'false') {
      console.log(`内容违规！置信度: ${confidence}, 违规类型: ${violation_types}`);
      return false;
    } else if (decision === 'unknown') {
      console.log(`内容疑似违规，建议人工复审。置信度: ${confidence}`);
      return null;
    } else {
      console.log(`内容正常。置信度: ${confidence}`);
      return true;
    }
  } else {
    console.log('审核失败');
    return null;
  }
}

// 使用示例
moderateContent('这是一条正常的评论');
```

## 最佳实践

### 1. 异步处理

对于大量内容的审核，建议使用异步任务队列（如 Celery）进行处理，避免阻塞主线程。

### 2. 缓存机制

对于相同的文本内容，可以缓存审核结果，减少 API 调用次数和成本。

### 3. 人工复审

对于 `decision` 为 `unknown` 的内容，建议加入人工复审队列，由管理员进行最终判断。

### 4. 错误处理

审核服务可能因网络问题或 API 限制而失败，建议实现重试机制和降级策略：

```python
from app.services.moderation_service import get_moderation_service

def safe_moderate(text: str, max_retries: int = 3):
    """带重试机制的安全审核"""
    service = get_moderation_service()
    
    for attempt in range(max_retries):
        try:
            result = service.moderate(text)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                # 最后一次重试失败，返回默认结果
                return {
                    "decision": "unknown",
                    "confidence": 0.5,
                    "violation_types": []
                }
            continue
```

### 5. 批量审核

如需批量审核多条内容，可以使用异步并发：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def batch_moderate(texts: list):
    """批量审核文本"""
    service = get_moderation_service()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, service.moderate, text)
            for text in texts
        ]
        results = await asyncio.gather(*tasks)
    
    return results
```

## 性能优化

### 1. 调整模型参数

可以通过调整 `temperature` 和 `max_tokens` 参数来优化性能：

```python
# 更稳定的输出（推荐）
result = service.moderate(text, temperature=0.1, max_tokens=100)

# 更快的响应
result = service.moderate(text, temperature=0.0, max_tokens=50)
```

### 2. 连接池复用

`ModerationService` 使用单例模式，自动复用 OpenAI 客户端连接，无需额外配置。

## 故障排查

### 问题 1：API Key 未配置

**错误信息**：`未找到 SILICONFLOW_API_KEY`

**解决方案**：检查 `.env` 文件中是否正确配置了 `SILICONFLOW_API_KEY`。

### 问题 2：模型输出格式错误

**错误信息**：`JSON 解析失败`

**解决方案**：这通常是模型输出不稳定导致的，系统会自动返回 `unknown` 结果。如果频繁出现，可以尝试：
- 降低 `temperature` 参数（如设为 0.0）
- 检查输入文本是否过长或包含特殊字符

### 问题 3：API 调用超时

**错误信息**：`审核过程发生异常: timeout`

**解决方案**：
- 检查网络连接
- 增加超时时间（在 OpenAI 客户端配置中）
- 实现重试机制

## 成本估算

硅基流动的计费方式为按 token 计费，具体价格请参考官方文档。

**估算示例**（假设价格为 ¥0.001/1K tokens）：

- 单次审核（100 字文本）：约 150 tokens，成本约 ¥0.00015
- 每日 10,000 次审核：成本约 ¥1.5

建议定期监控 API 使用量，避免超出预算。

## 相关文档

- [硅基流动官方文档](https://docs.siliconflow.cn/)
- [OpenAI Python 库文档](https://github.com/openai/openai-python)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

## 更新日志

- **2026-02-24**：初始版本，支持色情、涉政、辱骂三类内容的审核
