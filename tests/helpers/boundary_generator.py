"""
边界值生成器模块

提供用于自动生成边界值和极端情况测试用例的工具类。
用于系统化地测试所有函数的边界情况和边界值处理。
"""

from typing import Any, List, Dict, Optional, Callable, Union, Type
from dataclasses import dataclass
from itertools import combinations
import sys
import uuid
from datetime import datetime, timedelta


@dataclass
class BoundaryValue:
    """
    边界值数据类

    表示一个边界值测试用例，包含值、描述和预期行为。
    """

    value: Any
    description: str
    expected_behavior: str = "handle_gracefully"  # handle_gracefully, raise_exception, return_none
    category: str = "boundary"  # boundary, null, empty, max, min, extreme


class BoundaryValueGenerator:
    """
    边界值生成器类

    自动生成各种类型的边界值和极端情况测试用例。
    支持生成空值、最大值、最小值、边界条件等多种测试场景。

    Example:
        >>> generator = BoundaryValueGenerator()
        >>> # 生成字符串边界值
        >>> string_boundaries = generator.generate_string_boundaries()
        >>> for boundary in string_boundaries:
        ...     print(f"{boundary.description}: {boundary.value}")

        >>> # 生成整数边界值
        >>> int_boundaries = generator.generate_integer_boundaries()
        >>> for boundary in int_boundaries:
        ...     print(f"{boundary.description}: {boundary.value}")
    """

    def __init__(self):
        """初始化边界值生成器"""
        self._max_string_length = 10000
        self._max_list_length = 1000

    def generate_null_values(self) -> List[BoundaryValue]:
        """
        生成空值测试用例

        包括 None、空字符串、空列表、空字典等。

        Returns:
            List[BoundaryValue]: 空值边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> null_values = generator.generate_null_values()
            >>> assert any(bv.value is None for bv in null_values)
        """
        return [
            BoundaryValue(value=None, description="None value", expected_behavior="handle_gracefully", category="null"),
            BoundaryValue(
                value="", description="Empty string", expected_behavior="handle_gracefully", category="empty"
            ),
            BoundaryValue(value=[], description="Empty list", expected_behavior="handle_gracefully", category="empty"),
            BoundaryValue(
                value={}, description="Empty dictionary", expected_behavior="handle_gracefully", category="empty"
            ),
            BoundaryValue(
                value=tuple(), description="Empty tuple", expected_behavior="handle_gracefully", category="empty"
            ),
            BoundaryValue(
                value=set(), description="Empty set", expected_behavior="handle_gracefully", category="empty"
            ),
        ]

    def generate_null_test_cases(
        self, function: Callable, param_name: str, include_nested: bool = True
    ) -> List[Dict[str, Any]]:
        """
        为指定函数和参数生成空值测试用例

        生成全面的空值测试场景，包括：
        - 直接的 None 值
        - 空容器（空字符串、空列表、空字典等）
        - 嵌套结构中的空值（如果 include_nested=True）

        Args:
            function: 要测试的函数
            param_name: 参数名称
            include_nested: 是否包含嵌套结构中的空值测试

        Returns:
            List[Dict[str, Any]]: 空值测试用例列表

        Example:
            >>> def process_user(user_data: dict) -> bool:
            ...     return user_data is not None

            >>> generator = BoundaryValueGenerator()
            >>> test_cases = generator.generate_null_test_cases(
            ...     function=process_user,
            ...     param_name="user_data",
            ...     include_nested=True
            ... )
            >>> assert len(test_cases) > 0
        """
        test_cases = []

        # 基本空值测试
        basic_null_values = self.generate_null_values()
        for boundary in basic_null_values:
            test_case = {
                "function": function,
                "param_name": param_name,
                "param_value": boundary.value,
                "description": f"{function.__name__}({param_name}={boundary.description})",
                "expected_behavior": boundary.expected_behavior,
                "category": boundary.category,
                "test_type": "basic_null",
            }
            test_cases.append(test_case)

        # 嵌套结构中的空值测试
        if include_nested:
            nested_null_cases = [
                BoundaryValue(
                    value=[None],
                    description="List with single None element",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value=[None, None, None],
                    description="List with multiple None elements",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value=[None, "value", None],
                    description="List with mixed None and non-None elements",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value={"key": None},
                    description="Dictionary with None value",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value={"key1": None, "key2": None},
                    description="Dictionary with multiple None values",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value={"key1": None, "key2": "value"},
                    description="Dictionary with mixed None and non-None values",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value={"nested": {"inner": None}},
                    description="Nested dictionary with None value",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value=[{"key": None}],
                    description="List of dictionaries with None value",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value={"list": [None, None]},
                    description="Dictionary with list containing None values",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value=(None,),
                    description="Tuple with single None element",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
                BoundaryValue(
                    value=(None, None, None),
                    description="Tuple with multiple None elements",
                    expected_behavior="handle_gracefully",
                    category="null",
                ),
            ]

            for boundary in nested_null_cases:
                test_case = {
                    "function": function,
                    "param_name": param_name,
                    "param_value": boundary.value,
                    "description": f"{function.__name__}({param_name}={boundary.description})",
                    "expected_behavior": boundary.expected_behavior,
                    "category": boundary.category,
                    "test_type": "nested_null",
                }
                test_cases.append(test_case)

        return test_cases

    def generate_null_combinations(self, function: Callable, param_names: List[str]) -> List[Dict[str, Any]]:
        """
        为多个参数生成空值组合测试用例

        测试多个参数同时为空值的情况，用于发现参数组合的边界情况。

        Args:
            function: 要测试的函数
            param_names: 参数名称列表

        Returns:
            List[Dict[str, Any]]: 空值组合测试用例列表

        Example:
            >>> def create_user(username: str, email: str, password: str) -> dict:
            ...     return {"username": username, "email": email}

            >>> generator = BoundaryValueGenerator()
            >>> test_cases = generator.generate_null_combinations(
            ...     function=create_user,
            ...     param_names=["username", "email", "password"]
            ... )
            >>> assert len(test_cases) > 0
        """
        test_cases = []

        # 单个参数为 None 的情况
        for param_name in param_names:
            test_case = {
                "function": function,
                "params": {name: None if name == param_name else "valid_value" for name in param_names},
                "description": f"{function.__name__} with {param_name}=None",
                "expected_behavior": "handle_gracefully",
                "category": "null",
                "test_type": "single_null_param",
            }
            test_cases.append(test_case)

        # 所有参数都为 None 的情况
        test_case = {
            "function": function,
            "params": {name: None for name in param_names},
            "description": f"{function.__name__} with all params=None",
            "expected_behavior": "handle_gracefully",
            "category": "null",
            "test_type": "all_null_params",
        }
        test_cases.append(test_case)

        # 两两组合为 None 的情况（如果参数数量 >= 2）
        if len(param_names) >= 2:
            from itertools import combinations

            for combo in combinations(param_names, 2):
                test_case = {
                    "function": function,
                    "params": {name: None if name in combo else "valid_value" for name in param_names},
                    "description": f"{function.__name__} with {', '.join(combo)}=None",
                    "expected_behavior": "handle_gracefully",
                    "category": "null",
                    "test_type": "multiple_null_params",
                }
                test_cases.append(test_case)

        return test_cases

    def generate_max_value_test_cases(
        self,
        function: Callable,
        param_name: str,
        param_type: str,
        max_value: Optional[Union[int, float, str]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        为指定函数和参数生成最大值测试用例

        生成全面的最大值测试场景，包括：
        - 最大值本身
        - 刚好低于最大值的值
        - 刚好超过最大值的值
        - 系统级最大值（如果适用）

        Args:
            function: 要测试的函数
            param_name: 参数名称
            param_type: 参数类型 ("string", "integer", "float", "list", "dict")
            max_value: 最大值限制（根据类型不同含义不同）
                - string: 最大字符串长度
                - integer/float: 最大数值
                - list: 最大列表长度
                - dict: 最大键数量
            **kwargs: 传递给边界值生成器的额外参数

        Returns:
            List[Dict[str, Any]]: 最大值测试用例列表

        Example:
            >>> def validate_age(age: int) -> bool:
            ...     return 0 <= age <= 150

            >>> generator = BoundaryValueGenerator()
            >>> test_cases = generator.generate_max_value_test_cases(
            ...     function=validate_age,
            ...     param_name="age",
            ...     param_type="integer",
            ...     max_value=150
            ... )
            >>> assert any(tc["param_value"] == 150 for tc in test_cases)
            >>> assert any(tc["param_value"] == 149 for tc in test_cases)
            >>> assert any(tc["param_value"] == 151 for tc in test_cases)
        """
        test_cases = []

        if param_type == "string":
            max_length = max_value if max_value is not None else self._max_string_length

            # 最大长度字符串
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": "a" * max_length,
                    "description": f"{function.__name__}({param_name}=max_length_string[{max_length}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "at_max",
                }
            )

            # 刚好低于最大长度
            if max_length > 0:
                test_cases.append(
                    {
                        "function": function,
                        "param_name": param_name,
                        "param_value": "a" * (max_length - 1),
                        "description": f"{function.__name__}({param_name}=below_max_string[{max_length - 1}])",
                        "expected_behavior": "handle_gracefully",
                        "category": "max",
                        "test_type": "below_max",
                    }
                )

            # 刚好超过最大长度
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": "a" * (max_length + 1),
                    "description": f"{function.__name__}({param_name}=above_max_string[{max_length + 1}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "above_max",
                }
            )

            # 远超最大长度
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": "a" * (max_length * 2),
                    "description": f"{function.__name__}({param_name}=far_above_max_string[{max_length * 2}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "far_above_max",
                }
            )

        elif param_type == "integer":
            max_int = max_value if max_value is not None else sys.maxsize

            # 最大值
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": max_int,
                    "description": f"{function.__name__}({param_name}=max_value[{max_int}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "at_max",
                }
            )

            # 刚好低于最大值
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": max_int - 1,
                    "description": f"{function.__name__}({param_name}=below_max[{max_int - 1}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "below_max",
                }
            )

            # 刚好超过最大值
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": max_int + 1,
                    "description": f"{function.__name__}({param_name}=above_max[{max_int + 1}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "above_max",
                }
            )

            # 系统最大值（如果不同于指定最大值）
            if max_value is not None and max_value != sys.maxsize:
                test_cases.append(
                    {
                        "function": function,
                        "param_name": param_name,
                        "param_value": sys.maxsize,
                        "description": f"{function.__name__}({param_name}=sys_max[{sys.maxsize}])",
                        "expected_behavior": "raise_exception",
                        "category": "extreme",
                        "test_type": "system_max",
                    }
                )

        elif param_type == "float":
            max_float = max_value if max_value is not None else sys.float_info.max

            # 最大值
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": max_float,
                    "description": f"{function.__name__}({param_name}=max_value[{max_float}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "at_max",
                }
            )

            # 刚好低于最大值
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": max_float - 0.1,
                    "description": f"{function.__name__}({param_name}=below_max[{max_float - 0.1}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "below_max",
                }
            )

            # 刚好超过最大值
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": max_float + 0.1,
                    "description": f"{function.__name__}({param_name}=above_max[{max_float + 0.1}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "above_max",
                }
            )

            # 正无穷大
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": float("inf"),
                    "description": f"{function.__name__}({param_name}=positive_infinity)",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "infinity",
                }
            )

            # 系统最大值（如果不同于指定最大值）
            if max_value is not None and max_value != sys.float_info.max:
                test_cases.append(
                    {
                        "function": function,
                        "param_name": param_name,
                        "param_value": sys.float_info.max,
                        "description": f"{function.__name__}({param_name}=sys_max[{sys.float_info.max}])",
                        "expected_behavior": "raise_exception",
                        "category": "extreme",
                        "test_type": "system_max",
                    }
                )

        elif param_type == "list":
            max_length = max_value if max_value is not None else self._max_list_length
            element_type = kwargs.get("element_type", str)

            # 根据元素类型生成示例元素
            if element_type == str:
                sample_element = "test"
            elif element_type == int:
                sample_element = 1
            elif element_type == float:
                sample_element = 1.0
            else:
                sample_element = "test"

            # 最大长度列表
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": [sample_element] * max_length,
                    "description": f"{function.__name__}({param_name}=max_length_list[{max_length}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "at_max",
                }
            )

            # 刚好低于最大长度
            if max_length > 0:
                test_cases.append(
                    {
                        "function": function,
                        "param_name": param_name,
                        "param_value": [sample_element] * (max_length - 1),
                        "description": f"{function.__name__}({param_name}=below_max_list[{max_length - 1}])",
                        "expected_behavior": "handle_gracefully",
                        "category": "max",
                        "test_type": "below_max",
                    }
                )

            # 刚好超过最大长度
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": [sample_element] * (max_length + 1),
                    "description": f"{function.__name__}({param_name}=above_max_list[{max_length + 1}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "above_max",
                }
            )

            # 远超最大长度
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": [sample_element] * (max_length * 2),
                    "description": f"{function.__name__}({param_name}=far_above_max_list[{max_length * 2}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "far_above_max",
                }
            )

        elif param_type == "dict":
            max_keys = max_value if max_value is not None else 1000

            # 最大键数字典
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": {f"key_{i}": f"value_{i}" for i in range(max_keys)},
                    "description": f"{function.__name__}({param_name}=max_keys_dict[{max_keys}])",
                    "expected_behavior": "handle_gracefully",
                    "category": "max",
                    "test_type": "at_max",
                }
            )

            # 刚好低于最大键数
            if max_keys > 0:
                test_cases.append(
                    {
                        "function": function,
                        "param_name": param_name,
                        "param_value": {f"key_{i}": f"value_{i}" for i in range(max_keys - 1)},
                        "description": f"{function.__name__}({param_name}=below_max_dict[{max_keys - 1}])",
                        "expected_behavior": "handle_gracefully",
                        "category": "max",
                        "test_type": "below_max",
                    }
                )

            # 刚好超过最大键数
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": {f"key_{i}": f"value_{i}" for i in range(max_keys + 1)},
                    "description": f"{function.__name__}({param_name}=above_max_dict[{max_keys + 1}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "above_max",
                }
            )

            # 远超最大键数
            test_cases.append(
                {
                    "function": function,
                    "param_name": param_name,
                    "param_value": {f"key_{i}": f"value_{i}" for i in range(max_keys * 2)},
                    "description": f"{function.__name__}({param_name}=far_above_max_dict[{max_keys * 2}])",
                    "expected_behavior": "raise_exception",
                    "category": "extreme",
                    "test_type": "far_above_max",
                }
            )

        else:
            raise ValueError(f"Unsupported parameter type for max value generation: {param_type}")

        return test_cases

    def generate_string_boundaries(self, max_length: Optional[int] = None) -> List[BoundaryValue]:
        """
        生成字符串边界值测试用例

        包括空字符串、单字符、超长字符串、特殊字符等。

        Args:
            max_length: 最大字符串长度，默认为 10000

        Returns:
            List[BoundaryValue]: 字符串边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> string_boundaries = generator.generate_string_boundaries(max_length=100)
            >>> assert any(len(bv.value) == 100 for bv in string_boundaries if isinstance(bv.value, str))
        """
        if max_length is None:
            max_length = self._max_string_length

        return [
            BoundaryValue(
                value="", description="Empty string", expected_behavior="handle_gracefully", category="empty"
            ),
            BoundaryValue(
                value=" ", description="Single space", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value="a", description="Single character", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value="a" * max_length,
                description=f"Maximum length string ({max_length} chars)",
                expected_behavior="handle_gracefully",
                category="max",
            ),
            BoundaryValue(
                value="a" * (max_length + 1),
                description=f"Over maximum length string ({max_length + 1} chars)",
                expected_behavior="raise_exception",
                category="extreme",
            ),
            BoundaryValue(
                value="   ", description="Whitespace only", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value="\n\t\r",
                description="Special whitespace characters",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value="<script>alert('xss')</script>",
                description="XSS attempt",
                expected_behavior="handle_gracefully",
                category="extreme",
            ),
            BoundaryValue(
                value="'; DROP TABLE users; --",
                description="SQL injection attempt",
                expected_behavior="handle_gracefully",
                category="extreme",
            ),
            BoundaryValue(
                value="../../../etc/passwd",
                description="Path traversal attempt",
                expected_behavior="handle_gracefully",
                category="extreme",
            ),
            BoundaryValue(
                value="你好世界🌍",
                description="Unicode characters (Chinese + emoji)",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value="\x00\x01\x02",
                description="Control characters",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
        ]

    def generate_integer_boundaries(
        self, min_value: Optional[int] = None, max_value: Optional[int] = None
    ) -> List[BoundaryValue]:
        """
        生成整数边界值测试用例

        包括零、负数、最大值、最小值等。

        Args:
            min_value: 最小整数值，默认为系统最小值
            max_value: 最大整数值，默认为系统最大值

        Returns:
            List[BoundaryValue]: 整数边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> int_boundaries = generator.generate_integer_boundaries(min_value=0, max_value=100)
            >>> assert any(bv.value == 0 for bv in int_boundaries)
            >>> assert any(bv.value == 100 for bv in int_boundaries)
        """
        if min_value is None:
            min_value = -sys.maxsize - 1
        if max_value is None:
            max_value = sys.maxsize

        boundaries = [
            BoundaryValue(value=0, description="Zero", expected_behavior="handle_gracefully", category="boundary"),
            BoundaryValue(value=1, description="One", expected_behavior="handle_gracefully", category="boundary"),
            BoundaryValue(
                value=-1, description="Negative one", expected_behavior="handle_gracefully", category="boundary"
            ),
        ]

        # 添加自定义范围的边界值
        if min_value != -sys.maxsize - 1:
            boundaries.extend(
                [
                    BoundaryValue(
                        value=min_value,
                        description=f"Minimum value ({min_value})",
                        expected_behavior="handle_gracefully",
                        category="min",
                    ),
                    BoundaryValue(
                        value=min_value - 1,
                        description=f"Below minimum value ({min_value - 1})",
                        expected_behavior="raise_exception",
                        category="extreme",
                    ),
                ]
            )

        if max_value != sys.maxsize:
            boundaries.extend(
                [
                    BoundaryValue(
                        value=max_value,
                        description=f"Maximum value ({max_value})",
                        expected_behavior="handle_gracefully",
                        category="max",
                    ),
                    BoundaryValue(
                        value=max_value + 1,
                        description=f"Above maximum value ({max_value + 1})",
                        expected_behavior="raise_exception",
                        category="extreme",
                    ),
                ]
            )

        # 添加系统级边界值
        boundaries.extend(
            [
                BoundaryValue(
                    value=sys.maxsize,
                    description=f"System max integer ({sys.maxsize})",
                    expected_behavior="handle_gracefully",
                    category="extreme",
                ),
                BoundaryValue(
                    value=-sys.maxsize - 1,
                    description=f"System min integer ({-sys.maxsize - 1})",
                    expected_behavior="handle_gracefully",
                    category="extreme",
                ),
            ]
        )

        return boundaries

    def generate_float_boundaries(
        self, min_value: Optional[float] = None, max_value: Optional[float] = None
    ) -> List[BoundaryValue]:
        """
        生成浮点数边界值测试用例

        包括零、负数、无穷大、NaN等。

        Args:
            min_value: 最小浮点数值
            max_value: 最大浮点数值

        Returns:
            List[BoundaryValue]: 浮点数边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> float_boundaries = generator.generate_float_boundaries()
            >>> assert any(bv.value == 0.0 for bv in float_boundaries)
        """
        boundaries = [
            BoundaryValue(
                value=0.0, description="Zero float", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value=1.0, description="One float", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value=-1.0, description="Negative one float", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value=float("inf"),
                description="Positive infinity",
                expected_behavior="handle_gracefully",
                category="extreme",
            ),
            BoundaryValue(
                value=float("-inf"),
                description="Negative infinity",
                expected_behavior="handle_gracefully",
                category="extreme",
            ),
            BoundaryValue(
                value=float("nan"),
                description="Not a Number (NaN)",
                expected_behavior="handle_gracefully",
                category="extreme",
            ),
            BoundaryValue(
                value=sys.float_info.min,
                description=f"System min float ({sys.float_info.min})",
                expected_behavior="handle_gracefully",
                category="min",
            ),
            BoundaryValue(
                value=sys.float_info.max,
                description=f"System max float ({sys.float_info.max})",
                expected_behavior="handle_gracefully",
                category="max",
            ),
            BoundaryValue(
                value=sys.float_info.epsilon,
                description=f"Float epsilon ({sys.float_info.epsilon})",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
        ]

        # 添加自定义范围的边界值
        if min_value is not None:
            boundaries.extend(
                [
                    BoundaryValue(
                        value=min_value,
                        description=f"Minimum value ({min_value})",
                        expected_behavior="handle_gracefully",
                        category="min",
                    ),
                    BoundaryValue(
                        value=min_value - 0.1,
                        description=f"Below minimum value ({min_value - 0.1})",
                        expected_behavior="raise_exception",
                        category="extreme",
                    ),
                ]
            )

        if max_value is not None:
            boundaries.extend(
                [
                    BoundaryValue(
                        value=max_value,
                        description=f"Maximum value ({max_value})",
                        expected_behavior="handle_gracefully",
                        category="max",
                    ),
                    BoundaryValue(
                        value=max_value + 0.1,
                        description=f"Above maximum value ({max_value + 0.1})",
                        expected_behavior="raise_exception",
                        category="extreme",
                    ),
                ]
            )

        return boundaries

    def generate_list_boundaries(
        self, max_length: Optional[int] = None, element_type: Optional[Type] = None
    ) -> List[BoundaryValue]:
        """
        生成列表边界值测试用例

        包括空列表、单元素列表、超长列表等。

        Args:
            max_length: 最大列表长度，默认为 1000
            element_type: 列表元素类型，用于生成特定类型的列表

        Returns:
            List[BoundaryValue]: 列表边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> list_boundaries = generator.generate_list_boundaries(max_length=10)
            >>> assert any(len(bv.value) == 0 for bv in list_boundaries if isinstance(bv.value, list))
        """
        if max_length is None:
            max_length = self._max_list_length

        # 根据元素类型生成示例元素
        if element_type == str:
            sample_element = "test"
        elif element_type == int:
            sample_element = 1
        elif element_type == float:
            sample_element = 1.0
        else:
            sample_element = "test"

        return [
            BoundaryValue(value=[], description="Empty list", expected_behavior="handle_gracefully", category="empty"),
            BoundaryValue(
                value=[sample_element],
                description="Single element list",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value=[sample_element] * max_length,
                description=f"Maximum length list ({max_length} elements)",
                expected_behavior="handle_gracefully",
                category="max",
            ),
            BoundaryValue(
                value=[sample_element] * (max_length + 1),
                description=f"Over maximum length list ({max_length + 1} elements)",
                expected_behavior="raise_exception",
                category="extreme",
            ),
            BoundaryValue(
                value=[None],
                description="List with None element",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value=[None] * 10,
                description="List with multiple None elements",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
        ]

    def generate_dict_boundaries(self, max_keys: Optional[int] = None) -> List[BoundaryValue]:
        """
        生成字典边界值测试用例

        包括空字典、单键字典、超大字典等。

        Args:
            max_keys: 最大键数量，默认为 1000

        Returns:
            List[BoundaryValue]: 字典边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> dict_boundaries = generator.generate_dict_boundaries(max_keys=10)
            >>> assert any(len(bv.value) == 0 for bv in dict_boundaries if isinstance(bv.value, dict))
        """
        if max_keys is None:
            max_keys = 1000

        return [
            BoundaryValue(
                value={}, description="Empty dictionary", expected_behavior="handle_gracefully", category="empty"
            ),
            BoundaryValue(
                value={"key": "value"},
                description="Single key dictionary",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value={f"key_{i}": f"value_{i}" for i in range(max_keys)},
                description=f"Maximum keys dictionary ({max_keys} keys)",
                expected_behavior="handle_gracefully",
                category="max",
            ),
            BoundaryValue(
                value={f"key_{i}": f"value_{i}" for i in range(max_keys + 1)},
                description=f"Over maximum keys dictionary ({max_keys + 1} keys)",
                expected_behavior="raise_exception",
                category="extreme",
            ),
            BoundaryValue(
                value={"key": None},
                description="Dictionary with None value",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value={"": "empty_key"},
                description="Dictionary with empty string key",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
        ]

    def generate_datetime_boundaries(self) -> List[BoundaryValue]:
        """
        生成日期时间边界值测试用例

        包括过去、未来、极端日期等。

        Returns:
            List[BoundaryValue]: 日期时间边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> datetime_boundaries = generator.generate_datetime_boundaries()
            >>> assert any(isinstance(bv.value, datetime) for bv in datetime_boundaries)
        """
        now = datetime.now()

        return [
            BoundaryValue(
                value=datetime.min,
                description="Minimum datetime (0001-01-01)",
                expected_behavior="handle_gracefully",
                category="min",
            ),
            BoundaryValue(
                value=datetime.max,
                description="Maximum datetime (9999-12-31)",
                expected_behavior="handle_gracefully",
                category="max",
            ),
            BoundaryValue(
                value=now, description="Current datetime", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value=now - timedelta(days=365 * 100),
                description="100 years ago",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value=now + timedelta(days=365 * 100),
                description="100 years in future",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value=datetime(1970, 1, 1),
                description="Unix epoch start",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value=datetime(2038, 1, 19, 3, 14, 7),
                description="Unix 32-bit timestamp overflow",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
        ]

    def generate_boolean_boundaries(self) -> List[BoundaryValue]:
        """
        生成布尔值边界值测试用例

        包括 True、False 和类似布尔值的其他值。

        Returns:
            List[BoundaryValue]: 布尔值边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> bool_boundaries = generator.generate_boolean_boundaries()
            >>> assert any(bv.value is True for bv in bool_boundaries)
        """
        return [
            BoundaryValue(value=True, description="True", expected_behavior="handle_gracefully", category="boundary"),
            BoundaryValue(value=False, description="False", expected_behavior="handle_gracefully", category="boundary"),
            BoundaryValue(
                value=1, description="Truthy integer (1)", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value=0, description="Falsy integer (0)", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value="", description="Falsy empty string", expected_behavior="handle_gracefully", category="boundary"
            ),
            BoundaryValue(
                value="true", description="String 'true'", expected_behavior="handle_gracefully", category="boundary"
            ),
        ]

    def generate_uuid_boundaries(self) -> List[BoundaryValue]:
        """
        生成 UUID 边界值测试用例

        包括有效 UUID、无效 UUID 字符串等。

        Returns:
            List[BoundaryValue]: UUID 边界值列表

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> uuid_boundaries = generator.generate_uuid_boundaries()
            >>> assert any("valid UUID" in bv.description for bv in uuid_boundaries)
        """
        return [
            BoundaryValue(
                value=str(uuid.uuid4()),
                description="Valid UUID v4",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value="00000000-0000-0000-0000-000000000000",
                description="Nil UUID",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
            BoundaryValue(
                value="invalid-uuid",
                description="Invalid UUID string",
                expected_behavior="raise_exception",
                category="extreme",
            ),
            BoundaryValue(
                value="", description="Empty UUID string", expected_behavior="raise_exception", category="extreme"
            ),
            BoundaryValue(
                value="12345678-1234-1234-1234-123456789012",
                description="Valid UUID format",
                expected_behavior="handle_gracefully",
                category="boundary",
            ),
        ]

    def generate_all_boundaries(self, value_type: Optional[str] = None) -> Dict[str, List[BoundaryValue]]:
        """
        生成所有类型的边界值测试用例

        Args:
            value_type: 指定生成的值类型，如果为 None 则生成所有类型
                可选值: "string", "integer", "float", "list", "dict",
                       "datetime", "boolean", "uuid", "null"

        Returns:
            Dict[str, List[BoundaryValue]]: 按类型分组的边界值字典

        Example:
            >>> generator = BoundaryValueGenerator()
            >>> all_boundaries = generator.generate_all_boundaries()
            >>> assert "string" in all_boundaries
            >>> assert "integer" in all_boundaries

            >>> # 只生成字符串边界值
            >>> string_only = generator.generate_all_boundaries(value_type="string")
            >>> assert len(string_only) == 1
            >>> assert "string" in string_only
        """
        boundaries = {}

        if value_type is None or value_type == "null":
            boundaries["null"] = self.generate_null_values()

        if value_type is None or value_type == "string":
            boundaries["string"] = self.generate_string_boundaries()

        if value_type is None or value_type == "integer":
            boundaries["integer"] = self.generate_integer_boundaries()

        if value_type is None or value_type == "float":
            boundaries["float"] = self.generate_float_boundaries()

        if value_type is None or value_type == "list":
            boundaries["list"] = self.generate_list_boundaries()

        if value_type is None or value_type == "dict":
            boundaries["dict"] = self.generate_dict_boundaries()

        if value_type is None or value_type == "datetime":
            boundaries["datetime"] = self.generate_datetime_boundaries()

        if value_type is None or value_type == "boolean":
            boundaries["boolean"] = self.generate_boolean_boundaries()

        if value_type is None or value_type == "uuid":
            boundaries["uuid"] = self.generate_uuid_boundaries()

        return boundaries

    def generate_concurrent_test_cases(
        self,
        function: Callable,
        num_threads: Optional[int] = None,
        num_operations: Optional[int] = None,
        operation_type: str = "mixed",
    ) -> List[Dict[str, Any]]:
        """
        为指定函数生成并发测试用例

        生成用于测试并发/并行执行场景的测试用例，包括：
        - 多线程同时访问
        - 竞态条件测试
        - 线程安全性验证
        - 并发写入冲突
        - 并发读取一致性

        Args:
            function: 要测试的函数
            num_threads: 并发线程数，默认为 [2, 5, 10, 50, 100]
            num_operations: 每个线程的操作次数，默认为 [1, 10, 100]
            operation_type: 操作类型
                - "read": 只读操作
                - "write": 只写操作
                - "mixed": 混合读写操作
                - "same_resource": 访问相同资源
                - "different_resources": 访问不同资源

        Returns:
            List[Dict[str, Any]]: 并发测试用例列表，每个测试用例包含：
                - function: 函数引用
                - num_threads: 线程数
                - num_operations: 操作次数
                - operation_type: 操作类型
                - description: 测试描述
                - expected_behavior: 预期行为
                - category: 测试类别
                - test_type: 测试类型

        Example:
            >>> def increment_counter(counter_dict, key):
            ...     counter_dict[key] = counter_dict.get(key, 0) + 1

            >>> generator = BoundaryValueGenerator()
            >>> test_cases = generator.generate_concurrent_test_cases(
            ...     function=increment_counter,
            ...     num_threads=[2, 10],
            ...     num_operations=[10, 100],
            ...     operation_type="write"
            ... )
            >>> assert len(test_cases) > 0
            >>> assert all("num_threads" in tc for tc in test_cases)
        """
        # 默认线程数配置
        if num_threads is None:
            thread_counts = [2, 5, 10, 50, 100]
        elif isinstance(num_threads, int):
            thread_counts = [num_threads]
        else:
            thread_counts = num_threads

        # 默认操作次数配置
        if num_operations is None:
            operation_counts = [1, 10, 100]
        elif isinstance(num_operations, int):
            operation_counts = [num_operations]
        else:
            operation_counts = num_operations

        test_cases = []

        # 生成不同线程数和操作次数的组合
        for threads in thread_counts:
            for operations in operation_counts:
                # 基本并发测试
                test_cases.append(
                    {
                        "function": function,
                        "num_threads": threads,
                        "num_operations": operations,
                        "operation_type": operation_type,
                        "description": f"{function.__name__} with {threads} threads, {operations} operations each ({operation_type})",
                        "expected_behavior": "thread_safe",
                        "category": "concurrent",
                        "test_type": "basic_concurrent",
                    }
                )

        # 竞态条件测试（多个线程同时访问相同资源）
        for threads in [2, 5, 10]:
            test_cases.append(
                {
                    "function": function,
                    "num_threads": threads,
                    "num_operations": 100,
                    "operation_type": "same_resource",
                    "description": f"{function.__name__} race condition test with {threads} threads accessing same resource",
                    "expected_behavior": "no_race_condition",
                    "category": "concurrent",
                    "test_type": "race_condition",
                }
            )

        # 高并发压力测试
        test_cases.append(
            {
                "function": function,
                "num_threads": 100,
                "num_operations": 1000,
                "operation_type": operation_type,
                "description": f"{function.__name__} high concurrency stress test (100 threads, 1000 ops each)",
                "expected_behavior": "handle_gracefully",
                "category": "concurrent",
                "test_type": "stress_test",
            }
        )

        # 并发写入冲突测试
        if operation_type in ["write", "mixed"]:
            test_cases.append(
                {
                    "function": function,
                    "num_threads": 10,
                    "num_operations": 50,
                    "operation_type": "write",
                    "description": f"{function.__name__} concurrent write conflict test",
                    "expected_behavior": "handle_write_conflicts",
                    "category": "concurrent",
                    "test_type": "write_conflict",
                }
            )

        # 并发读取一致性测试
        if operation_type in ["read", "mixed"]:
            test_cases.append(
                {
                    "function": function,
                    "num_threads": 20,
                    "num_operations": 100,
                    "operation_type": "read",
                    "description": f"{function.__name__} concurrent read consistency test",
                    "expected_behavior": "consistent_reads",
                    "category": "concurrent",
                    "test_type": "read_consistency",
                }
            )

        # 死锁检测测试
        test_cases.append(
            {
                "function": function,
                "num_threads": 5,
                "num_operations": 20,
                "operation_type": "mixed",
                "description": f"{function.__name__} deadlock detection test",
                "expected_behavior": "no_deadlock",
                "category": "concurrent",
                "test_type": "deadlock_detection",
            }
        )

        # 线程安全边界测试（单线程 vs 多线程）
        test_cases.append(
            {
                "function": function,
                "num_threads": 1,
                "num_operations": 100,
                "operation_type": operation_type,
                "description": f"{function.__name__} single thread baseline",
                "expected_behavior": "handle_gracefully",
                "category": "concurrent",
                "test_type": "baseline",
            }
        )

        return test_cases

    def generate_test_cases(
        self, function: Callable, param_name: str, param_type: str, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        为指定函数和参数生成测试用例

        Args:
            function: 要测试的函数
            param_name: 参数名称
            param_type: 参数类型 ("string", "integer", "float", "list", "dict", etc.)
            **kwargs: 传递给边界值生成器的额外参数

        Returns:
            List[Dict[str, Any]]: 测试用例列表，每个测试用例包含：
                - function: 函数引用
                - param_name: 参数名称
                - param_value: 参数值
                - description: 测试描述
                - expected_behavior: 预期行为
                - category: 边界值类别

        Example:
            >>> def my_function(name: str) -> str:
            ...     return f"Hello, {name}"

            >>> generator = BoundaryValueGenerator()
            >>> test_cases = generator.generate_test_cases(
            ...     function=my_function,
            ...     param_name="name",
            ...     param_type="string",
            ...     max_length=100
            ... )
            >>> assert len(test_cases) > 0
            >>> assert all("param_value" in tc for tc in test_cases)
        """
        # 根据参数类型生成边界值
        if param_type == "string":
            boundaries = self.generate_string_boundaries(**kwargs)
        elif param_type == "integer":
            boundaries = self.generate_integer_boundaries(**kwargs)
        elif param_type == "float":
            boundaries = self.generate_float_boundaries(**kwargs)
        elif param_type == "list":
            boundaries = self.generate_list_boundaries(**kwargs)
        elif param_type == "dict":
            boundaries = self.generate_dict_boundaries(**kwargs)
        elif param_type == "datetime":
            boundaries = self.generate_datetime_boundaries()
        elif param_type == "boolean":
            boundaries = self.generate_boolean_boundaries()
        elif param_type == "uuid":
            boundaries = self.generate_uuid_boundaries()
        elif param_type == "null":
            boundaries = self.generate_null_values()
        else:
            raise ValueError(f"Unsupported parameter type: {param_type}")

        # 将边界值转换为测试用例
        test_cases = []
        for boundary in boundaries:
            test_case = {
                "function": function,
                "param_name": param_name,
                "param_value": boundary.value,
                "description": f"{function.__name__}({param_name}={boundary.description})",
                "expected_behavior": boundary.expected_behavior,
                "category": boundary.category,
            }
            test_cases.append(test_case)

        return test_cases
