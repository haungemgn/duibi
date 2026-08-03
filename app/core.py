"""核心数据处理逻辑（纯函数，无界面依赖，方便测试与优化）。

对应原网页的全部功能：
- 集合运算：重复(Duplicate)、去重(Distinct)、差集(A有B没有)、交集、并集
- 文本格式化：加逗号、加引号逗号、去逗号、去逗号+引号
- JSON 整形
所有函数都接收纯文本，返回处理结果，互不耦合。
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Options:
    """处理选项，集中管理便于扩展。"""

    remove_newline: bool = False   # 结果去除回车（合并为一行）
    ignore_case: bool = False      # 集合运算忽略大小写
    trim_each: bool = False        # 对每行做首尾去空格


def split_lines(text: str, trim_each: bool = False) -> list[str]:
    """按行拆分，过滤空白行。trim_each 为 True 时对每行去首尾空格。"""
    lines = text.splitlines()
    result: list[str] = []
    for line in lines:
        if trim_each:
            line = line.strip()
        if line.strip():
            result.append(line)
    return result


def _key(value: str, ignore_case: bool) -> str:
    # casefold 比 lower 更适合做不区分大小写的 Unicode 文本比较。
    return value.casefold() if ignore_case else value


def distinct(lines: list[str], ignore_case: bool = False) -> list[str]:
    """去重，保持首次出现顺序。"""
    seen: set[str] = set()
    out: list[str] = []
    for item in lines:
        k = _key(item, ignore_case)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def duplicates(lines: list[str], ignore_case: bool = False) -> list[str]:
    """返回出现超过一次的元素（每个只列一次），保持顺序。"""
    seen: set[str] = set()
    dup_keys: set[str] = set()
    out: list[str] = []
    for item in lines:
        k = _key(item, ignore_case)
        if k in seen:
            if k not in dup_keys:
                dup_keys.add(k)
                out.append(item)
        else:
            seen.add(k)
    return out


def difference(a: list[str], b: list[str], ignore_case: bool = False) -> list[str]:
    """A 有 B 没有（A - B），去重并保持 A 的顺序。"""
    b_keys = {_key(x, ignore_case) for x in b}
    seen: set[str] = set()
    out: list[str] = []
    for item in a:
        k = _key(item, ignore_case)
        if k not in b_keys and k not in seen:
            seen.add(k)
            out.append(item)
    return out


def intersection(a: list[str], b: list[str], ignore_case: bool = False) -> list[str]:
    """交集（A ∩ B），去重并保持 A 的顺序。"""
    b_keys = {_key(x, ignore_case) for x in b}
    seen: set[str] = set()
    out: list[str] = []
    for item in a:
        k = _key(item, ignore_case)
        if k in b_keys and k not in seen:
            seen.add(k)
            out.append(item)
    return out


def union(a: list[str], b: list[str], ignore_case: bool = False) -> list[str]:
    """并集（A ∪ B），去重并保持先 A 后 B 的顺序。"""
    return distinct(a + b, ignore_case)


def add_comma(lines: list[str], with_quote: bool = False) -> list[str]:
    """加逗号，可选加单引号。每行末尾加逗号，最后一行不加。"""
    quote = "'" if with_quote else ""
    out = []
    n = len(lines)
    for i, item in enumerate(lines):
        end = "," if i < n - 1 else ""
        out.append(f"{quote}{item}{quote}{end}")
    return out


def remove_comma(lines: list[str]) -> list[str]:
    """去掉每行末尾的逗号。"""
    return [item.removesuffix(",") for item in lines]


def remove_comma_quote(lines: list[str], quote: str) -> list[str]:
    """去掉行首引号、行尾引号和逗号。quote 为 ' 或 " 。"""
    if quote not in {"'", '"'}:
        raise ValueError("quote 只能是单引号或双引号")

    out: list[str] = []
    for item in lines:
        item = item.removesuffix(",")
        if len(item) >= 2 and item.startswith(quote) and item.endswith(quote):
            item = item[1:-1]
        out.append(item)
    return out


def _reject_non_standard_json(value: str) -> None:
    """拒绝 Python json 默认接受、但 JSON 标准不允许的特殊数值。"""
    raise ValueError(f"不支持非标准 JSON 数值: {value}")


def to_json_pretty(text: str, indent: int = 2) -> tuple[bool, str]:
    """JSON 整形。返回 (是否成功, 结果或错误信息)。"""
    text = text.strip()
    if not text:
        return False, "输入为空"
    try:
        obj = json.loads(text, parse_constant=_reject_non_standard_json)
        return True, json.dumps(obj, indent=indent, ensure_ascii=False, allow_nan=False)
    except (json.JSONDecodeError, ValueError) as e:
        return False, f"JSON 解析错误: {e}"


def join_result(lines: list[str], remove_newline: bool = False) -> str:
    """把结果行拼接成文本。remove_newline 为 True 时合并为一行。"""
    if remove_newline:
        return "".join(lines)
    return "\n".join(lines)
