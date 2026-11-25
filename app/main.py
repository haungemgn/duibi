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

from PySide6.QtCore import QMimeData, QRegularExpression, QSettings, QSize, QStandardPaths, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
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
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from app.styles import THEMES, application_icon, build_stylesheet, icon_for
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
    from styles import THEMES, application_icon, build_stylesheet, icon_for
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


def label(text: str, name: str) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(name)
    return widget


def divider(name: str) -> QFrame:
    line = QFrame()
    line.setObjectName(name)
    line.setFixedHeight(1)
    return line


class TextPanel(QFrame):
    """数据编辑区；结果面板与 JSON 共用一个栏头。"""

    def __init__(self, role: str, title: str, placeholder: str):
        super().__init__()
        self.setObjectName("editorCard" if role != "R" else "resultBody")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.count_label = label("0 行", "countLabel")

        if role != "R":
            header = QHBoxLayout()
            header.setContentsMargins(13, 10, 13, 10)
            header.setSpacing(9)
            badge = label(role, "panelBadge")
            badge.setProperty("role", role)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(26, 26)
            header.addWidget(badge)
            header.addWidget(label(title, "panelTitle"))
            header.addStretch()
            header.addWidget(self.count_label)
            layout.addLayout(header)
            layout.addWidget(divider("cardRule"))

        self.edit = DataTextEdit()
        self.edit.setAccessibleName(title)
        self.edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.edit.setPlaceholderText(placeholder)
        self.edit.document().setDocumentMargin(11)
        self._line_count = 0
        self._count_timer = QTimer(self)
        self._count_timer.setSingleShot(True)
        self._count_timer.setInterval(150)
        self._count_timer.timeout.connect(self.lines)
        self.edit.textChanged.connect(self._count_timer.start)
        layout.addWidget(self.edit)

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
        self.resize(1120, 740)
        self.setMinimumSize(760, 520)
        self.settings = (
            settings if settings is not None else QSettings("DataCompareTool", "DataCompareTool")
        )
        self.current_theme_key = "white"
        self.operation_buttons = {}
        self.active_button = None
        self.cb_ignore_case = QCheckBox("忽略大小写")
        self.cb_trim = QCheckBox("去首尾空格")
        self.cb_remove_newline = QCheckBox("合并为一行")
        self.cb_remove_newline.setToolTip("执行集合运算或文本格式化时，将输出合并为一行")

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        root.addWidget(workspace, 1)
        work = QVBoxLayout(workspace)
        work.setContentsMargins(18, 14, 18, 12)
        self.main_split = QSplitter(Qt.Vertical)
        self.main_split.addWidget(self._build_inputs())
        self.main_split.addWidget(self._build_results())
        self.main_split.setSizes([390, 290])
        work.addWidget(self.main_split)
        self.status = self.statusBar()
        self._setup_shortcuts()
        saved_theme = self.settings.value("theme", "white", str)
        self._apply_theme(saved_theme if saved_theme in THEMES else "white")
        self._restore_settings()
        self.panel_a.edit.setFocus()
        self.status.showMessage("就绪")

    def _build_inputs(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        heading.setSpacing(12)
        heading.addWidget(label("输入数据", "sectionTitle"))
        heading.addStretch()
        heading.addWidget(self.cb_ignore_case)
        heading.addWidget(self.cb_trim)
        self.swap_button = self._button("交换 A / B", self.op_swap, "交换两组输入（Ctrl+R）", "secondaryAction")
        heading.addWidget(self.swap_button)
        layout.addLayout(heading)
        self.panel_a = TextPanel("A", "主数据", "粘贴主数据，每行一项")
        self.panel_b = TextPanel("B", "对照数据", "粘贴用于对照的数据，每行一项")
        self.top_split = QSplitter(Qt.Horizontal)
        self.top_split.addWidget(self.panel_a)
        self.top_split.addWidget(self.panel_b)
        self.top_split.setSizes([500, 500])
        layout.addWidget(self.top_split, 1)
        layout.addLayout(self._format_actions())
        return group

    def _format_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(label("格式化 A", "formatLabel"))
        formats = [
            ("加逗号", self.op_add_comma),
            ("加引号逗号", self.op_add_quote),
            ("去逗号", self.op_remove_comma),
            ("去逗号+单引号", lambda: self.op_remove_cq("'")),
            ("去逗号+双引号", lambda: self.op_remove_cq('"')),
        ]
        for text, callback in formats:
            button = self._button(text, callback, f"对主数据 A 执行「{text}」", "formatAction")
            self.operation_buttons[text] = button
            row.addWidget(button)
        row.addStretch()
        return row

    def _build_results(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        heading.addWidget(label("处理结果", "sectionTitle"))
        heading.addStretch()
        heading.addWidget(self.cb_remove_newline)
        layout.addLayout(heading)

        card = QFrame()
        card.setObjectName("resultCard")
        layout.addWidget(card, 1)
        body = QVBoxLayout(card)
        body.setContentsMargins(1, 1, 1, 1)
        body.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(12, 6, 12, 6)
        header.setSpacing(12)
        self.tabs = QTabBar()
        self.tabs.setObjectName("resultTabs")
        self.tabs.setDrawBase(False)
        self.tabs.addTab("文本")
        self.tabs.addTab("JSON")
        self.tabs.setAccessibleName("结果视图")
        header.addWidget(self.tabs)
        self.panel_r = TextPanel("R", "文本结果", "运行操作后，结果会显示在这里")
        header.addWidget(self.panel_r.count_label)
        header.addStretch()
        self.copy_button = self._button("复制结果", self.op_copy_result, "复制当前结果（Ctrl+Shift+C）", "copyAction")
        header.addWidget(self.copy_button)
        body.addLayout(header)
        body.addWidget(divider("cardRule"))

        self.json_view = DataTextEdit()
        self.json_view.setAccessibleName("JSON 结果")
        self.json_view.setReadOnly(True)
        self.json_view.setPlaceholderText("在 A 中粘贴 JSON，点击左侧的「JSON 美化」")
        self.json_view.document().setDocumentMargin(11)
        self.json_highlighter = JsonHighlighter(self.json_view.document())
        self.results = QStackedWidget()
        self.results.addWidget(self.panel_r)
        self.results.addWidget(self.json_view)
        self.tabs.currentChanged.connect(self._result_tab_changed)
        body.addWidget(self.results, 1)
        return group

    def _result_tab_changed(self, index: int) -> None:
        self.results.setCurrentIndex(index)
        self.panel_r.count_label.setVisible(index == 0)
        self.cb_remove_newline.setEnabled(index == 0)

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
        for splitter, key, defaults in (
            (self.top_split, "splitter/top", [500, 500]),
            (self.main_split, "splitter/main", [390, 290]),
        ):
            state = self.settings.value(key)
            if state is not None:
                splitter.restoreState(state)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(12)
            if 0 in splitter.sizes():
                splitter.setSizes(defaults)

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

    @staticmethod
    def _button(text, callback, tip, name) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setToolTip(tip)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    def _rail_menu(self, text: str, name: str, icon: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(name)
        button.setText(text)
        button.setIcon(icon_for(icon, "#c5cce0"))
        button.setIconSize(QSize(18, 18))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setCursor(Qt.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setMenu(QMenu(button))
        return button

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(184)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(3)
        brand = QHBoxLayout()
        brand.setContentsMargins(4, 0, 0, 14)
        brand.setSpacing(10)
        mark = label("", "brandMark")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        logo = icon_for("brand", "#ffffff", 22)
        mark.setPixmap(logo.pixmap(QSize(22, 22), self.devicePixelRatioF()))
        brand.addWidget(mark)
        brand.addWidget(label("数据对比", "brandName"))
        brand.addStretch()
        layout.addLayout(brand)
        layout.addWidget(divider("railRule"))
        layout.addSpacing(7)
        layout.addWidget(label("集合运算", "railHeading"))
        actions = [
            ("去除重复", "A", "distinct", self.op_distinct, "A 去重", "对 A 去重，保留首次出现的行（Ctrl+1）"),
            ("查找重复", "A", "duplicates", self.op_duplicate, "A 中重复", "列出 A 中重复的行"),
            ("差集", "A − B", "difference", self.op_difference, "差集 A 有 B 没有", "A 有、B 没有的行（Ctrl+2）"),
            ("交集", "A ∩ B", "intersection", self.op_intersection, "交集", "A 和 B 共有的行（Ctrl+3）"),
            ("并集", "A ∪ B", "union", self.op_union, "并集", "合并 A 和 B 并去重（Ctrl+4）"),
        ]
        for text, operands, icon, callback, key, tip in actions:
            button = self._button(text, callback, tip, "railAction")
            button.setIcon(icon_for(icon, "#c5cce0"))
            button.setIconSize(QSize(18, 18))
            hint = label(operands, "railHint")
            hint.setAttribute(Qt.WA_TransparentForMouseEvents)
            caption = QHBoxLayout(button)
            caption.setContentsMargins(0, 0, 10, 0)
            caption.addStretch()
            caption.addWidget(hint)
            self.operation_buttons[key] = button
            layout.addWidget(button)

        layout.addSpacing(8)
        layout.addWidget(label("格式工具", "railHeading"))
        json_button = self._button("JSON 美化", self.op_json, "美化 A 中的 JSON（Ctrl+J）", "railAction")
        json_button.setIcon(icon_for("json", "#c5cce0"))
        json_button.setIconSize(QSize(18, 18))
        self.operation_buttons["JSON 美化"] = json_button
        layout.addWidget(json_button)
        layout.addStretch()
        layout.addWidget(divider("railRule"))
        layout.addSpacing(4)
        self.theme_button = self._rail_menu("切换主题", "themeMenu", "theme")
        self.theme_group = QActionGroup(self)
        self.theme_actions = {}
        for key, theme in THEMES.items():
            action = self.theme_button.menu().addAction(theme["name"])
            action.setCheckable(True)
            self.theme_group.addAction(action)
            self.theme_actions[key] = action
            action.triggered.connect(lambda checked=False, k=key: self._apply_theme(k))
        layout.addWidget(self.theme_button)
        clear = self._button("清空工作区", self.op_clear, "清空所有输入和结果（Ctrl+L）", "railAction")
        clear.setIcon(icon_for("clear", "#c5cce0"))
        clear.setIconSize(QSize(18, 18))
        layout.addWidget(clear)
        return sidebar

    def _mark_operation(self, name: str | None) -> None:
        button = self.operation_buttons.get(name)
        if button is self.active_button:
            return
        for widget, active in ((self.active_button, False), (button, True)):
            if widget is not None:
                widget.setProperty("active", active)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
        self.active_button = button

    def _apply_theme(self, theme_key: str) -> None:
        theme = THEMES[theme_key]
        self.current_theme_key = theme_key
        self.theme_actions[theme_key].setChecked(True)
        self.settings.setValue("theme", theme_key)
        self.setStyleSheet(build_stylesheet(theme))
        self.swap_button.setIcon(icon_for("swap", theme["secondary_fg"], 16))
        self.copy_button.setIcon(icon_for("copy", theme["on_accent"], 16))
        self.json_highlighter.set_theme(theme)
        self.status.showMessage(f"已切换为{theme['name']}主题")

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
        self._mark_operation(op_name)
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
        self.json_view.clear()
        self.tabs.setCurrentIndex(0)
        self._mark_operation(None)
        self.status.showMessage("已清空")

    def op_json(self) -> None:
        self._mark_operation("JSON 美化")
        ok, result = to_json_pretty(self.panel_a.text())
        self.json_view.setPlainText(result)
        self.tabs.setCurrentIndex(1)
        self.status.showMessage("JSON 整形成功" if ok else result)

    def op_copy_result(self) -> None:
        if self.tabs.currentIndex() == 1:
            text = self.json_view.document().toRawText().replace("\u2029", "\n")
        else:
            text = self.panel_r.text()
        if not text:
            self.status.showMessage("当前结果为空，没有可复制的内容")
            return
        QGuiApplication.clipboard().setText(text)
        self.status.showMessage(f"已复制当前结果（{len(text)} 字符）")


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("数据对比工具")
    app.setWindowIcon(application_icon())
    install_exception_handler()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
