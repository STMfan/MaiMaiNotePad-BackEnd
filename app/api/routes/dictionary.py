"""
翻译字典路由模块

处理翻译字典相关的API端点，包括：
- 获取翻译字典（用于前端国际化）
"""

from fastapi import APIRouter
from typing import Dict, Any
import json
import os

from app.api.response_util import Success
from app.core.logging import app_logger


router = APIRouter()


# 翻译字典相关路由


def _get_dict_file_path() -> str:
    """获取翻译字典文件路径
    
    支持通过环境变量 TRANSLATION_DICT_PATH 覆盖默认路径（用于测试）
    
    Returns:
        str: 翻译字典文件的完整路径
    """
    if "TRANSLATION_DICT_PATH" in os.environ:
        return os.environ["TRANSLATION_DICT_PATH"]
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "translation_dict.json")


def _load_translation_dict() -> Dict[str, Any]:
    """加载翻译字典
    
    从文件中加载翻译字典数据，如果文件不存在或加载失败，返回空字典。
    
    Returns:
        Dict[str, Any]: 包含 blocks 和 tokens 的字典
    """
    path = _get_dict_file_path()
    if not os.path.exists(path):
        app_logger.warning(f"translation_dict.json not found at {path}")
        return {"blocks": {}, "tokens": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        app_logger.error(f"failed to load translation_dict.json: {e}")
        return {"blocks": {}, "tokens": {}}

    blocks = data.get("blocks") or {}
    tokens = data.get("tokens") or {}

    if not isinstance(blocks, dict):
        blocks = {}
    if not isinstance(tokens, dict):
        tokens = {}

    return {
        "blocks": blocks,
        "tokens": tokens,
    }


@router.get("/translation")
async def get_translation_dictionary():
    """获取翻译字典
    
    返回前端国际化所需的翻译字典，包含 blocks 和 tokens 两部分。
    
    Returns:
        Success: 包含翻译字典数据的成功响应
    """
    data = _load_translation_dict()
    return Success(data=data)
