"""核心逻辑测试：运行 `python test_core.py` 验证功能正确。"""

from core import (
    add_comma,
    difference,
    distinct,
    duplicates,
    intersection,
    join_result,
    remove_comma,
    remove_comma_quote,
    split_lines,
    to_json_pretty,
    union,
)


def check(name, got, expected):
    status = "OK " if got == expected else "FAIL"
    if got != expected:
        print(f"[{status}] {name}\n   期望: {expected}\n   实际: {got}")
    else:
        print(f"[{status}] {name}")
    return got == expected


def run():
    ok = True
    a = ["1", "2", "2", "3", "3", "3"]
    b = ["3", "4", "5"]

    ok &= check("split_lines 过滤空行", split_lines("a\n\n b \nc\n"), ["a", " b ", "c"])
    ok &= check("split_lines trim", split_lines("a\n b \nc", trim_each=True), ["a", "b", "c"])
    ok &= check("distinct", distinct(a), ["1", "2", "3"])
    ok &= check("duplicates", duplicates(a), ["2", "3"])
    ok &= check("difference A-B", difference(a, b), ["1", "2"])
    ok &= check("intersection", intersection(a, b), ["3"])
    ok &= check("union", union(a, b), ["1", "2", "3", "4", "5"])
    ok &= check("ignore_case distinct", distinct(["A", "a", "B"], ignore_case=True), ["A", "B"])
    ok &= check("add_comma", add_comma(["a", "b", "c"]), ["a,", "b,", "c"])
    ok &= check("add_comma quote", add_comma(["a", "b"], with_quote=True), ["'a',", "'b'"])
    ok &= check("remove_comma", remove_comma(["a,", "b,", "c"]), ["a", "b", "c"])
    ok &= check("remove_comma_quote single", remove_comma_quote(["'a',", "'b'"], "'"), ["a", "b"])
    ok &= check("remove_comma_quote double", remove_comma_quote(['"a",', '"b"'], '"'), ["a", "b"])
    ok &= check("join_result", join_result(["a", "b"]), "a\nb")
    ok &= check("join_result remove_newline", join_result(["a", "b"], remove_newline=True), "ab")

    good, result = to_json_pretty('{"b":1,"a":[1,2]}')
    ok &= check("to_json_pretty ok", good, True)
    bad, _ = to_json_pretty("{not json}")
    ok &= check("to_json_pretty 错误", bad, False)

    print("\n全部通过" if ok else "\n存在失败")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
