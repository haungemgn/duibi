"""界面层回归测试；使用 Qt offscreen 平台，无需显示窗口。"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox

try:
    from .main import MainWindow, THEMES
except ImportError:
    from main import MainWindow, THEMES


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        settings = QSettings(str(Path(directory.name) / "settings.ini"), QSettings.IniFormat)
        self.window = MainWindow(settings=settings)

    def tearDown(self) -> None:
        self.window.deleteLater()
        self.app.processEvents()

    def test_add_comma_preserves_duplicates(self) -> None:
        self.window.panel_a.set_text("x\nx\ny")
        self.window.op_add_comma()
        self.assertEqual(self.window.panel_r.text(), "x,\nx,\ny")

    def test_distinct_preserves_non_breaking_spaces(self) -> None:
        self.window.panel_a.set_text("a b\na\u00a0b\na b")
        self.window.op_distinct()
        self.assertEqual(self.window.panel_r.text(), "a b\na\u00a0b")

    def test_json_preserves_unicode_whitespace_in_strings(self) -> None:
        self.window.panel_a.set_text('"a\u00a0b\u2028c"')
        self.window.op_json()
        self.assertEqual(self.window.json_view.document().toRawText(), '"a\u00a0b\u2028c"')

    def test_copy_selection_preserves_whitespace_and_paragraphs(self) -> None:
        value = '"😀a\u00a0b\u2028c"\n"end"'
        for edit in (self.window.panel_a.edit, self.window.json_view):
            with self.subTest(editor=edit):
                edit.setPlainText("skip\n" + value)
                cursor = edit.textCursor()
                cursor.setPosition(5)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                edit.setTextCursor(cursor)
                self.assertEqual(edit.createMimeDataFromSelection().text(), value)

    def test_counts_use_the_same_lines_as_set_operations(self) -> None:
        a, b = self.window.panel_a, self.window.panel_b
        a.set_text("one\x85two\n \nthree")
        b.set_text("two\vfour")
        self.window.op_intersection()
        self.assertEqual(self.window.panel_r.text(), "two")
        self.assertEqual(a.count_label.text(), "3 行")
        self.assertEqual(b.count_label.text(), "2 行")
        self.assertIn("A: 3  B: 2  R: 1", self.window.status.currentMessage())
        b.set_text("changed")
        self.window.op_distinct()
        self.assertIn("A: 3  B: 1  R: 3", self.window.status.currentMessage())

    def test_json_rejects_non_standard_number(self) -> None:
        self.window.panel_a.set_text("NaN")
        self.window.op_json()
        self.assertIn("非标准 JSON", self.window.json_view.toPlainText())

    def test_json_highlights_whole_tokens(self) -> None:
        source = r'{"😀 42": "true \"x\" 123", "n": -1.5e+2, "ok": false}'
        self.window.json_view.setPlainText(source)
        self.window.json_highlighter.rehighlight()
        self.app.processEvents()

        formats = self.window.json_view.document().firstBlock().layout().formats()
        # Qt 的格式区间以 UTF-16 码元为单位。
        encoded = source.encode("utf-16-le")
        spans = [
            (encoded[2 * item.start:2 * (item.start + item.length)].decode("utf-16-le"),
             item.format.foreground().color().name())
            for item in formats
        ]
        theme = THEMES[self.window.current_theme_key]
        self.assertEqual(spans, [
            ('"😀 42"', theme["json_key"]),
            (r'"true \"x\" 123"', theme["json_string"]),
            ('"n"', theme["json_key"]),
            ('-1.5e+2', theme["json_number"]),
            ('"ok"', theme["json_key"]),
            ('false', theme["json_literal"]),
        ])

    def test_clear_can_be_cancelled(self) -> None:
        self.window.panel_a.set_text("important")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            self.window.op_clear()
        self.assertEqual(self.window.panel_a.text(), "important")
        self.assertEqual(self.window.status.currentMessage(), "已取消清空")

    def test_status_uses_plain_labels(self) -> None:
        self.window.panel_a.set_text("a\nb")
        self.window.op_distinct()
        self.assertTrue(self.window.status.currentMessage().startswith("A: 2  B: 0  R: 2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
