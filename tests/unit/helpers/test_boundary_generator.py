"""
边界值生成器单元测试

测试 BoundaryValueGenerator 类的所有功能。
"""

import pytest
import sys
import math
from datetime import datetime
from tests.helpers.boundary_generator import BoundaryValueGenerator, BoundaryValue


class TestBoundaryValueGenerator:
    """测试 BoundaryValueGenerator 类"""
    
    @pytest.fixture
    def generator(self):
        """创建边界值生成器实例"""
        return BoundaryValueGenerator()
    
    def test_generate_null_values(self, generator):
        """测试生成空值"""
        null_values = generator.generate_null_values()
        
        # 验证返回列表
        assert isinstance(null_values, list)
        assert len(null_values) > 0
        
        # 验证包含 None
        assert any(bv.value is None for bv in null_values)
        
        # 验证包含空字符串
        assert any(bv.value == "" for bv in null_values)
        
        # 验证包含空列表
        assert any(bv.value == [] for bv in null_values)
        
        # 验证包含空字典
        assert any(bv.value == {} for bv in null_values)
        
        # 验证所有值都是 BoundaryValue 实例
        assert all(isinstance(bv, BoundaryValue) for bv in null_values)
        
        # 验证所有值都有描述
        assert all(bv.description for bv in null_values)
    
    def test_generate_string_boundaries(self, generator):
        """测试生成字符串边界值"""
        string_boundaries = generator.generate_string_boundaries(max_length=100)
        
        # 验证返回列表
        assert isinstance(string_boundaries, list)
        assert len(string_boundaries) > 0
        
        # 验证包含空字符串
        assert any(bv.value == "" for bv in string_boundaries)
        
        # 验证包含单字符
        assert any(bv.value == "a" for bv in string_boundaries)
        
        # 验证包含最大长度字符串
        assert any(len(bv.value) == 100 for bv in string_boundaries if isinstance(bv.value, str))
        
        # 验证包含超长字符串
        assert any(len(bv.value) == 101 for bv in string_boundaries if isinstance(bv.value, str))
        
        # 验证包含特殊字符
        assert any("xss" in bv.description.lower() for bv in string_boundaries)
        assert any("sql" in bv.description.lower() for bv in string_boundaries)
        assert any("path" in bv.description.lower() for bv in string_boundaries)
        
        # 验证包含 Unicode 字符
        assert any("unicode" in bv.description.lower() for bv in string_boundaries)
    
    def test_generate_integer_boundaries(self, generator):
        """测试生成整数边界值"""
        int_boundaries = generator.generate_integer_boundaries(min_value=0, max_value=100)
        
        # 验证返回列表
        assert isinstance(int_boundaries, list)
        assert len(int_boundaries) > 0
        
        # 验证包含零
        assert any(bv.value == 0 for bv in int_boundaries)
        
        # 验证包含正数
        assert any(bv.value == 1 for bv in int_boundaries)
        
        # 验证包含负数
        assert any(bv.value == -1 for bv in int_boundaries)
        
        # 验证包含最小值
        assert any(bv.value == 0 for bv in int_boundaries)
        
        # 验证包含最大值
        assert any(bv.value == 100 for bv in int_boundaries)
        
        # 验证包含超出范围的值
        assert any(bv.value == -1 for bv in int_boundaries)
        assert any(bv.value == 101 for bv in int_boundaries)
        
        # 验证包含系统级边界值
        assert any(bv.value == sys.maxsize for bv in int_boundaries)
        assert any(bv.value == -sys.maxsize - 1 for bv in int_boundaries)
    
    def test_generate_integer_boundaries_no_limits(self, generator):
        """测试生成整数边界值（无限制）"""
        int_boundaries = generator.generate_integer_boundaries()
        
        # 验证返回列表
        assert isinstance(int_boundaries, list)
        assert len(int_boundaries) > 0
        
        # 验证包含基本值
        assert any(bv.value == 0 for bv in int_boundaries)
        assert any(bv.value == 1 for bv in int_boundaries)
        assert any(bv.value == -1 for bv in int_boundaries)
    
    def test_generate_float_boundaries(self, generator):
        """测试生成浮点数边界值"""
        float_boundaries = generator.generate_float_boundaries(min_value=0.0, max_value=100.0)
        
        # 验证返回列表
        assert isinstance(float_boundaries, list)
        assert len(float_boundaries) > 0
        
        # 验证包含零
        assert any(bv.value == 0.0 for bv in float_boundaries)
        
        # 验证包含正数
        assert any(bv.value == 1.0 for bv in float_boundaries)
        
        # 验证包含负数
        assert any(bv.value == -1.0 for bv in float_boundaries)
        
        # 验证包含无穷大
        assert any(math.isinf(bv.value) and bv.value > 0 for bv in float_boundaries)
        assert any(math.isinf(bv.value) and bv.value < 0 for bv in float_boundaries)
        
        # 验证包含 NaN
        assert any(math.isnan(bv.value) for bv in float_boundaries)
        
        # 验证包含系统级边界值
        assert any(bv.value == sys.float_info.min for bv in float_boundaries)
        assert any(bv.value == sys.float_info.max for bv in float_boundaries)
        assert any(bv.value == sys.float_info.epsilon for bv in float_boundaries)
    
    def test_generate_list_boundaries(self, generator):
        """测试生成列表边界值"""
        list_boundaries = generator.generate_list_boundaries(max_length=10, element_type=str)
        
        # 验证返回列表
        assert isinstance(list_boundaries, list)
        assert len(list_boundaries) > 0
        
        # 验证包含空列表
        assert any(bv.value == [] for bv in list_boundaries)
        
        # 验证包含单元素列表
        assert any(len(bv.value) == 1 for bv in list_boundaries if isinstance(bv.value, list))
        
        # 验证包含最大长度列表
        assert any(len(bv.value) == 10 for bv in list_boundaries if isinstance(bv.value, list))
        
        # 验证包含超长列表
        assert any(len(bv.value) == 11 for bv in list_boundaries if isinstance(bv.value, list))
        
        # 验证包含 None 元素的列表
        assert any(None in bv.value for bv in list_boundaries if isinstance(bv.value, list) and len(bv.value) > 0)
    
    def test_generate_dict_boundaries(self, generator):
        """测试生成字典边界值"""
        dict_boundaries = generator.generate_dict_boundaries(max_keys=10)
        
        # 验证返回列表
        assert isinstance(dict_boundaries, list)
        assert len(dict_boundaries) > 0
        
        # 验证包含空字典
        assert any(bv.value == {} for bv in dict_boundaries)
        
        # 验证包含单键字典
        assert any(len(bv.value) == 1 for bv in dict_boundaries if isinstance(bv.value, dict))
        
        # 验证包含最大键数字典
        assert any(len(bv.value) == 10 for bv in dict_boundaries if isinstance(bv.value, dict))
        
        # 验证包含超大字典
        assert any(len(bv.value) == 11 for bv in dict_boundaries if isinstance(bv.value, dict))
        
        # 验证包含 None 值的字典
        assert any(None in bv.value.values() for bv in dict_boundaries if isinstance(bv.value, dict) and len(bv.value) > 0)
        
        # 验证包含空字符串键的字典
        assert any("" in bv.value for bv in dict_boundaries if isinstance(bv.value, dict) and len(bv.value) > 0)
    
    def test_generate_datetime_boundaries(self, generator):
        """测试生成日期时间边界值"""
        datetime_boundaries = generator.generate_datetime_boundaries()
        
        # 验证返回列表
        assert isinstance(datetime_boundaries, list)
        assert len(datetime_boundaries) > 0
        
        # 验证包含最小日期
        assert any(bv.value == datetime.min for bv in datetime_boundaries)
        
        # 验证包含最大日期
        assert any(bv.value == datetime.max for bv in datetime_boundaries)
        
        # 验证包含当前日期
        assert any(isinstance(bv.value, datetime) for bv in datetime_boundaries)
        
        # 验证包含 Unix epoch
        assert any(bv.value == datetime(1970, 1, 1) for bv in datetime_boundaries)
        
        # 验证所有值都是 datetime 实例
        assert all(isinstance(bv.value, datetime) for bv in datetime_boundaries)
    
    def test_generate_boolean_boundaries(self, generator):
        """测试生成布尔值边界值"""
        bool_boundaries = generator.generate_boolean_boundaries()
        
        # 验证返回列表
        assert isinstance(bool_boundaries, list)
        assert len(bool_boundaries) > 0
        
        # 验证包含 True
        assert any(bv.value is True for bv in bool_boundaries)
        
        # 验证包含 False
        assert any(bv.value is False for bv in bool_boundaries)
        
        # 验证包含类似布尔值的其他值
        assert any(bv.value == 1 for bv in bool_boundaries)
        assert any(bv.value == 0 for bv in bool_boundaries)
        assert any(bv.value == "" for bv in bool_boundaries)
    
    def test_generate_uuid_boundaries(self, generator):
        """测试生成 UUID 边界值"""
        uuid_boundaries = generator.generate_uuid_boundaries()
        
        # 验证返回列表
        assert isinstance(uuid_boundaries, list)
        assert len(uuid_boundaries) > 0
        
        # 验证包含有效 UUID
        assert any("valid" in bv.description.lower() for bv in uuid_boundaries)
        
        # 验证包含 Nil UUID
        assert any(bv.value == "00000000-0000-0000-0000-000000000000" for bv in uuid_boundaries)
        
        # 验证包含无效 UUID
        assert any(bv.value == "invalid-uuid" for bv in uuid_boundaries)
        
        # 验证包含空字符串
        assert any(bv.value == "" for bv in uuid_boundaries)
    
    def test_generate_all_boundaries(self, generator):
        """测试生成所有类型的边界值"""
        all_boundaries = generator.generate_all_boundaries()
        
        # 验证返回字典
        assert isinstance(all_boundaries, dict)
        
        # 验证包含所有类型
        expected_types = ["null", "string", "integer", "float", "list", "dict", "datetime", "boolean", "uuid"]
        for expected_type in expected_types:
            assert expected_type in all_boundaries
            assert isinstance(all_boundaries[expected_type], list)
            assert len(all_boundaries[expected_type]) > 0
    
    def test_generate_all_boundaries_specific_type(self, generator):
        """测试生成特定类型的边界值"""
        string_only = generator.generate_all_boundaries(value_type="string")
        
        # 验证只包含字符串类型
        assert isinstance(string_only, dict)
        assert len(string_only) == 1
        assert "string" in string_only
        assert isinstance(string_only["string"], list)
        assert len(string_only["string"]) > 0
    
    def test_generate_test_cases_string(self, generator):
        """测试为字符串参数生成测试用例"""
        def sample_function(name: str) -> str:
            return f"Hello, {name}"
        
        test_cases = generator.generate_test_cases(
            function=sample_function,
            param_name="name",
            param_type="string",
            max_length=100
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证每个测试用例的结构
        for tc in test_cases:
            assert "function" in tc
            assert "param_name" in tc
            assert "param_value" in tc
            assert "description" in tc
            assert "expected_behavior" in tc
            assert "category" in tc
            
            assert tc["function"] == sample_function
            assert tc["param_name"] == "name"
            assert isinstance(tc["description"], str)
            assert tc["expected_behavior"] in ["handle_gracefully", "raise_exception", "return_none"]
            assert tc["category"] in ["boundary", "null", "empty", "max", "min", "extreme"]
    
    def test_generate_test_cases_integer(self, generator):
        """测试为整数参数生成测试用例"""
        def sample_function(age: int) -> bool:
            return age >= 18
        
        test_cases = generator.generate_test_cases(
            function=sample_function,
            param_name="age",
            param_type="integer",
            min_value=0,
            max_value=150
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含边界值
        assert any(tc["param_value"] == 0 for tc in test_cases)
        assert any(tc["param_value"] == 150 for tc in test_cases)
        assert any(tc["param_value"] == -1 for tc in test_cases)
        assert any(tc["param_value"] == 151 for tc in test_cases)
    
    def test_generate_test_cases_list(self, generator):
        """测试为列表参数生成测试用例"""
        def sample_function(items: list) -> int:
            return len(items)
        
        test_cases = generator.generate_test_cases(
            function=sample_function,
            param_name="items",
            param_type="list",
            max_length=10
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含空列表
        assert any(tc["param_value"] == [] for tc in test_cases)
        
        # 验证包含不同长度的列表
        assert any(len(tc["param_value"]) == 1 for tc in test_cases if isinstance(tc["param_value"], list))
        assert any(len(tc["param_value"]) == 10 for tc in test_cases if isinstance(tc["param_value"], list))
    
    def test_generate_test_cases_unsupported_type(self, generator):
        """测试不支持的参数类型"""
        def sample_function(value):
            return value
        
        with pytest.raises(ValueError, match="Unsupported parameter type"):
            generator.generate_test_cases(
                function=sample_function,
                param_name="value",
                param_type="unsupported_type"
            )
    
    def test_boundary_value_dataclass(self):
        """测试 BoundaryValue 数据类"""
        bv = BoundaryValue(
            value="test",
            description="Test value",
            expected_behavior="handle_gracefully",
            category="boundary"
        )
        
        assert bv.value == "test"
        assert bv.description == "Test value"
        assert bv.expected_behavior == "handle_gracefully"
        assert bv.category == "boundary"
    
    def test_boundary_value_default_values(self):
        """测试 BoundaryValue 默认值"""
        bv = BoundaryValue(
            value="test",
            description="Test value"
        )
        
        assert bv.expected_behavior == "handle_gracefully"
        assert bv.category == "boundary"
    
    def test_generator_initialization(self, generator):
        """测试生成器初始化"""
        assert generator._max_string_length == 10000
        assert generator._max_list_length == 1000
    
    def test_string_boundaries_custom_max_length(self, generator):
        """测试自定义最大字符串长度"""
        custom_length = 50
        boundaries = generator.generate_string_boundaries(max_length=custom_length)
        
        # 验证包含自定义长度的字符串
        assert any(len(bv.value) == custom_length for bv in boundaries if isinstance(bv.value, str))
        assert any(len(bv.value) == custom_length + 1 for bv in boundaries if isinstance(bv.value, str))
    
    def test_list_boundaries_with_element_type(self, generator):
        """测试指定元素类型的列表边界值"""
        # 测试整数类型
        int_list_boundaries = generator.generate_list_boundaries(max_length=5, element_type=int)
        assert any(all(isinstance(x, int) for x in bv.value) for bv in int_list_boundaries if isinstance(bv.value, list) and len(bv.value) > 0)
        
        # 测试浮点数类型
        float_list_boundaries = generator.generate_list_boundaries(max_length=5, element_type=float)
        assert any(all(isinstance(x, float) for x in bv.value) for bv in float_list_boundaries if isinstance(bv.value, list) and len(bv.value) > 0)
        
        # 测试字符串类型
        str_list_boundaries = generator.generate_list_boundaries(max_length=5, element_type=str)
        assert any(all(isinstance(x, str) for x in bv.value) for bv in str_list_boundaries if isinstance(bv.value, list) and len(bv.value) > 0)
    
    def test_categories_are_correct(self, generator):
        """测试边界值类别正确性"""
        all_boundaries = generator.generate_all_boundaries()
        
        for type_name, boundaries in all_boundaries.items():
            for bv in boundaries:
                # 验证类别是有效的
                assert bv.category in ["boundary", "null", "empty", "max", "min", "extreme"]
                
                # 验证类别与值的对应关系
                if bv.value is None:
                    assert bv.category == "null"
                elif bv.value == "" or bv.value == [] or bv.value == {}:
                    # 空值可能是 empty、boundary 或 extreme（如果预期会抛出异常）
                    assert bv.category in ["empty", "boundary", "extreme"]
    
    def test_expected_behaviors_are_valid(self, generator):
        """测试预期行为的有效性"""
        all_boundaries = generator.generate_all_boundaries()
        
        valid_behaviors = ["handle_gracefully", "raise_exception", "return_none"]
        
        for type_name, boundaries in all_boundaries.items():
            for bv in boundaries:
                assert bv.expected_behavior in valid_behaviors
    
    def test_generate_null_test_cases_basic(self, generator):
        """测试生成基本空值测试用例"""
        def sample_function(data):
            return data
        
        test_cases = generator.generate_null_test_cases(
            function=sample_function,
            param_name="data",
            include_nested=False
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含基本空值
        assert any(tc["param_value"] is None for tc in test_cases)
        assert any(tc["param_value"] == "" for tc in test_cases)
        assert any(tc["param_value"] == [] for tc in test_cases)
        assert any(tc["param_value"] == {} for tc in test_cases)
        
        # 验证测试用例结构
        for tc in test_cases:
            assert "function" in tc
            assert "param_name" in tc
            assert "param_value" in tc
            assert "description" in tc
            assert "expected_behavior" in tc
            assert "category" in tc
            assert "test_type" in tc
            assert tc["test_type"] == "basic_null"
    
    def test_generate_null_test_cases_with_nested(self, generator):
        """测试生成包含嵌套结构的空值测试用例"""
        def sample_function(data):
            return data
        
        test_cases = generator.generate_null_test_cases(
            function=sample_function,
            param_name="data",
            include_nested=True
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含嵌套空值测试
        nested_cases = [tc for tc in test_cases if tc["test_type"] == "nested_null"]
        assert len(nested_cases) > 0
        
        # 验证包含列表中的 None
        assert any(tc["param_value"] == [None] for tc in nested_cases)
        assert any(tc["param_value"] == [None, None, None] for tc in nested_cases)
        
        # 验证包含字典中的 None
        assert any(tc["param_value"] == {"key": None} for tc in nested_cases)
        assert any(tc["param_value"] == {"key1": None, "key2": None} for tc in nested_cases)
        
        # 验证包含嵌套字典中的 None
        assert any(tc["param_value"] == {"nested": {"inner": None}} for tc in nested_cases)
        
        # 验证包含元组中的 None
        assert any(tc["param_value"] == (None,) for tc in nested_cases)
    
    def test_generate_null_test_cases_descriptions(self, generator):
        """测试空值测试用例的描述"""
        def my_function(param):
            return param
        
        test_cases = generator.generate_null_test_cases(
            function=my_function,
            param_name="param",
            include_nested=True
        )
        
        # 验证所有测试用例都有描述
        assert all(tc["description"] for tc in test_cases)
        
        # 验证描述包含函数名和参数名
        assert all("my_function" in tc["description"] for tc in test_cases)
        assert all("param" in tc["description"] for tc in test_cases)
    
    def test_generate_null_combinations_single_param(self, generator):
        """测试单个参数的空值组合"""
        def sample_function(username, email, password):
            return {"username": username, "email": email}
        
        test_cases = generator.generate_null_combinations(
            function=sample_function,
            param_names=["username", "email", "password"]
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含单个参数为 None 的测试用例
        single_null_cases = [tc for tc in test_cases if tc["test_type"] == "single_null_param"]
        assert len(single_null_cases) == 3  # 3个参数，每个都有一个测试用例
        
        # 验证每个参数都有对应的测试用例
        param_names = [tc["description"] for tc in single_null_cases]
        assert any("username=None" in desc for desc in param_names)
        assert any("email=None" in desc for desc in param_names)
        assert any("password=None" in desc for desc in param_names)
    
    def test_generate_null_combinations_all_params(self, generator):
        """测试所有参数都为 None 的组合"""
        def sample_function(param1, param2):
            return param1 or param2
        
        test_cases = generator.generate_null_combinations(
            function=sample_function,
            param_names=["param1", "param2"]
        )
        
        # 验证包含所有参数为 None 的测试用例
        all_null_cases = [tc for tc in test_cases if tc["test_type"] == "all_null_params"]
        assert len(all_null_cases) == 1
        
        # 验证所有参数都为 None
        all_null_case = all_null_cases[0]
        assert all(value is None for value in all_null_case["params"].values())
    
    def test_generate_null_combinations_multiple_params(self, generator):
        """测试多个参数组合为 None"""
        def sample_function(param1, param2, param3):
            return param1 or param2 or param3
        
        test_cases = generator.generate_null_combinations(
            function=sample_function,
            param_names=["param1", "param2", "param3"]
        )
        
        # 验证包含两两组合为 None 的测试用例
        multiple_null_cases = [tc for tc in test_cases if tc["test_type"] == "multiple_null_params"]
        assert len(multiple_null_cases) == 3  # C(3,2) = 3
        
        # 验证每个组合都有对应的测试用例
        descriptions = [tc["description"] for tc in multiple_null_cases]
        assert any("param1" in desc and "param2" in desc for desc in descriptions)
        assert any("param1" in desc and "param3" in desc for desc in descriptions)
        assert any("param2" in desc and "param3" in desc for desc in descriptions)
    
    def test_generate_null_combinations_single_param_only(self, generator):
        """测试只有一个参数的情况"""
        def sample_function(param):
            return param
        
        test_cases = generator.generate_null_combinations(
            function=sample_function,
            param_names=["param"]
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        
        # 应该有2个测试用例：单个参数为None + 所有参数为None（实际上是同一个）
        assert len(test_cases) == 2
        
        # 不应该有多参数组合的测试用例
        multiple_null_cases = [tc for tc in test_cases if tc["test_type"] == "multiple_null_params"]
        assert len(multiple_null_cases) == 0
    
    def test_null_test_cases_structure(self, generator):
        """测试空值测试用例的结构完整性"""
        def sample_function(data):
            return data
        
        test_cases = generator.generate_null_test_cases(
            function=sample_function,
            param_name="data",
            include_nested=True
        )
        
        # 验证每个测试用例都有必需的字段
        required_fields = ["function", "param_name", "param_value", "description", 
                          "expected_behavior", "category", "test_type"]
        
        for tc in test_cases:
            for field in required_fields:
                assert field in tc, f"Missing field: {field}"
            
            # 验证字段类型
            assert callable(tc["function"])
            assert isinstance(tc["param_name"], str)
            assert isinstance(tc["description"], str)
            assert isinstance(tc["expected_behavior"], str)
            assert isinstance(tc["category"], str)
            assert isinstance(tc["test_type"], str)
    
    def test_null_combinations_structure(self, generator):
        """测试空值组合测试用例的结构完整性"""
        def sample_function(param1, param2):
            return param1 or param2
        
        test_cases = generator.generate_null_combinations(
            function=sample_function,
            param_names=["param1", "param2"]
        )
        
        # 验证每个测试用例都有必需的字段
        required_fields = ["function", "params", "description", 
                          "expected_behavior", "category", "test_type"]
        
        for tc in test_cases:
            for field in required_fields:
                assert field in tc, f"Missing field: {field}"
            
            # 验证字段类型
            assert callable(tc["function"])
            assert isinstance(tc["params"], dict)
            assert isinstance(tc["description"], str)
            assert isinstance(tc["expected_behavior"], str)
            assert isinstance(tc["category"], str)
            assert isinstance(tc["test_type"], str)

    def test_generate_max_value_test_cases_string(self, generator):
        """测试生成字符串最大值测试用例"""
        def validate_username(username: str) -> bool:
            return len(username) <= 50
        
        test_cases = generator.generate_max_value_test_cases(
            function=validate_username,
            param_name="username",
            param_type="string",
            max_value=50
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含最大长度字符串
        at_max_cases = [tc for tc in test_cases if tc["test_type"] == "at_max"]
        assert len(at_max_cases) == 1
        assert len(at_max_cases[0]["param_value"]) == 50
        
        # 验证包含低于最大长度的字符串
        below_max_cases = [tc for tc in test_cases if tc["test_type"] == "below_max"]
        assert len(below_max_cases) == 1
        assert len(below_max_cases[0]["param_value"]) == 49
        
        # 验证包含超过最大长度的字符串
        above_max_cases = [tc for tc in test_cases if tc["test_type"] == "above_max"]
        assert len(above_max_cases) == 1
        assert len(above_max_cases[0]["param_value"]) == 51
        
        # 验证包含远超最大长度的字符串
        far_above_cases = [tc for tc in test_cases if tc["test_type"] == "far_above_max"]
        assert len(far_above_cases) == 1
        assert len(far_above_cases[0]["param_value"]) == 100
        
        # 验证测试用例结构
        for tc in test_cases:
            assert "function" in tc
            assert "param_name" in tc
            assert "param_value" in tc
            assert "description" in tc
            assert "expected_behavior" in tc
            assert "category" in tc
            assert "test_type" in tc
    
    def test_generate_max_value_test_cases_integer(self, generator):
        """测试生成整数最大值测试用例"""
        def validate_age(age: int) -> bool:
            return 0 <= age <= 150
        
        test_cases = generator.generate_max_value_test_cases(
            function=validate_age,
            param_name="age",
            param_type="integer",
            max_value=150
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含最大值
        assert any(tc["param_value"] == 150 and tc["test_type"] == "at_max" for tc in test_cases)
        
        # 验证包含低于最大值
        assert any(tc["param_value"] == 149 and tc["test_type"] == "below_max" for tc in test_cases)
        
        # 验证包含超过最大值
        assert any(tc["param_value"] == 151 and tc["test_type"] == "above_max" for tc in test_cases)
        
        # 验证包含系统最大值
        assert any(tc["param_value"] == sys.maxsize and tc["test_type"] == "system_max" for tc in test_cases)
        
        # 验证预期行为
        at_max = [tc for tc in test_cases if tc["test_type"] == "at_max"][0]
        assert at_max["expected_behavior"] == "handle_gracefully"
        
        above_max = [tc for tc in test_cases if tc["test_type"] == "above_max"][0]
        assert above_max["expected_behavior"] == "raise_exception"
    
    def test_generate_max_value_test_cases_float(self, generator):
        """测试生成浮点数最大值测试用例"""
        def validate_temperature(temp: float) -> bool:
            return -273.15 <= temp <= 1000.0
        
        test_cases = generator.generate_max_value_test_cases(
            function=validate_temperature,
            param_name="temp",
            param_type="float",
            max_value=1000.0
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含最大值
        assert any(tc["param_value"] == 1000.0 and tc["test_type"] == "at_max" for tc in test_cases)
        
        # 验证包含低于最大值
        assert any(abs(tc["param_value"] - 999.9) < 0.01 and tc["test_type"] == "below_max" for tc in test_cases)
        
        # 验证包含超过最大值
        assert any(abs(tc["param_value"] - 1000.1) < 0.01 and tc["test_type"] == "above_max" for tc in test_cases)
        
        # 验证包含正无穷大
        assert any(math.isinf(tc["param_value"]) and tc["test_type"] == "infinity" for tc in test_cases)
        
        # 验证包含系统最大值
        assert any(tc["param_value"] == sys.float_info.max and tc["test_type"] == "system_max" for tc in test_cases)
    
    def test_generate_max_value_test_cases_list(self, generator):
        """测试生成列表最大值测试用例"""
        def process_items(items: list) -> int:
            return len(items)
        
        test_cases = generator.generate_max_value_test_cases(
            function=process_items,
            param_name="items",
            param_type="list",
            max_value=10,
            element_type=str
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含最大长度列表
        at_max_cases = [tc for tc in test_cases if tc["test_type"] == "at_max"]
        assert len(at_max_cases) == 1
        assert len(at_max_cases[0]["param_value"]) == 10
        
        # 验证包含低于最大长度的列表
        below_max_cases = [tc for tc in test_cases if tc["test_type"] == "below_max"]
        assert len(below_max_cases) == 1
        assert len(below_max_cases[0]["param_value"]) == 9
        
        # 验证包含超过最大长度的列表
        above_max_cases = [tc for tc in test_cases if tc["test_type"] == "above_max"]
        assert len(above_max_cases) == 1
        assert len(above_max_cases[0]["param_value"]) == 11
        
        # 验证包含远超最大长度的列表
        far_above_cases = [tc for tc in test_cases if tc["test_type"] == "far_above_max"]
        assert len(far_above_cases) == 1
        assert len(far_above_cases[0]["param_value"]) == 20
    
    def test_generate_max_value_test_cases_dict(self, generator):
        """测试生成字典最大值测试用例"""
        def process_config(config: dict) -> int:
            return len(config)
        
        test_cases = generator.generate_max_value_test_cases(
            function=process_config,
            param_name="config",
            param_type="dict",
            max_value=5
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证包含最大键数字典
        at_max_cases = [tc for tc in test_cases if tc["test_type"] == "at_max"]
        assert len(at_max_cases) == 1
        assert len(at_max_cases[0]["param_value"]) == 5
        
        # 验证包含低于最大键数的字典
        below_max_cases = [tc for tc in test_cases if tc["test_type"] == "below_max"]
        assert len(below_max_cases) == 1
        assert len(below_max_cases[0]["param_value"]) == 4
        
        # 验证包含超过最大键数的字典
        above_max_cases = [tc for tc in test_cases if tc["test_type"] == "above_max"]
        assert len(above_max_cases) == 1
        assert len(above_max_cases[0]["param_value"]) == 6
        
        # 验证包含远超最大键数的字典
        far_above_cases = [tc for tc in test_cases if tc["test_type"] == "far_above_max"]
        assert len(far_above_cases) == 1
        assert len(far_above_cases[0]["param_value"]) == 10
    
    def test_generate_max_value_test_cases_unsupported_type(self, generator):
        """测试不支持的参数类型"""
        def sample_function(value):
            return value
        
        with pytest.raises(ValueError, match="Unsupported parameter type for max value generation"):
            generator.generate_max_value_test_cases(
                function=sample_function,
                param_name="value",
                param_type="unsupported_type"
            )
    
    def test_generate_max_value_test_cases_default_max(self, generator):
        """测试使用默认最大值"""
        def process_text(text: str) -> int:
            return len(text)
        
        # 不指定 max_value，应该使用默认值
        test_cases = generator.generate_max_value_test_cases(
            function=process_text,
            param_name="text",
            param_type="string"
        )
        
        # 验证使用了默认最大值
        at_max_cases = [tc for tc in test_cases if tc["test_type"] == "at_max"]
        assert len(at_max_cases) == 1
        assert len(at_max_cases[0]["param_value"]) == generator._max_string_length
    
    def test_generate_max_value_test_cases_categories(self, generator):
        """测试最大值测试用例的类别"""
        def validate_count(count: int) -> bool:
            return count <= 100
        
        test_cases = generator.generate_max_value_test_cases(
            function=validate_count,
            param_name="count",
            param_type="integer",
            max_value=100
        )
        
        # 验证类别正确性
        for tc in test_cases:
            if tc["test_type"] in ["at_max", "below_max"]:
                assert tc["category"] == "max"
            elif tc["test_type"] in ["above_max", "far_above_max", "system_max", "infinity"]:
                assert tc["category"] == "extreme"
    
    def test_generate_max_value_test_cases_expected_behaviors(self, generator):
        """测试最大值测试用例的预期行为"""
        def validate_score(score: float) -> bool:
            return 0.0 <= score <= 100.0
        
        test_cases = generator.generate_max_value_test_cases(
            function=validate_score,
            param_name="score",
            param_type="float",
            max_value=100.0
        )
        
        # 验证预期行为正确性
        for tc in test_cases:
            if tc["test_type"] in ["at_max", "below_max"]:
                assert tc["expected_behavior"] == "handle_gracefully"
            elif tc["test_type"] in ["above_max", "far_above_max", "system_max", "infinity"]:
                assert tc["expected_behavior"] == "raise_exception"
    
    def test_generate_max_value_test_cases_list_with_element_type(self, generator):
        """测试指定元素类型的列表最大值测试用例"""
        def process_numbers(numbers: list) -> float:
            return sum(numbers)
        
        # 测试整数类型
        int_test_cases = generator.generate_max_value_test_cases(
            function=process_numbers,
            param_name="numbers",
            param_type="list",
            max_value=5,
            element_type=int
        )
        
        at_max_case = [tc for tc in int_test_cases if tc["test_type"] == "at_max"][0]
        assert all(isinstance(x, int) for x in at_max_case["param_value"])
        
        # 测试浮点数类型
        float_test_cases = generator.generate_max_value_test_cases(
            function=process_numbers,
            param_name="numbers",
            param_type="list",
            max_value=5,
            element_type=float
        )
        
        at_max_case = [tc for tc in float_test_cases if tc["test_type"] == "at_max"][0]
        assert all(isinstance(x, float) for x in at_max_case["param_value"])
    
    def test_generate_max_value_test_cases_descriptions(self, generator):
        """测试最大值测试用例的描述"""
        def my_function(param: int) -> bool:
            return param <= 100
        
        test_cases = generator.generate_max_value_test_cases(
            function=my_function,
            param_name="param",
            param_type="integer",
            max_value=100
        )
        
        # 验证所有测试用例都有描述
        assert all(tc["description"] for tc in test_cases)
        
        # 验证描述包含函数名和参数名
        assert all("my_function" in tc["description"] for tc in test_cases)
        assert all("param" in tc["description"] for tc in test_cases)
        
        # 验证描述包含测试类型信息
        for tc in test_cases:
            if tc["test_type"] == "at_max":
                assert "max_value" in tc["description"] or "max_length" in tc["description"] or "max_keys" in tc["description"]
            elif tc["test_type"] == "below_max":
                assert "below_max" in tc["description"]
            elif tc["test_type"] == "above_max":
                assert "above_max" in tc["description"]

    def test_generate_concurrent_test_cases_basic(self, generator):
        """测试生成基本并发测试用例"""
        def increment_counter(counter_dict, key):
            counter_dict[key] = counter_dict.get(key, 0) + 1
        
        test_cases = generator.generate_concurrent_test_cases(
            function=increment_counter,
            num_threads=[2, 5],
            num_operations=[10, 100],
            operation_type="write"
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证基本并发测试用例
        basic_cases = [tc for tc in test_cases if tc["test_type"] == "basic_concurrent"]
        assert len(basic_cases) == 4  # 2 threads * 2 operations = 4 combinations
        
        # 验证测试用例结构
        for tc in basic_cases:
            assert "function" in tc
            assert "num_threads" in tc
            assert "num_operations" in tc
            assert "operation_type" in tc
            assert "description" in tc
            assert "expected_behavior" in tc
            assert "category" in tc
            assert "test_type" in tc
            
            assert tc["function"] == increment_counter
            assert tc["num_threads"] in [2, 5]
            assert tc["num_operations"] in [10, 100]
            assert tc["operation_type"] == "write"
            assert tc["category"] == "concurrent"
    
    def test_generate_concurrent_test_cases_default_params(self, generator):
        """测试使用默认参数生成并发测试用例"""
        def sample_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=sample_function
        )
        
        # 验证返回列表
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        # 验证使用了默认线程数和操作次数
        basic_cases = [tc for tc in test_cases if tc["test_type"] == "basic_concurrent"]
        assert len(basic_cases) == 15  # 5 threads * 3 operations = 15 combinations
        
        # 验证默认线程数
        thread_counts = set(tc["num_threads"] for tc in basic_cases)
        assert thread_counts == {2, 5, 10, 50, 100}
        
        # 验证默认操作次数
        operation_counts = set(tc["num_operations"] for tc in basic_cases)
        assert operation_counts == {1, 10, 100}
    
    def test_generate_concurrent_test_cases_race_condition(self, generator):
        """测试竞态条件测试用例"""
        def update_shared_resource(resource):
            resource["value"] += 1
        
        test_cases = generator.generate_concurrent_test_cases(
            function=update_shared_resource,
            operation_type="same_resource"
        )
        
        # 验证包含竞态条件测试
        race_cases = [tc for tc in test_cases if tc["test_type"] == "race_condition"]
        assert len(race_cases) == 3  # 2, 5, 10 threads
        
        # 验证竞态条件测试用例
        for tc in race_cases:
            assert tc["operation_type"] == "same_resource"
            assert tc["expected_behavior"] == "no_race_condition"
            assert tc["num_threads"] in [2, 5, 10]
            assert tc["num_operations"] == 100
            assert "race condition" in tc["description"]
    
    def test_generate_concurrent_test_cases_stress_test(self, generator):
        """测试高并发压力测试用例"""
        def process_request(request_data):
            return {"status": "ok"}
        
        test_cases = generator.generate_concurrent_test_cases(
            function=process_request,
            operation_type="mixed"
        )
        
        # 验证包含压力测试
        stress_cases = [tc for tc in test_cases if tc["test_type"] == "stress_test"]
        assert len(stress_cases) == 1
        
        # 验证压力测试用例
        stress_case = stress_cases[0]
        assert stress_case["num_threads"] == 100
        assert stress_case["num_operations"] == 1000
        assert stress_case["expected_behavior"] == "handle_gracefully"
        assert "stress test" in stress_case["description"]
    
    def test_generate_concurrent_test_cases_write_conflict(self, generator):
        """测试并发写入冲突测试用例"""
        def write_data(data_store, key, value):
            data_store[key] = value
        
        # 测试写操作类型
        write_test_cases = generator.generate_concurrent_test_cases(
            function=write_data,
            operation_type="write"
        )
        
        write_conflict_cases = [tc for tc in write_test_cases if tc["test_type"] == "write_conflict"]
        assert len(write_conflict_cases) == 1
        assert write_conflict_cases[0]["operation_type"] == "write"
        assert write_conflict_cases[0]["expected_behavior"] == "handle_write_conflicts"
        
        # 测试混合操作类型
        mixed_test_cases = generator.generate_concurrent_test_cases(
            function=write_data,
            operation_type="mixed"
        )
        
        write_conflict_cases = [tc for tc in mixed_test_cases if tc["test_type"] == "write_conflict"]
        assert len(write_conflict_cases) == 1
        
        # 测试只读操作类型（不应该有写冲突测试）
        read_test_cases = generator.generate_concurrent_test_cases(
            function=write_data,
            operation_type="read"
        )
        
        write_conflict_cases = [tc for tc in read_test_cases if tc["test_type"] == "write_conflict"]
        assert len(write_conflict_cases) == 0
    
    def test_generate_concurrent_test_cases_read_consistency(self, generator):
        """测试并发读取一致性测试用例"""
        def read_data(data_store, key):
            return data_store.get(key)
        
        # 测试读操作类型
        read_test_cases = generator.generate_concurrent_test_cases(
            function=read_data,
            operation_type="read"
        )
        
        read_consistency_cases = [tc for tc in read_test_cases if tc["test_type"] == "read_consistency"]
        assert len(read_consistency_cases) == 1
        assert read_consistency_cases[0]["operation_type"] == "read"
        assert read_consistency_cases[0]["expected_behavior"] == "consistent_reads"
        assert read_consistency_cases[0]["num_threads"] == 20
        assert read_consistency_cases[0]["num_operations"] == 100
        
        # 测试混合操作类型
        mixed_test_cases = generator.generate_concurrent_test_cases(
            function=read_data,
            operation_type="mixed"
        )
        
        read_consistency_cases = [tc for tc in mixed_test_cases if tc["test_type"] == "read_consistency"]
        assert len(read_consistency_cases) == 1
        
        # 测试只写操作类型（不应该有读一致性测试）
        write_test_cases = generator.generate_concurrent_test_cases(
            function=read_data,
            operation_type="write"
        )
        
        read_consistency_cases = [tc for tc in write_test_cases if tc["test_type"] == "read_consistency"]
        assert len(read_consistency_cases) == 0
    
    def test_generate_concurrent_test_cases_deadlock_detection(self, generator):
        """测试死锁检测测试用例"""
        def acquire_locks(lock1, lock2):
            with lock1:
                with lock2:
                    pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=acquire_locks,
            operation_type="mixed"
        )
        
        # 验证包含死锁检测测试
        deadlock_cases = [tc for tc in test_cases if tc["test_type"] == "deadlock_detection"]
        assert len(deadlock_cases) == 1
        
        # 验证死锁检测测试用例
        deadlock_case = deadlock_cases[0]
        assert deadlock_case["num_threads"] == 5
        assert deadlock_case["num_operations"] == 20
        assert deadlock_case["operation_type"] == "mixed"
        assert deadlock_case["expected_behavior"] == "no_deadlock"
        assert "deadlock" in deadlock_case["description"]
    
    def test_generate_concurrent_test_cases_baseline(self, generator):
        """测试单线程基线测试用例"""
        def process_item(item):
            return item * 2
        
        test_cases = generator.generate_concurrent_test_cases(
            function=process_item,
            operation_type="read"
        )
        
        # 验证包含基线测试
        baseline_cases = [tc for tc in test_cases if tc["test_type"] == "baseline"]
        assert len(baseline_cases) == 1
        
        # 验证基线测试用例
        baseline_case = baseline_cases[0]
        assert baseline_case["num_threads"] == 1
        assert baseline_case["num_operations"] == 100
        assert baseline_case["expected_behavior"] == "handle_gracefully"
        assert "single thread baseline" in baseline_case["description"]
    
    def test_generate_concurrent_test_cases_single_thread_count(self, generator):
        """测试指定单个线程数"""
        def sample_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            num_threads=10,
            num_operations=[1, 10]
        )
        
        # 验证基本并发测试只使用指定的线程数
        basic_cases = [tc for tc in test_cases if tc["test_type"] == "basic_concurrent"]
        assert all(tc["num_threads"] == 10 for tc in basic_cases)
        assert len(basic_cases) == 2  # 1 thread * 2 operations
    
    def test_generate_concurrent_test_cases_single_operation_count(self, generator):
        """测试指定单个操作次数"""
        def sample_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            num_threads=[2, 5],
            num_operations=50
        )
        
        # 验证基本并发测试只使用指定的操作次数
        basic_cases = [tc for tc in test_cases if tc["test_type"] == "basic_concurrent"]
        assert all(tc["num_operations"] == 50 for tc in basic_cases)
        assert len(basic_cases) == 2  # 2 threads * 1 operation
    
    def test_generate_concurrent_test_cases_all_test_types(self, generator):
        """测试生成所有类型的并发测试用例"""
        def sample_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            operation_type="mixed"
        )
        
        # 验证包含所有测试类型
        test_types = set(tc["test_type"] for tc in test_cases)
        expected_types = {
            "basic_concurrent",
            "race_condition",
            "stress_test",
            "write_conflict",
            "read_consistency",
            "deadlock_detection",
            "baseline"
        }
        assert expected_types.issubset(test_types)
    
    def test_generate_concurrent_test_cases_categories(self, generator):
        """测试并发测试用例的类别"""
        def sample_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            operation_type="mixed"
        )
        
        # 验证所有测试用例的类别都是 concurrent
        assert all(tc["category"] == "concurrent" for tc in test_cases)
    
    def test_generate_concurrent_test_cases_descriptions(self, generator):
        """测试并发测试用例的描述"""
        def my_concurrent_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=my_concurrent_function,
            operation_type="mixed"
        )
        
        # 验证所有测试用例都有描述
        assert all(tc["description"] for tc in test_cases)
        
        # 验证描述包含函数名
        assert all("my_concurrent_function" in tc["description"] for tc in test_cases)
        
        # 验证描述包含线程数和操作次数信息
        basic_cases = [tc for tc in test_cases if tc["test_type"] == "basic_concurrent"]
        for tc in basic_cases:
            assert str(tc["num_threads"]) in tc["description"]
            assert str(tc["num_operations"]) in tc["description"]
    
    def test_generate_concurrent_test_cases_expected_behaviors(self, generator):
        """测试并发测试用例的预期行为"""
        def sample_function():
            pass
        
        test_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            operation_type="mixed"
        )
        
        # 验证预期行为的有效性
        valid_behaviors = {
            "thread_safe",
            "no_race_condition",
            "handle_gracefully",
            "handle_write_conflicts",
            "consistent_reads",
            "no_deadlock"
        }
        
        for tc in test_cases:
            assert tc["expected_behavior"] in valid_behaviors
    
    def test_generate_concurrent_test_cases_operation_types(self, generator):
        """测试不同操作类型的并发测试用例"""
        def sample_function():
            pass
        
        # 测试读操作
        read_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            operation_type="read"
        )
        
        # 应该有读一致性测试，但没有写冲突测试
        assert any(tc["test_type"] == "read_consistency" for tc in read_cases)
        assert not any(tc["test_type"] == "write_conflict" for tc in read_cases)
        
        # 测试写操作
        write_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            operation_type="write"
        )
        
        # 应该有写冲突测试，但没有读一致性测试
        assert any(tc["test_type"] == "write_conflict" for tc in write_cases)
        assert not any(tc["test_type"] == "read_consistency" for tc in write_cases)
        
        # 测试混合操作
        mixed_cases = generator.generate_concurrent_test_cases(
            function=sample_function,
            operation_type="mixed"
        )
        
        # 应该同时有读一致性和写冲突测试
        assert any(tc["test_type"] == "read_consistency" for tc in mixed_cases)
        assert any(tc["test_type"] == "write_conflict" for tc in mixed_cases)
