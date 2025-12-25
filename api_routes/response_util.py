from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse

def create_response(
    success: bool = False,
    message: Optional[str] = None,
    data: Optional[Any] = None,
    pagination: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    response_data: Dict[str, Any] = {
        "success": success,
        "message": "",
        "data": {}
    }
    
    if message is not None:
        response_data["message"] = message
    
    if data is not None:
        response_data["data"] = data
    
    if pagination is not None:
        response_data["pagination"] = pagination
    
    return JSONResponse(content=response_data)


def Success(message: Optional[str] = None, data: Optional[Any] = None) -> JSONResponse:
    return create_response(success=True,message=message,data=data)

def Error(message: Optional[str] = None, data: Optional[Any] = None) -> JSONResponse:
    return create_response(success=False,message=message,data=data)



def Page(
    data: Any,
    page: int,
    page_size: int,
    total: int,
    message: Optional[str] = None
) -> JSONResponse:
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
    }
    
    return create_response(
        success=True,
        message=message,
        data=data,
        pagination=pagination
    )


