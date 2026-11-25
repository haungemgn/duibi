"""核心数据处理逻辑（纯函数，无界面依赖，方便测试与优化）。

对应原网页的全部功能：
- 集合运算：重复(Duplicate)、去重(Distinct)、差集(A有B没有)、交集、并集
- 文本格式化：加逗号、加引号逗号、去逗号、去逗号+引号
- JSON 整形
所有函数都接收纯文本，返回处理结果，互不耦合。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import chain


@dataclass(frozen=True, slots=True)
class Options:
    """处理选项，集中管理便于扩展。"""

    remove_newline: bool = False   # 结果去除回车（合并为一行）
    ignore_case: bool = False      # 集合运算忽略大小写
    trim_each: bool = False        # 对每行做首尾去空格


def split_lines(text: str, trim_each: bool = False) -> list[str]:
    """按行拆分，过滤空白行。trim_each 为 True 时对每行去首尾空格。"""
    if trim_each:
        return [line for line in map(str.strip, text.splitlines()) if line]
    return [line for line in text.splitlines() if line and not line.isspace()]


def _key(value: str, ignore_case: bool) -> str:
    # casefold 比 lower 更适合做不区分大小写的 Unicode 文本比较。
    return value.casefold() if ignore_case else value


def distinct(lines: Iterable[str], ignore_case: bool = False) -> list[str]:
    """去重，保持首次出现顺序。"""
    if not ignore_case:
        return list(dict.fromkeys(lines))
    seen: set[str] = set()
    out: list[str] = []
    for item in lines:
        k = item.casefold()
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
    excluded = {_key(x, ignore_case) for x in b}
    out: list[str] = []
    for item in a:
        k = _key(item, ignore_case)
        if k not in excluded:
            excluded.add(k)
            out.append(item)
    return out


def intersection(a: list[str], b: list[str], ignore_case: bool = False) -> list[str]:
    """交集（A ∩ B），去重并保持 A 的顺序。"""
    remaining = {_key(x, ignore_case) for x in b}
    out: list[str] = []
    for item in a:
        k = _key(item, ignore_case)
        if k in remaining:
            remaining.remove(k)
            out.append(item)
            if not remaining:
                break
    return out


def union(a: list[str], b: list[str], ignore_case: bool = False) -> list[str]:
    """并集（A ∪ B），去重并保持先 A 后 B 的顺序。"""
    return distinct(chain(a, b), ignore_case)


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


_JSON_TOKENS = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"|[{}\[\],:]|[^{}\[\],: \t\r\n]+')


def to_json_pretty(text: str, indent: int | str | None = 2) -> tuple[bool, str]:
    """JSON 整形。返回 (是否成功, 结果或错误信息)。"""
    if not text.strip(" \r\n\t"):
        return False, "输入为空"
    try:
        # 标准库负责语法校验。保留数字原文可避免无意义的大整数和浮点转换。
        json.loads(text, parse_int=str, parse_float=str, parse_constant=_reject_non_standard_json)
    except ValueError as e:
        return False, f"JSON 解析错误: {e}"
    except RecursionError:
        return False, "JSON 嵌套过深，无法整形"

    # 直接排版已校验的原文，避免字典覆盖重名字段或重新编码改写数字与转义。
    unit = indent if isinstance(indent, str) else " " * (indent or 0)
    parts: list[str] = []
    previous = ""
    depth = 0
    for match in _JSON_TOKENS.finditer(text):
        token = match.group()
        if token in ("}", "]"):
            depth -= 1
            if indent is not None and previous not in ("{", "["):
                parts.append("\n" + unit * depth)
        elif indent is not None and previous in ("{", "[", ","):
            parts.append("\n" + unit * depth)
        elif previous == ",":
            parts.append(" ")

        parts.append(": " if token == ":" else token)
        if token in ("{", "["):
            depth += 1
        previous = token
    return True, "".join(parts)


def join_result(lines: list[str], remove_newline: bool = False) -> str:
    """把结果行拼接成文本。remove_newline 为 True 时合并为一行。"""
    if remove_newline:
        return "".join(lines)
    return "\n".join(lines)
