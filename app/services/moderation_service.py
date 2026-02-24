"""
AI 内容审核服务模块

基于硅基流动 Qwen/Qwen3-8B 模型的内容安全审核服务。
支持色情、涉政、辱骂等违规内容的检测。
"""

import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class ModerationService:
    """AI 内容审核服务类"""

    # 系统提示词：指导模型如何进行内容审核
    SYSTEM_PROMPT = """你是一个专业的内容安全审核员，负责判断用户生成的文本是否包含违规信息。

审核范围：
1. 色情（porn）：仅限露骨的性行为描写、色情词汇，不包含软色情或性暗示
2. 涉政（politics）：仅限中国国内政治敏感内容，包括对领导人的负面评价、敏感历史事件、领土分裂言论等
3. 辱骂（abuse）：仅限粗口脏话，不包含隐晦的人身攻击或歧视性言论

判断逻辑：
- 明确违规（置信度 > 0.8）：文本明显包含上述任一违规类型
- 明确正常（置信度 < 0.4）：文本完全正常，无任何违规迹象
- 不确定（置信度 0.4 ~ 0.8）：文本疑似违规但无法确定，如隐晦表达、谐音、反讽或边缘内容

输出格式（必须是合法的 JSON，不含任何额外文字）：
{
  "decision": "true/false/unknown",
  "confidence": 0.0-1.0,
  "violation_types": ["porn", "politics", "abuse"]
}

字段说明：
- decision: "true"（通过）、"false"（拒绝）或 "unknown"（不确定）
- confidence: 0~1 的浮点数，表示内容违规的置信度，越接近 1 越确信违规
- violation_types: 违规类型数组，若 decision 为 "true" 则为空数组

示例：

输入：[包含露骨性描写的文本]
输出：{"decision": "false", "confidence": 0.95, "violation_types": ["porn"]}

输入：[包含对领导人侮辱性称呼的文本]
输出：{"decision": "false", "confidence": 0.92, "violation_types": ["politics"]}

输入：[包含粗口的句子]
输出：{"decision": "false", "confidence": 0.88, "violation_types": ["abuse"]}

输入：[正常的日常对话]
输出：{"decision": "true", "confidence": 0.15, "violation_types": []}

输入：[使用谐音或隐晦表达的疑似违规内容]
输出：{"decision": "unknown", "confidence": 0.65, "violation_types": ["politics"]}

输入：[同时包含多种违规类型的文本]
输出：{"decision": "false", "confidence": 0.93, "violation_types": ["porn", "abuse"]}

请严格按照上述格式输出，不要添加任何解释或额外文字。"""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.siliconflow.cn/v1"):
        """
        初始化审核服务

        Args:
            api_key: 硅基流动 API Key，若为 None 则从环境变量 SILICONFLOW_API_KEY 读取
            base_url: API 基础地址
        """
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 SILICONFLOW_API_KEY，请在环境变量中设置或通过参数传入")

        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.model = "Qwen/Qwen2.5-7B-Instruct"  # 硅基流动免费模型

        logger.info(f"ModerationService 初始化成功，使用模型: {self.model}")

    def moderate(
        self, text: str, text_type: str = "comment", temperature: float = 0.1, max_tokens: int = 100
    ) -> dict[str, Any]:
        """
        对文本进行内容审核

        Args:
            text: 待审核的文本内容
            text_type: 文本类型（comment/post/title/content），帮助模型更好理解上下文
            temperature: 模型温度参数，越低输出越稳定
            max_tokens: 最大输出 token 数

        Returns:
            审核结果字典，包含以下字段：
            - decision: str, "true"（通过）/"false"（拒绝）/"unknown"（不确定）
            - confidence: float, 0~1，违规置信度
            - violation_types: List[str], 违规类型列表
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回默认通过结果")
            return {"decision": "true", "confidence": 0.0, "violation_types": []}

        # 构建用户消息，包含文本类型信息
        user_message = f"文本类型：{text_type}\n待审核内容：{text}"

        try:
            # 调用模型进行审核
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.SYSTEM_PROMPT}, {"role": "user", "content": user_message}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            # 提取模型输出
            output = response.choices[0].message.content.strip()
            logger.debug(f"模型原始输出: {output}")

            # 解析 JSON 结果
            result = json.loads(output)

            # 验证结果格式
            if not self._validate_result(result):
                logger.error(f"模型输出格式不符合要求: {result}")
                return self._get_default_unknown_result()

            logger.info(
                f"审核完成 - 决策: {result['decision']}, 置信度: {result['confidence']}, 违规类型: {result['violation_types']}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 原始输出: {output if 'output' in locals() else 'N/A'}")
            return self._get_default_unknown_result()

        except Exception as e:
            logger.error(f"审核过程发生异常: {e}", exc_info=True)
            return self._get_default_unknown_result()

    def _validate_result(self, result: dict) -> bool:
        """
        验证审核结果格式是否正确

        Args:
            result: 待验证的结果字典

        Returns:
            bool: 格式是否正确
        """
        if not isinstance(result, dict):
            return False

        # 检查必需字段
        if "decision" not in result or "confidence" not in result or "violation_types" not in result:
            return False

        # 检查字段类型和取值
        if result["decision"] not in ["true", "false", "unknown"]:
            return False

        if not isinstance(result["confidence"], (int, float)) or not (0 <= result["confidence"] <= 1):
            return False

        if not isinstance(result["violation_types"], list):
            return False

        # 检查违规类型是否合法
        valid_types = {"porn", "politics", "abuse"}
        if not all(vtype in valid_types for vtype in result["violation_types"]):
            return False

        return True

    def _get_default_unknown_result(self) -> dict[str, Any]:
        """
        获取默认的"不确定"结果（用于异常情况）

        Returns:
            默认结果字典
        """
        return {"decision": "unknown", "confidence": 0.5, "violation_types": []}


# 全局服务实例（延迟初始化）
_moderation_service: ModerationService | None = None


def get_moderation_service() -> ModerationService:
    """
    获取全局审核服务实例（单例模式）

    Returns:
        ModerationService 实例
    """
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service
