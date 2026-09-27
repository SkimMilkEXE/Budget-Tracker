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


# Chart colours per role: (light mode, dark mode). Income/spending are validated for colour-blind
# separation and >=3:1 contrast against the app's light and dark backgrounds. Spending is always
# orange and income always blue, in every chart.
_CHART = {
    "income": ("#2a78d6", "#3987e5"),
    "spending": ("#eb6834", "#d95926"),
    "ink": ("#0b0b0b", "#ffffff"),  # titles, legend
    "label": ("#52514e", "#c3c2b7"),  # axis tick labels
    "grid": ("#e1e0d9", "#3d3d3b"),
    "axis": ("#c3c2b7", "#555553"),
}


def _dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def amount_color(cents: int) -> QColor:
    """Green for income, red for expenses, readable in the current light/dark mode."""
    income, expense = _DARK if _dark() else _LIGHT
    return income if cents > 0 else expense


def chart_color(role: str) -> QColor:
    """A chart colour by role ("income", "spending", "ink", "label", "grid", "axis") for the current mode."""
    return QColor(_CHART[role][1 if _dark() else 0])


def budget_color(level: str) -> str:
    """Hex fill for a budget bar: green under, yellow near, red over the limit."""
    return _BUDGET[level][1 if _dark() else 0]
