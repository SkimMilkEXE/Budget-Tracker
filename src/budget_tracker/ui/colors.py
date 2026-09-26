from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication

# (income, expense) text colours; darker shades on light backgrounds, lighter on dark.
_LIGHT = (QColor("#1a7f37"), QColor("#c62828"))
_DARK = (QColor("#4ade80"), QColor("#f87171"))


def amount_color(cents: int) -> QColor:
    """Green for income, red for expenses, readable in the current light/dark mode."""
    dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    income, expense = _DARK if dark else _LIGHT
    return income if cents > 0 else expense
