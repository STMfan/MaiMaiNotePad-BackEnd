"""
AI 内容审核功能演示

演示如何使用 ModerationService 进行内容审核。
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.moderation_service import ModerationService


def print_result(text: str, result: dict):
    """打印审核结果"""
    print(f"\n{'='*60}")
    print(f"待审核文本: {text}")
    print(f"{'='*60}")
    print(f"审核决策: {result['decision']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"违规类型: {result['violation_types']}")
    print(f"{'='*60}\n")


def main():
    """主函数"""
    print("AI 内容审核功能演示")
    print("=" * 60)

    # 检查环境变量
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("❌ 错误：未配置 SILICONFLOW_API_KEY")
        print("请在 .env 文件中设置正确的 API Key")
        return

    try:
        # 初始化审核服务
        print("正在初始化审核服务...")
        service = ModerationService()
        print("✅ 审核服务初始化成功")
        print(f"使用模型: {service.model}")
        print(f"API 地址: {service.base_url}\n")

        # 测试用例
        test_cases = [
            ("这是一条正常的评论，讨论技术问题。", "comment"),
            ("今天天气真好，适合出去玩。", "post"),
            ("Python 是一门很棒的编程语言。", "content"),
            ("你他妈就是个傻逼", "comment")
        ]

        print("开始测试审核功能...\n")

        for text, text_type in test_cases:
            try:
                result = service.moderate(text=text, text_type=text_type)
                print_result(text, result)
            except Exception as e:
                print(f"❌ 审核失败: {e}\n")

        print("✅ 演示完成！")

    except ValueError as e:
        print(f"❌ 配置错误: {e}")
    except Exception as e:
        print(f"❌ 发生异常: {e}")


if __name__ == "__main__":
    main()
