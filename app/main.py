"""数据对比工具 - Windows 桌面版（PySide6 / Qt）。

基于原网页《优化数据对页面》重写为原生桌面软件：
- 性能更高：QPlainTextEdit 处理大文本，集合运算用 Python set
- 体验更好：分组工具栏、快捷键、行数统计、一键复制、JSON 高亮、深浅色自适应
- 自由优化：界面与核心逻辑(core.py)解耦
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QMimeData, QRegularExpression, QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QFont,
    QGuiApplication,
    QKeySequence,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from app.core import (
        Options,
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
except ImportError:  # 兼容从 app 目录直接运行 main.py
    from core import (
        Options,
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


THEMES: dict[str, dict[str, str]] = {
    "white": {
        "name": "白色",
        "bg": "#ffffff",
        "fg": "#1f2937",
        "input_bg": "#ffffff",
        "input_fg": "#111827",
        "border": "#d1d5db",
        "muted": "#6b7280",
        "btn_bg": "#f9fafb",
        "btn_hover": "#f3f4f6",
        "btn_pressed": "#e5e7eb",
        "primary_border": "#3b82f6",
        "primary_fg": "#1d4ed8",
        "primary_hover": "#e0ecff",
        "json_key": "#7c3aed",
        "json_string": "#15803d",
        "json_number": "#2563eb",
        "json_literal": "#b45309",
    },
    "gray": {
        "name": "灰色",
        "bg": "#e5e7eb",
        "fg": "#111827",
        "input_bg": "#f3f4f6",
        "input_fg": "#111827",
        "border": "#9ca3af",
        "muted": "#4b5563",
        "btn_bg": "#d1d5db",
        "btn_hover": "#cbd5e1",
        "btn_pressed": "#9ca3af",
        "primary_border": "#2563eb",
        "primary_fg": "#1e40af",
        "primary_hover": "#bfdbfe",
        "json_key": "#6d28d9",
        "json_string": "#166534",
        "json_number": "#1d4ed8",
        "json_literal": "#92400e",
    },
    "black": {
        "name": "黑色",
        "bg": "#1e1e1e",
        "fg": "#e5e7eb",
        "input_bg": "#2d2d2d",
        "input_fg": "#f3f4f6",
        "border": "#4b5563",
        "muted": "#9ca3af",
        "btn_bg": "#374151",
        "btn_hover": "#4b5563",
        "btn_pressed": "#6b7280",
        "primary_border": "#60a5fa",
        "primary_fg": "#93c5fd",
        "primary_hover": "#1e3a5f",
        "json_key": "#c586c0",
        "json_string": "#6a9955",
        "json_number": "#569cd6",
        "json_literal": "#dcdcaa",
    },
}


def install_exception_handler() -> None:
    """记录未处理异常，并在 windowed 打包模式下给用户可见提示。"""
    log_path: Path | None = None
    try:
        log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "data-compare-tool.log"
        logging.basicConfig(
            filename=log_path,
            level=logging.ERROR,
            encoding="utf-8",
            format="%(asctime)s %(levelname)s %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.ERROR)

    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical(
            "未处理异常",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        detail = f"\n错误日志：{log_path}" if log_path is not None else ""
        QMessageBox.critical(None, "程序发生错误", f"操作未能完成，请重试。{detail}")

    sys.excepthook = handle_exception


def build_stylesheet(theme: dict[str, str]) -> str:
    return f"""
QWidget {{
    font-size: 13px;
    background: {theme["bg"]};
    color: {theme["fg"]};
}}
QMainWindow {{
    background: {theme["bg"]};
}}
QStatusBar {{
    background: {theme["bg"]};
    color: {theme["fg"]};
    border-top: 1px solid {theme["border"]};
}}
QPushButton {{
    padding: 6px 10px;
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    background: {theme["btn_bg"]};
    color: {theme["fg"]};
}}
QPushButton:hover {{ background: {theme["btn_hover"]}; }}
QPushButton:pressed {{ background: {theme["btn_pressed"]}; }}
QPushButton[primary="true"] {{
    border: 1px solid {theme["primary_border"]};
    color: {theme["primary_fg"]};
    font-weight: 600;
}}
QPushButton[primary="true"]:hover {{ background: {theme["primary_hover"]}; }}
QPlainTextEdit {{
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    padding: 4px;
    background: {theme["input_bg"]};
    color: {theme["input_fg"]};
    selection-background-color: {theme["primary_border"]};
}}
QTabWidget::pane {{
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    background: {theme["bg"]};
}}
QTabBar::tab {{
    background: {theme["btn_bg"]};
    color: {theme["fg"]};
    border: 1px solid {theme["border"]};
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: {theme["input_bg"]};
    color: {theme["input_fg"]};
}}
QCheckBox, QRadioButton {{
    color: {theme["fg"]};
    spacing: 6px;
}}
QFrame {{
    background: {theme["bg"]};
    border: 1px solid {theme["border"]};
    border-radius: 8px;
}}
QSplitter::handle {{
    background: {theme["border"]};
}}
"""


class JsonHighlighter(QSyntaxHighlighter):
    """简单的 JSON 语法高亮，随主题切换颜色。"""

    token_pattern = QRegularExpression(
        r'(?<string>"(?:[^"\\]++|\\.)*")(?<colon>\s*:)?'
        r'|(?<number>-?\b[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b)'
        r'|\b(?:true|false|null)\b'
    )

    def __init__(self, document):
        super().__init__(document)
        self.set_theme(THEMES["white"])

    def set_theme(self, theme: dict[str, str]) -> None:
        def fmt(color: str, bold: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f

        self.string_format = fmt(theme["json_string"])
        self.key_format = fmt(theme["json_key"], True)
        self.number_format = fmt(theme["json_number"])
        self.literal_format = fmt(theme["json_literal"], True)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        matches = self.token_pattern.globalMatch(text)
        while matches.hasNext():
            match = matches.next()
            if match.hasCaptured("string"):
                char_format = self.key_format if match.hasCaptured("colon") else self.string_format
                length = match.capturedLength("string")
            else:
                char_format = self.number_format if match.hasCaptured("number") else self.literal_format
                length = match.capturedLength()
            self.setFormat(match.capturedStart(), length, char_format)


class DataTextEdit(QPlainTextEdit):
    def createMimeDataFromSelection(self) -> QMimeData:
        mime = super().createMimeDataFromSelection()
        selected = self.textCursor().selectedText()
        if "\u00a0" in selected or "\u2028" in selected:
            # Qt 会在首次读取时才生成剪贴板格式。先生成，再替换纯文本内容。
            mime.text()
            mime.setText(selected.replace("\u2029", "\n"))
        return mime


class TextPanel(QWidget):
    """带标题和行数统计的文本面板。"""

    def __init__(self, title: str, read_only: bool = False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight:600;")
        self.count_label = QLabel("0 行")
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.edit = DataTextEdit()
        self.edit.setReadOnly(read_only)
        self.edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.edit.setPlaceholderText("在此粘贴/输入数据，每行一个…")
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.edit.setFont(font)
        self._line_count = 0
        self._count_timer = QTimer(self)
        self._count_timer.setSingleShot(True)
        self._count_timer.setInterval(150)
        self._count_timer.timeout.connect(self.lines)
        self.edit.textChanged.connect(self._count_timer.start)
        layout.addWidget(self.edit)

    def apply_theme(self, theme: dict[str, str]) -> None:
        self.count_label.setStyleSheet(f"color:{theme['muted']};")

    def text(self) -> str:
        # toPlainText() 会把不换行空格改成普通空格。只还原 Qt 的段落分隔符。
        return self.edit.document().toRawText().replace("\u2029", "\n")

    def lines(self, trim_each: bool = False) -> list[str]:
        rows = split_lines(self.text(), trim_each)
        self._count_timer.stop()
        self._line_count = len(rows)
        self.count_label.setText(f"{self._line_count} 行")
        return rows

    def line_count(self) -> int:
        if self._count_timer.isActive():
            self.lines()
        return self._line_count

    def set_text(self, value: str) -> None:
        self.edit.setPlainText(value)


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.setWindowTitle("数据对比工具")
        self.resize(1100, 720)
        self.setMinimumSize(760, 520)
        self.settings = (
            settings if settings is not None else QSettings("DataCompareTool", "DataCompareTool")
        )
        self.current_theme_key = "white"
        self.section_labels: list[QLabel] = []

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ---- 选项行 ----
        self.cb_remove_newline = QCheckBox("结果去回车")
        self.cb_ignore_case = QCheckBox("忽略大小写")
        self.cb_trim = QCheckBox("去首尾空格")
        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("选项："))
        opt_row.addWidget(self.cb_remove_newline)
        opt_row.addWidget(self.cb_ignore_case)
        opt_row.addWidget(self.cb_trim)
        opt_row.addStretch()
        opt_row.addWidget(self._build_theme_selector())
        root.addLayout(opt_row)

        # ---- 工具栏按钮 ----
        self.toolbar_frame = self._build_buttons()
        root.addWidget(self.toolbar_frame)

        # ---- 文本区 ----
        self.panel_a = TextPanel("A 集合")
        self.panel_b = TextPanel("B 集合")
        self.panel_r = TextPanel("R 结果", read_only=False)

        self.top_split = QSplitter(Qt.Horizontal)
        self.top_split.addWidget(self.panel_a)
        self.top_split.addWidget(self.panel_b)
        self.top_split.setSizes([550, 550])

        # 结果区用 Tab：纯文本 + JSON 视图
        self.tabs = QTabWidget()
        self.tabs.addTab(self.panel_r, "R 结果")
        self.json_view = DataTextEdit()
        self.json_view.setReadOnly(True)
        jfont = QFont("Consolas", 10)
        jfont.setStyleHint(QFont.Monospace)
        self.json_view.setFont(jfont)
        self.json_highlighter = JsonHighlighter(self.json_view.document())
        self.tabs.addTab(self.json_view, "JSON 视图")

        self.main_split = QSplitter(Qt.Vertical)
        self.main_split.addWidget(self.top_split)
        self.main_split.addWidget(self.tabs)
        self.main_split.setSizes([400, 320])
        root.addWidget(self.main_split, 1)

        self.status = self.statusBar()

        self._setup_shortcuts()
        saved_theme = self.settings.value("theme", "white", str)
        if saved_theme not in THEMES:
            saved_theme = "white"
        self.theme_buttons[saved_theme].setChecked(True)
        self._restore_settings()
        self.status.showMessage("就绪 — 左侧 A，右侧 B，下方为结果")

    def _restore_settings(self) -> None:
        """恢复不包含业务数据的界面状态和用户选项。"""
        self.cb_remove_newline.setChecked(
            self.settings.value("options/remove_newline", False, type=bool)
        )
        self.cb_ignore_case.setChecked(
            self.settings.value("options/ignore_case", False, type=bool)
        )
        self.cb_trim.setChecked(self.settings.value("options/trim_each", False, type=bool))

        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        top_state = self.settings.value("splitter/top")
        if top_state is not None:
            self.top_split.restoreState(top_state)
        main_state = self.settings.value("splitter/main")
        if main_state is not None:
            self.main_split.restoreState(main_state)

    def closeEvent(self, event: QCloseEvent) -> None:
        """退出时保存界面布局和选项，不保存用户输入内容。"""
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("splitter/top", self.top_split.saveState())
        self.settings.setValue("splitter/main", self.main_split.saveState())
        self.settings.setValue("options/remove_newline", self.cb_remove_newline.isChecked())
        self.settings.setValue("options/ignore_case", self.cb_ignore_case.isChecked())
        self.settings.setValue("options/trim_each", self.cb_trim.isChecked())
        self.settings.sync()
        super().closeEvent(event)

    def _build_theme_selector(self) -> QWidget:
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(QLabel("背景："))

        self.theme_group = QButtonGroup(self)
        self.theme_buttons: dict[str, QRadioButton] = {}
        for key, theme in THEMES.items():
            btn = QRadioButton(theme["name"])
            btn.setCursor(Qt.PointingHandCursor)
            self.theme_group.addButton(btn)
            self.theme_buttons[key] = btn
            row.addWidget(btn)
            btn.toggled.connect(lambda checked, k=key: checked and self._apply_theme(k))

        return box

    def _apply_theme(self, theme_key: str) -> None:
        theme = THEMES[theme_key]
        self.current_theme_key = theme_key
        self.settings.setValue("theme", theme_key)

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(theme))

        for panel in (self.panel_a, self.panel_b, self.panel_r):
            panel.apply_theme(theme)
        for label in self.section_labels:
            label.setStyleSheet(f"color:{theme['muted']}; font-size:11px;")

        self.json_highlighter.set_theme(theme)

        self.status.showMessage(f"已切换为{theme['name']}背景")

    # ---------- 界面构建 ----------
    def _build_buttons(self) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        grid = QGridLayout(frame)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        # (文本, 回调, 行, 列, 提示)
        set_ops = [
            ("重复(A)", self.op_duplicate, "找出 A 中重复出现的元素"),
            ("去重(A)", self.op_distinct, "A 去重，保持顺序"),
            ("A∩!B 差集", self.op_difference, "A 有 B 没有"),
            ("A∩B 交集", self.op_intersection, "A 与 B 都有"),
            ("A∪B 并集", self.op_union, "A 与 B 合并去重"),
        ]
        fmt_ops = [
            ("AB 互换", self.op_swap, "交换 A、B 内容"),
            ("清空", self.op_clear, "清空所有文本"),
            ("加逗号", self.op_add_comma, "每行末尾加逗号"),
            ("加引号逗号", self.op_add_quote, "加单引号并加逗号"),
            ("去逗号", self.op_remove_comma, "去掉行尾逗号"),
            ("去逗号+单引号", lambda: self.op_remove_cq("'"), "去逗号和单引号"),
            ("去逗号+双引号", lambda: self.op_remove_cq('"'), "去逗号和双引号"),
            ("JSON 整形", self.op_json, "把 A 当作 JSON 美化"),
        ]

        lbl1 = QLabel("集合运算")
        self.section_labels.append(lbl1)
        grid.addWidget(lbl1, 0, 0)
        for i, (text, cb, tip) in enumerate(set_ops):
            btn = self._make_btn(text, cb, tip, primary=True)
            grid.addWidget(btn, 1, i)

        lbl2 = QLabel("格式化 / 工具")
        self.section_labels.append(lbl2)
        grid.addWidget(lbl2, 2, 0)
        tool_ops = fmt_ops + [
            ("复制结果", self.op_copy_result, "复制 R 结果到剪贴板"),
        ]
        columns = 5
        for i, (text, cb, tip) in enumerate(tool_ops):
            btn = self._make_btn(text, cb, tip)
            grid.addWidget(btn, 3 + i // columns, i % columns)

        for column in range(columns):
            grid.setColumnStretch(column, 1)

        return frame

    def _make_btn(self, text: str, callback, tip: str, primary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        if primary:
            btn.setProperty("primary", True)
        return btn

    def _setup_shortcuts(self) -> None:
        shortcuts = {
            "Ctrl+1": self.op_distinct,
            "Ctrl+2": self.op_difference,
            "Ctrl+3": self.op_intersection,
            "Ctrl+4": self.op_union,
            "Ctrl+R": self.op_swap,
            "Ctrl+L": self.op_clear,
            "Ctrl+J": self.op_json,
            "Ctrl+Shift+C": self.op_copy_result,
        }
        for key, cb in shortcuts.items():
            act = QAction(self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(cb)
            self.addAction(act)

    # ---------- 选项 ----------
    def _options(self) -> Options:
        return Options(
            remove_newline=self.cb_remove_newline.isChecked(),
            ignore_case=self.cb_ignore_case.isChecked(),
            trim_each=self.cb_trim.isChecked(),
        )

    def _lines_a(self) -> list[str]:
        return self.panel_a.lines(self.cb_trim.isChecked())

    def _lines_b(self) -> list[str]:
        return self.panel_b.lines(self.cb_trim.isChecked())

    def _show_result(self, lines: list[str], op_name: str) -> None:
        opts = self._options()
        self.panel_r.set_text(join_result(lines, opts.remove_newline))
        self.tabs.setCurrentIndex(0)
        a_n = self.panel_a.line_count()
        b_n = self.panel_b.line_count()
        self.status.showMessage(
            f"A: {a_n}  B: {b_n}  R: {len(lines)}   ({op_name})"
        )

    # ---------- 操作 ----------
    def op_distinct(self) -> None:
        self._show_result(distinct(self._lines_a(), self.cb_ignore_case.isChecked()), "A 去重")

    def op_duplicate(self) -> None:
        self._show_result(duplicates(self._lines_a(), self.cb_ignore_case.isChecked()), "A 中重复")

    def op_difference(self) -> None:
        self._show_result(
            difference(self._lines_a(), self._lines_b(), self.cb_ignore_case.isChecked()),
            "差集 A 有 B 没有",
        )

    def op_intersection(self) -> None:
        self._show_result(
            intersection(self._lines_a(), self._lines_b(), self.cb_ignore_case.isChecked()),
            "交集",
        )

    def op_union(self) -> None:
        self._show_result(
            union(self._lines_a(), self._lines_b(), self.cb_ignore_case.isChecked()),
            "并集",
        )

    def op_add_comma(self) -> None:
        self._show_result(add_comma(self._lines_a()), "加逗号")

    def op_add_quote(self) -> None:
        self._show_result(
            add_comma(self._lines_a(), with_quote=True),
            "加引号逗号",
        )

    def op_remove_comma(self) -> None:
        self._show_result(remove_comma(self._lines_a()), "去逗号")

    def op_remove_cq(self, quote: str) -> None:
        name = "去逗号+单引号" if quote == "'" else "去逗号+双引号"
        self._show_result(remove_comma_quote(self._lines_a(), quote), name)

    def op_swap(self) -> None:
        a, b = self.panel_a.text(), self.panel_b.text()
        self.panel_a.set_text(b)
        self.panel_b.set_text(a)
        self.status.showMessage("已互换 A、B")

    def op_clear(self) -> None:
        editors = (self.panel_a.edit, self.panel_b.edit, self.panel_r.edit, self.json_view)
        has_content = any(not editor.document().isEmpty() for editor in editors)
        if not has_content:
            self.status.showMessage("当前没有需要清空的内容")
            return

        answer = QMessageBox.question(
            self,
            "确认清空",
            "确定清空 A、B、R 和 JSON 中的全部内容吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            self.status.showMessage("已取消清空")
            return

        self.panel_a.set_text("")
        self.panel_b.set_text("")
        self.panel_r.set_text("")
        self.json_view.setPlainText("")
        self.status.showMessage("已清空")

    def op_json(self) -> None:
        ok, result = to_json_pretty(self.panel_a.text())
        self.json_view.setPlainText(result)
        self.tabs.setCurrentIndex(1)
        self.status.showMessage("JSON 整形成功" if ok else result)

    def op_copy_result(self) -> None:
        text = self.panel_r.text()
        if not text:
            self.status.showMessage("R 结果为空，没有可复制的内容")
            return
        QGuiApplication.clipboard().setText(text)
        self.status.showMessage(f"已复制 R 结果（{len(text)} 字符）到剪贴板")


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("数据对比工具")
    install_exception_handler()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
