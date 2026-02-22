#!/usr/bin/env python3
"""
测试模板生成器
自动为未覆盖的代码生成测试模板

使用方法:
    1. 先生成覆盖率报告:
       pytest --cov=app --cov-report=json --cov-report=term-missing
    
    2. 运行此脚本:
       python scripts/python/generate_test_templates.py
    
    3. 手动完善生成的测试模板

注意:
    - 生成的测试只是模板，需要添加具体的测试逻辑
    - 不会覆盖已存在的测试文件
    - 只为覆盖率低于 50% 的文件生成模板
"""

import os
import ast
import json
from typing import List, Dict


def analyze_coverage(coverage_file: str = "coverage.json") -> Dict:
    """分析覆盖率文件，找出未覆盖的代码"""
    if not os.path.exists(coverage_file):
        print(f"❌ 错误: 找不到覆盖率文件 '{coverage_file}'")
        print("\n请先运行以下命令生成覆盖率报告:")
        print("  pytest --cov=app --cov-report=json --cov-report=term-missing")
        return {}

    try:
        with open(coverage_file, "r") as f:
            coverage_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: 无法解析覆盖率文件: {e}")
        return {}

    uncovered = {}
    for file_path, file_data in coverage_data.get("files", {}).items():
        if file_path.startswith("app/"):
            missing_lines = file_data.get("missing_lines", [])
            percent = file_data.get("summary", {}).get("percent_covered", 100)
            if percent < 100 and missing_lines:
                uncovered[file_path] = {
                    "percent": percent,
                    "missing_lines": missing_lines,
                    "total_statements": file_data.get("summary", {}).get("num_statements", 0),
                }

    return uncovered


def extract_functions_from_file(file_path: str) -> List[Dict]:
    """从Python文件中提取函数定义"""
    try:
        with open(file_path, "r") as f:
            tree = ast.parse(f.read())

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args": [arg.arg for arg in node.args.args],
                    }
                )

        return functions
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def generate_test_template(module_path: str, functions: List[Dict]) -> str:
    """生成测试模板"""
    module_name = module_path.replace("app/", "").replace("/", "_").replace(".py", "")
    test_class_name = "".join(word.capitalize() for word in module_name.split("_"))

    template = f'''"""
{module_path} 的测试
自动生成的测试模板
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class Test{test_class_name}:
    """测试 {module_path}"""
    
'''

    for func in functions:
        func_name = func["name"]
        if func_name.startswith("_"):
            continue  # 跳过私有函数

        test_name = f"test_{func_name}"
        async_marker = "@pytest.mark.asyncio\n    " if func["is_async"] else ""
        async_def = "async " if func["is_async"] else ""

        template += f'''    {async_marker}{async_def}def {test_name}(self, test_db):
        """测试 {func_name}"""
        # TODO: 实现测试逻辑
        pass
    
'''

    return template


def main():
    """主函数"""
    print("=" * 60)
    print("测试模板生成器")
    print("=" * 60)
    print()

    print("📊 分析覆盖率数据...")
    uncovered = analyze_coverage()

    if not uncovered:
        print("\n✨ 太棒了！所有文件的覆盖率都是 100%，或者没有找到覆盖率数据。")
        return

    print(f"\n发现 {len(uncovered)} 个文件需要提升覆盖率:\n")

    # 按覆盖率排序
    sorted_files = sorted(uncovered.items(), key=lambda x: x[1]["percent"])

    # 显示前10个覆盖率最低的文件
    for file_path, data in sorted_files[:10]:
        print(f"  📄 {file_path}: {data['percent']:.1f}% " f"({len(data['missing_lines'])} 行未覆盖)")

    if len(sorted_files) > 10:
        print(f"\n  ... 还有 {len(sorted_files) - 10} 个文件未显示")

    print("\n" + "=" * 60)
    print("🔨 生成测试模板...")
    print("=" * 60)
    print()

    generated_count = 0
    skipped_count = 0

    # 为覆盖率最低的文件生成模板
    for file_path, data in sorted_files[:5]:
        if data["percent"] < 50:  # 只为覆盖率低于50%的生成
            functions = extract_functions_from_file(file_path)
            if functions:
                template = generate_test_template(file_path, functions)

                # 生成测试文件名
                test_file_name = file_path.replace("app/", "tests/test_").replace("/", "_")
                test_file_path = f"{test_file_name}_generated.py"

                # 检查文件是否已存在
                if not os.path.exists(test_file_path):
                    with open(test_file_path, "w") as f:
                        f.write(template)
                    print(f"  ✓ 生成: {test_file_path}")
                    generated_count += 1
                else:
                    print(f"  ⊗ 跳过: {test_file_path} (已存在)")
                    skipped_count += 1

    print()
    print("=" * 60)
    print("完成！")
    print("=" * 60)
    print()

    if generated_count > 0:
        print(f"✨ 成功生成 {generated_count} 个测试模板")
        print()
        print("📝 下一步:")
        print("  1. 查看生成的测试文件: tests/test_*_generated.py")
        print("  2. 添加具体的测试逻辑和断言")
        print("  3. 运行测试: pytest tests/test_*_generated.py")
        print("  4. 重新生成覆盖率报告查看改进")
    elif skipped_count > 0:
        print(f"⊗ 跳过了 {skipped_count} 个已存在的测试文件")
        print("  如需重新生成，请先删除对应的 *_generated.py 文件")
    else:
        print("ℹ️  没有生成新的测试模板")
        print("  原因: 所有文件的覆盖率都高于 50%")
        print("  提示: 可以手动为覆盖率较低的文件编写测试")
    print()


if __name__ == "__main__":
    main()
