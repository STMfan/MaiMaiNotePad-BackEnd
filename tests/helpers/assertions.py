"""
测试断言辅助函数
提供常用的断言方法，简化测试代码
"""


def assert_success_response(response, expected_data_keys=None):
    """
    断言成功响应格式和内容

    Args:
        response: TestClient 响应对象
        expected_data_keys: 期望在 data 中存在的键列表
    """
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data.get("success") is True, f"Expected success=True, got {data}"
    assert "data" in data, f"Expected 'data' key in response, got {data}"

    if expected_data_keys:
        for key in expected_data_keys:
            assert key in data["data"], f"Expected key '{key}' in data, got {data['data'].keys()}"


def assert_pagination_response(response, expected_page, expected_page_size):
    """
    断言分页响应格式

    Args:
        response: TestClient 响应对象
        expected_page: 期望的页码
        expected_page_size: 期望的每页数量
    """
    assert response.status_code == 200

    data = response.json()
    assert "pagination" in data, f"Expected 'pagination' key, got {data.keys()}"

    pagination = data["pagination"]
    assert pagination["page"] == expected_page, f"Expected page {expected_page}, got {pagination['page']}"
    assert (
        pagination["page_size"] == expected_page_size
    ), f"Expected page_size {expected_page_size}, got {pagination['page_size']}"
    assert "total" in pagination
    assert "total_pages" in pagination


def assert_error_response(response, expected_status_codes: int | list[int], expected_message_keywords: str | list[str]):
    """
    断言错误响应格式和内容
    处理 FastAPI 验证错误（422 with 'detail'）和自定义 API 错误（with 'error'）

    Args:
        response: TestClient 响应对象
        expected_status_codes: 期望的状态码或状态码列表
        expected_message_keywords: 期望在错误消息中出现的关键词或关键词列表
    """
    # 标准化输入为列表
    if isinstance(expected_status_codes, int):
        expected_status_codes = [expected_status_codes]
    if isinstance(expected_message_keywords, str):
        expected_message_keywords = [expected_message_keywords]

    # 检查状态码
    assert (
        response.status_code in expected_status_codes
    ), f"Expected status code in {expected_status_codes}, got {response.status_code}"

    data = response.json()

    # 处理 FastAPI 验证错误（422）
    if "detail" in data:
        detail = data["detail"]
        if isinstance(detail, list):
            # 提取所有错误消息
            error_messages = []
            for error in detail:
                if isinstance(error, dict):
                    error_messages.append(error.get("msg", ""))
                    error_messages.append(str(error.get("loc", "")))
            combined_message = " ".join(error_messages).lower()
        else:
            combined_message = str(detail).lower()

        # 检查是否有任何关键词匹配
        keyword_found = any(keyword.lower() in combined_message for keyword in expected_message_keywords)

        assert keyword_found, f"Expected one of {expected_message_keywords} in error message, got: {data}"

    # 处理自定义 API 错误
    elif "error" in data:
        error_message = data["error"].get("message", "").lower()

        # 检查是否有任何关键词匹配
        keyword_found = any(keyword.lower() in error_message for keyword in expected_message_keywords)

        assert keyword_found, f"Expected one of {expected_message_keywords} in error message, got: {error_message}"

    else:
        # 未知错误格式
        raise AssertionError(f"Unknown error response format: {data}")


def assert_model_fields(model_dict, expected_fields):
    """
    断言模型字典包含期望的字段

    Args:
        model_dict: 模型的字典表示
        expected_fields: 期望存在的字段列表
    """
    for field in expected_fields:
        assert field in model_dict, f"Expected field '{field}' in model, got {model_dict.keys()}"


def assert_list_response(response, expected_min_length=None, expected_max_length=None):
    """
    断言列表响应

    Args:
        response: TestClient 响应对象
        expected_min_length: 期望的最小列表长度
        expected_max_length: 期望的最大列表长度
    """
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list), f"Expected list, got {type(data['data'])}"

    if expected_min_length is not None:
        assert (
            len(data["data"]) >= expected_min_length
        ), f"Expected at least {expected_min_length} items, got {len(data['data'])}"

    if expected_max_length is not None:
        assert (
            len(data["data"]) <= expected_max_length
        ), f"Expected at most {expected_max_length} items, got {len(data['data'])}"
