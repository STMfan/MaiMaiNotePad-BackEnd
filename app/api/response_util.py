"""响应工具模块 - 提供统一的API响应格式化函数"""

from typing import TypeVar

from app.models.schemas import BaseResponse, PageResponse, Pagination

T = TypeVar("T")


def success(message: str | None = None, data: T | None = None) -> BaseResponse[T | None]:
    """创建成功响应

    Args:
        message: 响应消息
        data: 响应数据

    Returns:
        BaseResponse: 成功响应对象
    """
    return BaseResponse[T | None](success=True, message=message or "", data=data)


def error(message: str | None = None, data: T | None = None) -> BaseResponse[T | None]:
    """创建错误响应

    Args:
        message: 错误消息
        data: 错误数据

    Returns:
        BaseResponse: 错误响应对象
    """
    return BaseResponse[T | None](success=False, message=message or "", data=data)


def page(data: list[T], page: int, page_size: int, total: int, message: str | None = None) -> PageResponse[T]:
    """创建分页响应

    Args:
        data: 数据列表
        page: 当前页码
        page_size: 每页大小
        total: 总记录数
        message: 响应消息

    Returns:
        PageResponse: 分页响应对象
    """
    pagination = Pagination(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
    )

    return PageResponse[T](success=True, message=message or "", data=data, pagination=pagination)


# 向后兼容的别名（已弃用，请使用小写版本）
Success = success
Error = error
Page = page
