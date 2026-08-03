"""界面层回归测试；使用 Qt offscreen 平台，无需显示窗口。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

try:
    from .main import MainWindow
except ImportError:
    from main import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        QStandardPaths.setTestModeEnabled(True)
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        QSettings("DataCompareTool", "DataCompareTool").clear()
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.deleteLater()
        self.app.processEvents()

    def test_add_comma_preserves_duplicates(self) -> None:
        self.window.panel_a.set_text("x\nx\ny")
        self.window.op_add_comma()
        self.assertEqual(self.window.panel_r.text(), "x,\nx,\ny")

    def test_json_rejects_non_standard_number(self) -> None:
        self.window.panel_a.set_text("NaN")
        self.window.op_json()
        self.assertIn("非标准 JSON", self.window.json_view.toPlainText())

    def test_json_key_highlight_overrides_string_highlight(self) -> None:
        self.window.json_view.setPlainText('{"key": "value"}')
        self.window.json_highlighter.rehighlight()
        self.app.processEvents()

        formats = self.window.json_view.document().firstBlock().layout().formats()
        key_format = next(item for item in formats if item.start == 1)
        expected = self.window.json_highlighter.rules[1][1].foreground().color()
        self.assertEqual(key_format.format.foreground().color(), expected)

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
