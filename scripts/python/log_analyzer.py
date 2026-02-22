#!/usr/bin/env python3
"""
智能日志分析工具

根据错误信息（状态码、错误码、请求ID等）自动检索和分析日志
"""

import re
import sys
from pathlib import Path
from typing import List, Dict
from collections import defaultdict


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_files = [log_dir / "maimnp.log", log_dir / "maimnp_error.log"]

    def extract_search_terms(self, query: str) -> Dict[str, List[str]]:
        """从查询文本中提取搜索关键词"""
        terms = {"status_codes": [], "error_codes": [], "request_ids": [], "keywords": []}

        # 提取状态码（3位数字）
        # 支持多种格式: "状态码 422", "422 状态码", "HTTP 422", "422 Bad Request"
        status_pattern = r"(?:状态码|HTTP)[：:\s]*(\d{3})|(\d{3})\s*(?:状态码|Bad Request|OK|Unauthorized|Forbidden|Not Found|Internal Server Error)"
        for match in re.finditer(status_pattern, query):
            code = match.group(1) or match.group(2)
            if code and code not in terms["status_codes"]:
                terms["status_codes"].append(code)

        # 提取错误码（5位数字）
        # 支持多种格式: "错误码 40022", "40022 错误码", "Code=40022"
        error_pattern = r"(?:错误码|Code=)[：:\s]*(\d{5})|(\d{5})\s*错误码"
        for match in re.finditer(error_pattern, query):
            code = match.group(1) or match.group(2)
            if code and code not in terms["error_codes"]:
                terms["error_codes"].append(code)

        # 提取请求ID（UUID格式）
        # 支持多种格式: "请求ID xxx", "ID=xxx", "request_id: xxx"
        request_id_pattern = r"(?:请求ID|ID=|request_id[：:\s]*)[：:\s]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})|([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
        for match in re.finditer(request_id_pattern, query, re.IGNORECASE):
            req_id = match.group(1) or match.group(2)
            if req_id and req_id not in terms["request_ids"]:
                terms["request_ids"].append(req_id)

        # 提取其他关键词（中文词组，至少2个字）
        keyword_pattern = r"[\u4e00-\u9fa5]{2,}"
        keywords = re.findall(keyword_pattern, query)
        # 过滤掉"状态码"、"错误码"、"请求ID"等元信息
        filter_words = {"状态码", "错误码", "请求", "请求ID", "日志", "错误", "失败", "成功"}
        for kw in keywords:
            if kw not in filter_words and kw not in terms["keywords"]:
                terms["keywords"].append(kw)

        # 限制关键词数量，避免过多
        terms["keywords"] = terms["keywords"][:5]

        return terms

    def search_logs(self, terms: Dict[str, List[str]], max_results: int = 50) -> List[Dict]:
        """搜索日志文件（按优先级搜索，找到高优先级结果后停止）"""
        results = []

        # 定义搜索优先级和对应的搜索条件
        search_priorities = [
            (1, "request_ids", "请求ID"),
            (2, "error_codes", "错误码"),
            (3, "status_codes", "状态码"),
            (4, "keywords", "关键词"),
        ]

        # 按优先级搜索
        for priority, term_key, term_name in search_priorities:
            if not terms[term_key]:
                continue

            # 搜索当前优先级的条件
            for log_file in self.log_files:
                if not log_file.exists():
                    continue

                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        matched = False
                        match_value = None

                        # 检查当前优先级的条件
                        for term_value in terms[term_key]:
                            if term_value in line:
                                matched = True
                                match_value = term_value
                                break

                        if matched:
                            # 提取时间戳
                            timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                            timestamp = timestamp_match.group(1) if timestamp_match else "未知时间"

                            # 提取日志级别 - 支持多种格式
                            level_match = re.search(
                                r"\s+-\s+(?:maimnp\s+-\s+)?(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+-\s+", line
                            )
                            level = level_match.group(1) if level_match else "UNKNOWN"

                            # 获取上下文（前后各2行）
                            context_start = max(0, i - 2)
                            context_end = min(len(lines), i + 3)
                            context = lines[context_start:context_end]

                            results.append(
                                {
                                    "file": log_file.name,
                                    "line_number": i + 1,
                                    "timestamp": timestamp,
                                    "level": level,
                                    "content": line.strip(),
                                    "match_info": [f"{term_name}: {match_value}"],
                                    "context": [ctx_line.strip() for ctx_line in context],
                                    "priority": priority,
                                }
                            )

                            if len(results) >= max_results:
                                break

                except Exception as e:
                    print(f"读取日志文件 {log_file} 失败: {e}")

                if len(results) >= max_results:
                    break

            # 如果找到了结果，不再搜索更低优先级的条件
            if results:
                print(f"✓ 通过 {term_name} 找到 {len(results)} 条记录，停止搜索")
                break

        # 按时间戳排序（同一优先级内）
        results.sort(key=lambda x: x["timestamp"])

        return results

    def analyze_results(self, results: List[Dict]) -> Dict:
        """分析搜索结果"""
        analysis = {
            "total_count": len(results),
            "by_level": defaultdict(int),
            "by_file": defaultdict(int),
            "time_range": {"earliest": None, "latest": None},
            "error_codes": set(),
            "status_codes": set(),
            "request_ids": set(),
        }

        for result in results:
            # 统计日志级别
            analysis["by_level"][result["level"]] += 1

            # 统计文件
            analysis["by_file"][result["file"]] += 1

            # 时间范围
            if result["timestamp"] != "未知时间":
                if not analysis["time_range"]["earliest"]:
                    analysis["time_range"]["earliest"] = result["timestamp"]
                    analysis["time_range"]["latest"] = result["timestamp"]
                else:
                    if result["timestamp"] < analysis["time_range"]["earliest"]:
                        analysis["time_range"]["earliest"] = result["timestamp"]
                    if result["timestamp"] > analysis["time_range"]["latest"]:
                        analysis["time_range"]["latest"] = result["timestamp"]

            # 提取错误码
            error_codes = re.findall(r"Code=(\d{5})", result["content"])
            analysis["error_codes"].update(error_codes)

            # 提取状态码
            status_codes = re.findall(
                r"(\d{3})\s+(?:OK|Bad Request|Unauthorized|Forbidden|Not Found|Internal Server Error)",
                result["content"],
            )
            analysis["status_codes"].update(status_codes)

            # 提取请求ID
            request_ids = re.findall(
                r"ID=([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", result["content"]
            )
            analysis["request_ids"].update(request_ids)

        return analysis

    def format_output(self, results: List[Dict], analysis: Dict, show_context: bool = True):
        """格式化输出结果"""
        print()
        print("=" * 80)
        print("日志分析结果")
        print("=" * 80)
        print()

        # 统计信息
        print("📊 统计信息")
        print("-" * 80)
        print(f"找到记录数: {analysis['total_count']}")

        if analysis["time_range"]["earliest"]:
            print(f"时间范围: {analysis['time_range']['earliest']} ~ {analysis['time_range']['latest']}")

        if analysis["by_level"]:
            print("日志级别: ", end="")
            level_strs = [f"{level}({count})" for level, count in sorted(analysis["by_level"].items())]
            print(", ".join(level_strs))

        if analysis["error_codes"]:
            print(f"错误码: {', '.join(sorted(analysis['error_codes']))}")

        if analysis["status_codes"]:
            print(f"状态码: {', '.join(sorted(analysis['status_codes']))}")

        if analysis["request_ids"]:
            print(f"请求ID数量: {len(analysis['request_ids'])}")

        print()

        # 详细记录
        if results:
            # 确定搜索类型
            priority = results[0].get("priority", 0)
            priority_names = {1: "🔴 请求ID匹配", 2: "🟠 错误码匹配", 3: "🟡 状态码匹配", 4: "🟢 关键词匹配"}

            search_type = priority_names.get(priority, "搜索结果")

            print(f"📝 详细记录 - {search_type}")
            print("-" * 80)

            for i, result in enumerate(results, 1):
                # 日志级别颜色
                level_colors = {
                    "DEBUG": "\033[36m",  # 青色
                    "INFO": "\033[32m",  # 绿色
                    "WARNING": "\033[33m",  # 黄色
                    "ERROR": "\033[31m",  # 红色
                    "CRITICAL": "\033[35m",  # 紫色
                }
                color = level_colors.get(result["level"], "")
                reset = "\033[0m" if color else ""

                print(f"\n[{i}] {result['file']}:{result['line_number']}")
                print(f"    时间: {result['timestamp']}")
                print(f"    级别: {color}{result['level']}{reset}")
                print(f"    匹配: {', '.join(result['match_info'])}")
                print(f"    内容: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")

                if show_context and len(result["context"]) > 1:
                    print("    上下文:")
                    for ctx_line in result["context"]:
                        # 截断过长的行
                        ctx_display = ctx_line[:150] + "..." if len(ctx_line) > 150 else ctx_line
                        if ctx_line == result["content"]:
                            print(f"      → {ctx_display}")
                        else:
                            print(f"        {ctx_display}")
        else:
            print("❌ 未找到匹配的日志记录")

        print()
        print("=" * 80)


def main():
    """主函数"""
    # 项目根目录
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"

    if not log_dir.exists():
        print(f"❌ 日志目录不存在: {log_dir}")
        sys.exit(1)

    analyzer = LogAnalyzer(log_dir)

    print("=" * 80)
    print("智能日志分析工具")
    print("=" * 80)
    print()
    print("使用说明:")
    print("  输入包含错误信息的文本，工具会自动提取关键信息并搜索日志")
    print("  支持识别: 状态码、错误码、请求ID、关键词")
    print()
    print("多行输入:")
    print("  - 可以粘贴多行日志内容")
    print("  - 输入空行结束输入并开始搜索")
    print("  - 或者单行输入后直接回车")
    print()
    print("示例:")
    print("  该邮箱已被注册 状态码 422 错误码 40022 请求ID fc972dbc-770f-455c-98d3-ad0dad100395")
    print("  用户登录失败 错误码 40001")
    print("  500 Internal Server Error")
    print()
    print("命令:")
    print("  q/quit/exit - 退出程序")
    print("  clear/cls   - 清屏")
    print("=" * 80)
    print()

    while True:
        try:
            print("请输入查询内容（多行输入请以空行结束，输入q/quit/exit退出程序）:")

            # 读取多行输入
            lines = []
            first_line = True

            while True:
                try:
                    if first_line:
                        line = input("> ").strip()
                        first_line = False
                    else:
                        line = input("  ").strip()

                    # 如果是空行且已经有内容，结束输入
                    if not line and lines:
                        break

                    # 如果第一行就是空行，继续等待
                    if not line and not lines:
                        continue

                    lines.append(line)

                    # 检查是否是命令（只在第一行检查）
                    if len(lines) == 1:
                        if line.lower() in ["q", "quit", "exit"]:
                            print("再见！")
                            return

                        if line.lower() in ["clear", "cls"]:
                            import os

                            os.system("clear" if os.name != "nt" else "cls")
                            print("=" * 80)
                            print("智能日志分析工具")
                            print("=" * 80)
                            print()
                            lines = []
                            first_line = True
                            continue

                except EOFError:
                    # Ctrl+D 结束输入
                    break

            # 合并所有行
            query = " ".join(lines).strip()

            if not query:
                continue

            # 显示接收到的完整内容
            print()
            print("📥 接收到的查询内容:")
            print("-" * 80)
            if len(query) > 200:
                print(f"{query[:200]}...")
                print(f"（共 {len(query)} 字符）")
            else:
                print(query)
            print("-" * 80)

            # 提取搜索词
            terms = analyzer.extract_search_terms(query)

            # 显示提取的搜索词
            print()
            print("🔍 提取的搜索条件:")
            if terms["request_ids"]:
                print(f"  请求ID: {', '.join(terms['request_ids'])}")
            if terms["error_codes"]:
                print(f"  错误码: {', '.join(terms['error_codes'])}")
            if terms["status_codes"]:
                print(f"  状态码: {', '.join(terms['status_codes'])}")
            if terms["keywords"]:
                print(f"  关键词: {', '.join(terms['keywords'])}")

            if not any(terms.values()):
                print("  ⚠️  未能提取到有效的搜索条件")
                continue

            # 搜索日志
            print()
            print("🔎 正在搜索日志...")
            results = analyzer.search_logs(terms)

            # 分析结果
            analysis = analyzer.analyze_results(results)

            # 输出结果
            analyzer.format_output(results, analysis, show_context=True)

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
