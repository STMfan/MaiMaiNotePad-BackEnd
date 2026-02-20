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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "translation_dict.json")


def _load_translation_dict() -> Dict[str, Any]:
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
    data = _load_translation_dict()
    return Success(data=data)

