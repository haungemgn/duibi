"""桌面工作区主题和可缩放的操作图标。"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


_LIGHT = {
    "name": "浅色", "bg": "#f5f6fa", "card": "#ffffff", "fg": "#202b41",
    "secondary_fg": "#44516a", "muted": "#606e85", "placeholder": "#738097",
    "border": "#d4dce7", "divider": "#e4e9f1", "recess": "#eef1f7",
    "accent": "#5049bf", "accent_hover": "#423aa9", "on_accent": "#ffffff",
    "subtle": "#eceaff", "subtle_fg": "#4e45ad", "green": "#dff2ed", "green_fg": "#146958",
    "rail_icon": "#bdcce4", "rail_active_icon": "#ffffff",
    "json_key": "#6741ab", "json_string": "#146758", "json_number": "#285aab", "json_literal": "#9b491f",
}

THEMES = {
    "white": _LIGHT,
    "gray": {
        **_LIGHT, "name": "灰色", "bg": "#e5e8ed", "card": "#f5f6f8",
        "border": "#c1c8d2", "divider": "#d7dce3", "recess": "#e6e8ee",
    },
    "black": {
        **_LIGHT, "name": "深色", "bg": "#161c28", "card": "#202838", "fg": "#eef2fa",
        "secondary_fg": "#d4deed", "muted": "#abb8cd", "placeholder": "#9aa8bd",
        "border": "#3c485e", "divider": "#364154", "recess": "#303b50",
        "accent": "#6258cb", "accent_hover": "#6b61d2", "subtle": "#38375d", "subtle_fg": "#d6d0ff",
        "green": "#25433f", "green_fg": "#a1e6d1",
        "json_key": "#c4a7fa", "json_string": "#96dbc0", "json_number": "#9fc5ff", "json_literal": "#ffc08a",
    },
}


def build_stylesheet(theme: dict[str, str]) -> str:
    """按对象名称设置容器和控件，避免给嵌套的 Qt 子控件误加边框。"""
    return """
    QWidget {
        color: %(fg)s;
        font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        font-size: 13px;
    }
    QMainWindow, QWidget#workspace { background-color: %(bg)s; }
    QLabel { background: transparent; border: none; }
    QFrame#sidebar { background-color: #1b2436; border: none; }
    QLabel#brandMark, QPushButton#brandMark {
        background-color: #6159d7; border-radius: 9px; color: white;
    }
    QLabel#brandName { font-size: 19px; font-weight: 700; color: #f6f8ff; }
    QLabel#railHeading {
        color: #a8b5cc; font-weight: 600; font-size: 11px; padding: 1px 8px 2px;
    }
    QLabel#railHint { color: #b2c0d8; background: transparent; font-size: 12px; }
    QPushButton[active="true"] QLabel#railHint { color: #e3e1ff; }
    QFrame#railRule { border: none; background-color: #354158; }
    QPushButton#railAction, QToolButton#railMenu, QToolButton#themeMenu {
        text-align: left; color: #e0e7f5; font-weight: 500;
        background: transparent; border: 1px solid transparent; border-radius: 6px;
        min-height: 28px; padding: 1px 8px;
    }
    QPushButton#railAction:hover, QToolButton#railMenu:hover, QToolButton#themeMenu:hover {
        background-color: #2a374e; color: #ffffff;
    }
    QPushButton#railAction:pressed, QToolButton#railMenu:pressed, QToolButton#themeMenu:pressed {
        background-color: #36445f;
    }
    QPushButton#railAction[active="true"], QToolButton#railMenu[active="true"] {
        background-color: #494392; color: #ffffff; font-weight: 600;
    }
    QPushButton#railAction:focus, QToolButton#railMenu:focus, QToolButton#themeMenu:focus {
        border-color: #b7b4ff;
    }
    QToolButton#railMenu::menu-indicator, QToolButton#themeMenu::menu-indicator {
        subcontrol-origin: padding; subcontrol-position: right center; right: 5px;
    }
    QLabel#sectionTitle { font-size: 20px; font-weight: 700; }
    QFrame#editorCard, QFrame#resultCard {
        background-color: %(card)s; border: 1px solid %(border)s; border-radius: 10px;
    }
    QFrame#cardRule { background-color: %(divider)s; border: none; }
    QLabel#panelBadge {
        border-radius: 6px; background-color: %(subtle)s; color: %(subtle_fg)s;
        font: 700 14px "Segoe UI";
    }
    QLabel#panelBadge[role="B"] { background-color: %(green)s; color: %(green_fg)s; }
    QLabel#panelTitle { font-size: 15px; font-weight: 600; }
    QLabel#countLabel { color: %(muted)s; font-size: 12px; }
    QPlainTextEdit {
        background-color: %(card)s; color: %(fg)s; placeholder-text-color: %(placeholder)s;
        font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI", monospace;
        font-size: 14px; border: 1px solid transparent;
        border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;
        selection-background-color: %(accent)s; selection-color: %(on_accent)s;
    }
    QPlainTextEdit:focus { border-bottom-color: %(subtle_fg)s; }
    QCheckBox { spacing: 6px; color: %(secondary_fg)s; font-size: 12px; }
    QCheckBox:disabled { color: %(placeholder)s; }
    QPushButton#secondaryAction, QPushButton#copyAction {
        background-color: %(card)s; color: %(secondary_fg)s; border: 1px solid %(border)s;
        padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;
    }
    QPushButton#secondaryAction:hover { background-color: %(recess)s; }
    QPushButton#copyAction { background-color: %(accent)s; color: %(on_accent)s; border-color: %(accent)s; }
    QPushButton#copyAction:hover { background-color: %(accent_hover)s; }
    QPushButton#secondaryAction:pressed, QPushButton#copyAction:pressed { background-color: %(subtle)s; color: %(subtle_fg)s; }
    QPushButton#secondaryAction:focus { border-color: %(subtle_fg)s; }
    QPushButton#copyAction:focus { border-color: %(fg)s; }
    QTabBar#resultTabs { background: transparent; }
    QTabBar#resultTabs::tab {
        background: %(recess)s; color: %(secondary_fg)s; border: 1px solid transparent;
        border-radius: 5px; padding: 4px 12px; margin-right: 3px; font-size: 12px;
    }
    QTabBar#resultTabs::tab:selected { background: %(subtle)s; color: %(subtle_fg)s; font-weight: 600; }
    QTabBar#resultTabs::tab:hover { border-color: %(border)s; }
    QSplitter::handle { background: transparent; }
    QSplitter::handle:hover { background: %(divider)s; border-radius: 4px; }
    QMenu, QToolTip { background-color: %(card)s; color: %(fg)s; border: 1px solid %(border)s; padding: 4px; }
    QMenu::item { padding: 6px 20px; border-radius: 4px; }
    QMenu::item:selected { background-color: %(subtle)s; color: %(subtle_fg)s; }
    QStatusBar { background-color: %(bg)s; color: %(muted)s; border-top: 1px solid %(border)s; font-size: 11px; }
    QStatusBar::item { border: none; }
    """ % theme


def icon_for(name: str, color: str, size: int = 18) -> QIcon:
    """在 24 单位网格上绘制图标，并提供双倍分辨率的位图给高 DPI 屏幕。"""
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    with QPainter(pixmap) as painter:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(pixmap.width() / 24, pixmap.height() / 24)
        ink = QColor(color)
        painter.setPen(QPen(ink, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        def line(*points: tuple[float, float]) -> None:
            painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in points]))

        if name in ("difference", "intersection", "union"):
            left, right = QPainterPath(), QPainterPath()
            left.addEllipse(QRectF(2, 5.5, 13, 13))
            right.addEllipse(QRectF(9, 5.5, 13, 13))
            if name == "difference":
                area = left.subtracted(right)
            elif name == "intersection":
                area = left.intersected(right)
            else:
                area = left.united(right)
            shade = QColor(ink)
            shade.setAlpha(135)
            painter.fillPath(area, shade)
            painter.drawPath(left)
            painter.drawPath(right)
        elif name == "distinct":
            line((3, 5), (20, 5))
            line((3, 11), (12, 11))
            line((3, 17), (8, 17))
            line((12, 16), (15, 19), (21, 12))
        elif name in ("duplicates", "copy"):
            line((8, 16), (4, 16), (4, 4), (16, 4), (16, 8))
            painter.drawRoundedRect(QRectF(8, 8, 12, 13), 2, 2)
        elif name == "format":
            line((4, 5), (20, 5))
            line((4, 10), (14, 10))
            line((4, 15), (20, 15))
            line((4, 20), (14, 20))
        elif name == "json":
            line((8, 3), (6, 3), (6, 9), (3, 12), (6, 15), (6, 21), (8, 21))
            line((16, 3), (18, 3), (18, 9), (21, 12), (18, 15), (18, 21), (16, 21))
        elif name == "theme":
            painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
            painter.setBrush(ink)
            painter.drawPie(QRectF(3.5, 3.5, 17, 17), 90 * 16, 180 * 16)
        elif name == "clear":
            line((3, 6), (21, 6))
            line((9, 6), (9, 3), (15, 3), (15, 6))
            line((6, 7), (7, 20), (17, 20), (18, 7))
            line((10, 10), (10.5, 16))
            line((14, 10), (13.5, 16))
        elif name == "swap":
            line((3, 7), (20, 7), (16, 3))
            line((21, 17), (4, 17), (8, 21))
        elif name == "brand":
            painter.setPen(Qt.NoPen)
            painter.setBrush(ink)
            painter.drawRoundedRect(QRectF(2.5, 8, 5, 13), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(9.5, 3, 5, 18), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(16.5, 6, 5, 9), 1.5, 1.5)
        elif name == "chevron":
            line((7, 10), (12, 15), (17, 10))
        else:
            raise ValueError(f"未知图标 {name}")
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def application_icon() -> QIcon:
    """为窗口、任务切换器和高 DPI 标题栏提供匹配的品牌图标。"""
    mark = icon_for("brand", "#ffffff", 128)
    icon = QIcon()
    for edge in (16, 20, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(edge, edge)
        pixmap.fill(Qt.transparent)
        with QPainter(pixmap) as painter:
            painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#6159d7"))
            painter.drawRoundedRect(QRectF(0, 0, edge, edge), edge * .23, edge * .23)
            side = round(edge * .74)
            offset = (edge - side) // 2
            mark.paint(painter, offset, offset, side, side)
        icon.addPixmap(pixmap)
    return icon
