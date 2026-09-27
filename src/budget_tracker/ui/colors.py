from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication

from budget_tracker.services.budgets import NEAR, OK, OVER

# (income, expense) text colours; darker shades on light backgrounds, lighter on dark.
_LIGHT = (QColor("#1a7f37"), QColor("#c62828"))
_DARK = (QColor("#4ade80"), QColor("#f87171"))

# Budget progress bar fills per level: (light mode, dark mode).
_BUDGET = {
    OK: ("#2e9e5b", "#4ade80"),
    NEAR: ("#d49b00", "#facc15"),
    OVER: ("#d93025", "#f87171"),
}


def _dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def amount_color(cents: int) -> QColor:
    """Green for income, red for expenses, readable in the current light/dark mode."""
    income, expense = _DARK if _dark() else _LIGHT
    return income if cents > 0 else expense


def budget_color(level: str) -> str:
    """Hex fill for a budget bar: green under, yellow near, red over the limit."""
    return _BUDGET[level][1 if _dark() else 0]
