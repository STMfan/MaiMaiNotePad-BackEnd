"""
环境感知错误消息解析工具

本模块提供根据环境（测试环境 vs 生产环境）返回适当错误消息的功能。
"""

import os

# 消息字典：将消息键映射到（英文，中文）翻译
MESSAGE_TRANSLATIONS: dict[str, tuple[str, str]] = {
    "invalid_credentials": ("Invalid authentication credentials", "无效的认证凭证"),
    "user_not_found": ("User not found", "用户不存在"),
    "insufficient_permissions": ("Not enough permissions", "权限不足"),
    "password_changed": ("Password changed, token invalid, please login again", "密码已修改，令牌已失效，请重新登录"),
    "authentication_failed": ("Authentication failed", "认证失败"),
    "access_denied": ("Access denied", "拒绝访问"),
    "resource_not_found": ("Resource not found", "资源不存在"),
    "resource_conflict": ("Resource conflict", "资源冲突"),
    "rate_limit_exceeded": ("Rate limit exceeded", "请求过于频繁"),
}


def get_message(key: str) -> str:
    """
    根据环境获取适当的错误消息。

    参数：
        key: MESSAGE_TRANSLATIONS 中的消息键

    返回：
        str: 测试环境返回英文消息，否则返回中文消息
    """
    if key not in MESSAGE_TRANSLATIONS:
        raise ValueError(f"未知的消息键: {key}")

    english_msg, chinese_msg = MESSAGE_TRANSLATIONS[key]

    # 检查是否在测试环境中
    test_language = os.environ.get("TEST_LANGUAGE", "").lower()

    if test_language == "en":
        return english_msg
    else:
        return chinese_msg
