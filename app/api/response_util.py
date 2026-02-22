"""响应工具模块 - 提供统一的API响应格式化函数"""

from typing import Optional, TypeVar, List

from app.models.schemas import BaseResponse, PageResponse, Pagination

T = TypeVar("T")


def Success(message: Optional[str] = None, data: Optional[T] = None) -> BaseResponse[Optional[T]]:
    """创建成功响应

    Args:
        message: 响应消息
        data: 响应数据

    Returns:
        BaseResponse: 成功响应对象
    """
    return BaseResponse[Optional[T]](success=True, message=message or "", data=data)


def Error(message: Optional[str] = None, data: Optional[T] = None) -> BaseResponse[Optional[T]]:
    """创建错误响应

    Args:
        message: 错误消息
        data: 错误数据

    Returns:
        BaseResponse: 错误响应对象
    """
    return BaseResponse[Optional[T]](success=False, message=message or "", data=data)


def Page(data: List[T], page: int, page_size: int, total: int, message: Optional[str] = None) -> PageResponse[T]:
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
