#!/usr/bin/env python3
"""
自动生成错误码文档脚本

从 app/error_messages.json 自动生成 docs/development/错误码文档.md
使用方法: python scripts/python/generate_error_codes_doc.py
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def load_error_messages(json_path: str) -> dict:
    """加载错误消息 JSON 文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def group_by_module(error_messages: dict) -> dict:
    """按模块分组错误码"""
    grouped = defaultdict(list)

    for error_code, error_info in error_messages.items():
        module = error_info.get("module", "unknown")
        key = error_info.get("key", "")
        message = error_info.get("messages", {}).get("zh-CN", "")

        grouped[module].append({"code": error_code, "key": key, "message": message})

    return grouped


def generate_markdown(grouped_errors: dict) -> str:
    """生成 Markdown 文档"""
    lines = [
        "# 错误码对照表",
        "",
        "> 本文档由脚本自动生成，基于 `app/error_messages.json`。",
        "> 如需修改错误文案或新增错误码，请修改 `app/error_messages.json`，然后运行脚本重新生成。",
        "> 生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
    ]

    # 按模块名称排序
    for module in sorted(grouped_errors.keys()):
        errors = grouped_errors[module]

        # 按错误码排序
        errors.sort(key=lambda x: int(x["code"]))

        lines.append(f"## 模块 {module}")
        lines.append("")
        lines.append("| 错误码 | Key | 中文提示 |")
        lines.append("|--------|-----|----------|")

        for error in errors:
            code = error["code"]
            key = error["key"]
            message = error["message"]

            # 转义管道符
            message = message.replace("|", "\\|")

            lines.append(f"| `{code}` | `{key}` | {message} |")

        lines.append("")

    # 添加使用说明
    lines.extend(
        [
            "---",
            "",
            "## 使用说明",
            "",
            "### 添加新错误码",
            "",
            "1. 编辑 `app/error_messages.json`，添加新的错误码条目：",
            "",
            "```json",
            "{",
            '  "20001": {',
            '    "key": "NEW_ERROR_KEY",',
            '    "module": "new_module",',
            '    "messages": {',
            '      "zh-CN": "错误提示信息"',
            "    }",
            "  }",
            "}",
            "```",
            "",
            "2. 运行脚本重新生成文档：",
            "",
            "```bash",
            "python scripts/generate_error_codes_doc.py",
            "```",
            "",
            "### 错误码规范",
            "",
            "- **10000-10999**: 认证和用户相关错误",
            "- **12000-12999**: 管理员相关错误",
            "- **13000-13999**: 知识库相关错误",
            "- **14000-14999**: 人设卡相关错误",
            "- **15000-15999**: 消息相关错误",
            "- **16000-16999**: 评论相关错误",
            "",
            "### JSON 文件结构",
            "",
            "```json",
            "{",
            '  "错误码": {',
            '    "key": "错误码标识符",',
            '    "module": "模块名称",',
            '    "messages": {',
            '      "zh-CN": "中文错误提示"',
            "    }",
            "  }",
            "}",
            "```",
            "",
            "---",
            "",
            f"**最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # scripts/python -> scripts -> project_root

    # 定义文件路径
    json_path = project_root / "app" / "error_messages.json"
    doc_path = project_root / "docs" / "development" / "错误码文档.md"

    # 检查输入文件是否存在
    if not json_path.exists():
        print(f"❌ 错误：找不到文件 {json_path}")
        return False

    try:
        # 加载错误消息
        print(f"📖 加载错误消息文件: {json_path}")
        error_messages = load_error_messages(str(json_path))
        print(f"✅ 成功加载 {len(error_messages)} 个错误码")

        # 按模块分组
        print("📊 按模块分组...")
        grouped_errors = group_by_module(error_messages)
        print(f"✅ 分组完成，共 {len(grouped_errors)} 个模块")

        # 生成 Markdown
        print("📝 生成 Markdown 文档...")
        markdown_content = generate_markdown(grouped_errors)

        # 写入文件
        print(f"💾 写入文件: {doc_path}")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"✅ 成功生成文档！")
        print(f"📄 文件位置: {doc_path}")

        # 统计信息
        print("\n📊 统计信息:")
        print(f"  - 总错误码数: {len(error_messages)}")
        print(f"  - 模块数: {len(grouped_errors)}")
        for module in sorted(grouped_errors.keys()):
            count = len(grouped_errors[module])
            print(f"    - {module}: {count} 个错误码")

        return True

    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
