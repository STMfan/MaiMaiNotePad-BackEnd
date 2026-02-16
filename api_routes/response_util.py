from typing import Any, Optional, TypeVar, List

from models import BaseResponse, PageResponse, Pagination

T = TypeVar("T")


def Success(message: Optional[str] = None, data: Optional[T] = None) -> BaseResponse[Optional[T]]:
    return BaseResponse[Optional[T]](
        success=True,
        message=message or "",
        data=data
    )


def Error(message: Optional[str] = None, data: Optional[T] = None) -> BaseResponse[Optional[T]]:
    return BaseResponse[Optional[T]](
        success=False,
        message=message or "",
        data=data
    )


def Page(
    data: List[T],
    page: int,
    page_size: int,
    total: int,
    message: Optional[str] = None
) -> PageResponse[T]:
    pagination = Pagination(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0
    )

    return PageResponse[T](
        success=True,
        message=message or "",
        data=data,
        pagination=pagination
    )

