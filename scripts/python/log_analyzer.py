#!/usr/bin/env python3
"""
智能日志分析工具

根据错误信息（状态码、错误码、请求ID等）自动检索和分析日志
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
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
        search_priorities = self._get_search_priorities()

        # 按优先级搜索
        for priority, term_key, term_name in search_priorities:
            if not terms[term_key]:
                continue

            # 搜索当前优先级的条件
            results = self._search_by_priority(terms[term_key], term_key, term_name, priority, max_results)

            # 如果找到了结果，不再搜索更低优先级的条件
            if results:
                print(f"✓ 通过 {term_name} 找到 {len(results)} 条记录，停止搜索")
                break

        # 按时间戳排序（同一优先级内）
        results.sort(key=lambda x: x["timestamp"])

        return results

    def _get_search_priorities(self) -> List[Tuple[int, str, str]]:
        """获取搜索优先级配置"""
        return [
            (1, "request_ids", "请求ID"),
            (2, "error_codes", "错误码"),
            (3, "status_codes", "状态码"),
            (4, "keywords", "关键词"),
        ]

    def _search_by_priority(
        self, term_values: List[str], term_key: str, term_name: str, priority: int, max_results: int
    ) -> List[Dict]:
        """按指定优先级搜索日志"""
        results = []

        for log_file in self.log_files:
            if not log_file.exists():
                continue

            try:
                results.extend(
                    self._search_in_file(log_file, term_values, term_name, priority, max_results - len(results))
                )

                if len(results) >= max_results:
                    break

            except Exception as e:
                print(f"读取日志文件 {log_file} 失败: {e}")

        return results

    def _search_in_file(
        self, log_file, term_values: List[str], term_name: str, priority: int, remaining_results: int
    ) -> List[Dict]:
        """在单个日志文件中搜索"""
        results = []

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            match_value = self._find_match_in_line(line, term_values)

            if match_value:
                result = self._create_log_result(log_file, i, line, lines, term_name, match_value, priority)
                results.append(result)

                if len(results) >= remaining_results:
                    break

        return results

    def _find_match_in_line(self, line: str, term_values: List[str]) -> Optional[str]:
        """在日志行中查找匹配的搜索词"""
        for term_value in term_values:
            if term_value in line:
                return term_value
        return None

    def _create_log_result(
        self,
        log_file,
        line_index: int,
        line: str,
        all_lines: List[str],
        term_name: str,
        match_value: str,
        priority: int,
    ) -> Dict:
        """创建日志搜索结果对象"""
        timestamp = self._extract_timestamp(line)
        level = self._extract_log_level(line)
        context = self._get_context_lines(all_lines, line_index)

        return {
            "file": log_file.name,
            "line_number": line_index + 1,
            "timestamp": timestamp,
            "level": level,
            "content": line.strip(),
            "match_info": [f"{term_name}: {match_value}"],
            "context": [ctx_line.strip() for ctx_line in context],
            "priority": priority,
        }

    def _extract_timestamp(self, line: str) -> str:
        """从日志行中提取时间戳"""
        timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        return timestamp_match.group(1) if timestamp_match else "未知时间"

    def _extract_log_level(self, line: str) -> str:
        """从日志行中提取日志级别"""
        level_match = re.search(r"\s+-\s+(?:maimnp\s+-\s+)?(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+-\s+", line)
        return level_match.group(1) if level_match else "UNKNOWN"

    def _get_context_lines(self, all_lines: List[str], line_index: int, context_size: int = 2) -> List[str]:
        """获取日志行的上下文（前后各 context_size 行）"""
        context_start = max(0, line_index - context_size)
        context_end = min(len(all_lines), line_index + context_size + 1)
        return all_lines[context_start:context_end]

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
        self._print_statistics(analysis)

        # 详细记录
        if results:
            self._print_detailed_results(results, show_context)
        else:
            print("❌ 未找到匹配的日志记录")

        print()
        print("=" * 80)

    def _print_statistics(self, analysis: Dict):
        """打印统计信息"""
        print("📊 统计信息")
        print("-" * 80)
        print(f"找到记录数: {analysis['total_count']}")

        self._print_time_range(analysis["time_range"])
        self._print_level_distribution(analysis["by_level"])
        self._print_error_codes(analysis["error_codes"])
        self._print_status_codes(analysis["status_codes"])
        self._print_request_ids_count(analysis["request_ids"])

        print()

    def _print_time_range(self, time_range: Dict):
        """打印时间范围"""
        if time_range["earliest"]:
            print(f"时间范围: {time_range['earliest']} ~ {time_range['latest']}")

    def _print_level_distribution(self, by_level: Dict):
        """打印日志级别分布"""
        if by_level:
            print("日志级别: ", end="")
            level_strs = [f"{level}({count})" for level, count in sorted(by_level.items())]
            print(", ".join(level_strs))

    def _print_error_codes(self, error_codes: set):
        """打印错误码"""
        if error_codes:
            print(f"错误码: {', '.join(sorted(error_codes))}")

    def _print_status_codes(self, status_codes: set):
        """打印状态码"""
        if status_codes:
            print(f"状态码: {', '.join(sorted(status_codes))}")

    def _print_request_ids_count(self, request_ids: set):
        """打印请求ID数量"""
        if request_ids:
            print(f"请求ID数量: {len(request_ids)}")

    def _print_detailed_results(self, results: List[Dict], show_context: bool):
        """打印详细记录"""
        priority = results[0].get("priority", 0)
        search_type = self._get_search_type_name(priority)

        print(f"📝 详细记录 - {search_type}")
        print("-" * 80)

        for i, result in enumerate(results, 1):
            self._print_single_result(i, result, show_context)

    def _get_search_type_name(self, priority: int) -> str:
        """根据优先级获取搜索类型名称"""
        priority_names = {1: "🔴 请求ID匹配", 2: "🟠 错误码匹配", 3: "🟡 状态码匹配", 4: "🟢 关键词匹配"}
        return priority_names.get(priority, "搜索结果")

    def _print_single_result(self, index: int, result: Dict, show_context: bool):
        """打印单条日志结果"""
        color, reset = self._get_level_color(result["level"])

        print(f"\n[{index}] {result['file']}:{result['line_number']}")
        print(f"    时间: {result['timestamp']}")
        print(f"    级别: {color}{result['level']}{reset}")
        print(f"    匹配: {', '.join(result['match_info'])}")

        content_display = self._truncate_text(result["content"], 200)
        print(f"    内容: {content_display}")

        if show_context and len(result["context"]) > 1:
            self._print_context(result["context"], result["content"])

    def _get_level_color(self, level: str) -> Tuple[str, str]:
        """获取日志级别对应的颜色代码"""
        level_colors = {
            "DEBUG": "\033[36m",  # 青色
            "INFO": "\033[32m",  # 绿色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",  # 红色
            "CRITICAL": "\033[35m",  # 紫色
        }
        color = level_colors.get(level, "")
        reset = "\033[0m" if color else ""
        return color, reset

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断过长的文本"""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def _print_context(self, context: List[str], current_content: str):
        """打印上下文行"""
        print("    上下文:")
        for ctx_line in context:
            ctx_display = self._truncate_text(ctx_line, 150)
            if ctx_line == current_content:
                print(f"      → {ctx_display}")
            else:
                print(f"        {ctx_display}")


def _print_welcome_message():
    """打印欢迎信息和使用说明"""
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


def _read_multiline_input() -> str:
    """读取多行输入

    Returns:
        合并后的输入字符串
    """
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

            # 检查是否是退出命令（只在第一行检查）
            if len(lines) == 1 and line.lower() in ["q", "quit", "exit"]:
                return "QUIT"

            # 检查是否是清屏命令（只在第一行检查）
            if len(lines) == 1 and line.lower() in ["clear", "cls"]:
                return "CLEAR"

        except EOFError:
            # Ctrl+D 结束输入
            break

    return " ".join(lines).strip()


def _clear_screen():
    """清屏并重新显示欢迎信息"""
    import os

    os.system("clear" if os.name != "nt" else "cls")
    _print_welcome_message()


def _display_query(query: str):
    """显示接收到的查询内容

    Args:
        query: 查询字符串
    """
    print()
    print("📥 接收到的查询内容:")
    print("-" * 80)
    if len(query) > 200:
        print(f"{query[:200]}...")
        print(f"（共 {len(query)} 字符）")
    else:
        print(query)
    print("-" * 80)


def _display_search_terms(terms: dict):
    """显示提取的搜索条件

    Args:
        terms: 搜索条件字典

    Returns:
        是否有有效的搜索条件
    """
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

    has_terms = any(terms.values())
    if not has_terms:
        print("  ⚠️  未能提取到有效的搜索条件")

    return has_terms


def _process_query(analyzer: LogAnalyzer, query: str):
    """处理单个查询

    Args:
        analyzer: 日志分析器实例
        query: 查询字符串
    """
    # 显示查询内容
    _display_query(query)

    # 提取搜索词
    terms = analyzer.extract_search_terms(query)

    # 显示搜索条件
    if not _display_search_terms(terms):
        return

    # 搜索日志
    print()
    print("🔎 正在搜索日志...")
    results = analyzer.search_logs(terms)

    # 分析结果
    analysis = analyzer.analyze_results(results)

    # 输出结果
    analyzer.format_output(results, analysis, show_context=True)


def main():
    """主函数"""
    # 项目根目录
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"

    if not log_dir.exists():
        print(f"❌ 日志目录不存在: {log_dir}")
        sys.exit(1)

    analyzer = LogAnalyzer(log_dir)

    # 显示欢迎信息
    _print_welcome_message()

    while True:
        try:
            print("请输入查询内容（多行输入请以空行结束，输入q/quit/exit退出程序）:")

            # 读取多行输入
            query = _read_multiline_input()

            # 处理特殊命令
            if query == "QUIT":
                print("再见！")
                return

            if query == "CLEAR":
                _clear_screen()
                continue

            # 跳过空查询
            if not query:
                continue

            # 处理查询
            _process_query(analyzer, query)

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
