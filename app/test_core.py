"""核心逻辑测试：运行 `python test_core.py` 验证功能正确。"""

import json
import sys
import unittest

try:
    from .core import (
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
except ImportError:
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


class CoreTests(unittest.TestCase):
    def test_split_lines(self):
        self.assertEqual(split_lines("a\n\n b \nc\n"), ["a", " b ", "c"])
        self.assertEqual(split_lines("a\n b \nc", trim_each=True), ["a", "b", "c"])
        self.assertEqual(split_lines("a\r\nb\rc"), ["a", "b", "c"])

    def test_set_operations(self):
        a = ["1", "2", "2", "3", "3", "3"]
        b = ["3", "4", "5"]
        self.assertEqual(distinct(a), ["1", "2", "3"])
        self.assertEqual(duplicates(a), ["2", "3"])
        self.assertEqual(difference(a, b), ["1", "2"])
        self.assertEqual(intersection(a, b), ["3"])
        self.assertEqual(union(a, b), ["1", "2", "3", "4", "5"])

    def test_ignore_case_preserves_first_spelling_and_order(self):
        a = ["Z", "Straße", "X", "z", "STRASSE", "y", "Y", "x"]
        b = ["strasse", "x", "W", "w"]
        self.assertEqual(distinct(a, ignore_case=True), ["Z", "Straße", "X", "y"])
        self.assertEqual(difference(a, b, ignore_case=True), ["Z", "y"])
        self.assertEqual(intersection(a, b, ignore_case=True), ["Straße", "X"])
        self.assertEqual(union(a, b, ignore_case=True), ["Z", "Straße", "X", "y", "W"])

    def test_comma_formatting(self):
        self.assertEqual(add_comma(["a", "b", "c"]), ["a,", "b,", "c"])
        self.assertEqual(add_comma(["a", "b"], with_quote=True), ["'a',", "'b'"])
        self.assertEqual(add_comma(["a", "a"]), ["a,", "a"])
        self.assertEqual(remove_comma(["a,", "b,", "c"]), ["a", "b", "c"])
        self.assertEqual(remove_comma_quote(["'a',", "'b'"], "'"), ["a", "b"])
        self.assertEqual(remove_comma_quote(['"a",', '"b"'], '"'), ["a", "b"])
        self.assertEqual(remove_comma_quote(["'a,"], "'"), ["'a"])
        with self.assertRaises(ValueError):
            remove_comma_quote(["a"], "invalid")

    def test_join_result(self):
        self.assertEqual(join_result(["a", "b"]), "a\nb")
        self.assertEqual(join_result(["a", "b"], remove_newline=True), "ab")

    def test_json_validation(self):
        self.assertTrue(to_json_pretty('{"b":1,"a":[1,2]}')[0])
        for source in ("{not json}", "NaN", "Infinity", "-Infinity"):
            with self.subTest(source=source):
                self.assertFalse(to_json_pretty(source)[0])

    def test_json_keeps_duplicate_keys_and_original_number_spelling(self):
        source = '{"a":0.1234567890123456789,"a":1e400,"b":-0}'
        expected = '{\n  "a": 0.1234567890123456789,\n  "a": 1e400,\n  "b": -0\n}'
        self.assertEqual(to_json_pretty(source), (True, expected))

    def test_json_keeps_string_contents_and_escape_sequences(self):
        token = r'"中文 : { [ , ] } \" \\ \/ \t \ud800"'
        self.assertEqual(to_json_pretty(f"[{token}]"), (True, f"[\n  {token}\n]"))

    def test_json_checks_only_standard_whitespace(self):
        self.assertFalse(to_json_pretty("\u00a0true")[0])
        self.assertEqual(to_json_pretty("  \r\n\t"), (False, "输入为空"))

    def test_json_reports_excessive_nesting(self):
        depth = max(10_000, sys.getrecursionlimit() + 1)
        ok, message = to_json_pretty("[" * depth + "]" * depth)
        self.assertFalse(ok)
        self.assertIn("嵌套", message)

    def test_json_indent_and_empty_containers(self):
        value = {"a": [None, {}, []], "b": True}
        for indent in (2, 0, -1, "\t", None):
            with self.subTest(indent=indent):
                self.assertEqual(to_json_pretty(json.dumps(value), indent),
                                 (True, json.dumps(value, indent=indent)))


if __name__ == "__main__":
    unittest.main()
