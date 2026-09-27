from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup, QGuiApplication, QPalette
from PySide6.QtWidgets import QLabel, QMainWindow, QMenu, QTabWidget, QToolButton, QVBoxLayout, QWidget

from budget_tracker.services.budgets import BudgetService
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService
from budget_tracker.services.rules import RuleService
from budget_tracker.services.transactions import TransactionService
from budget_tracker.ui.budgets_view import BudgetsView
from budget_tracker.ui.categories_view import CategoriesView
from budget_tracker.ui.rules_view import RulesView
from budget_tracker.ui.settings import DATE_FORMATS, MONTH_FORMATS, app_settings
from budget_tracker.ui.transactions_view import TransactionsView

# Theme menu entries. ColorScheme.Unknown tells Qt to follow the Windows setting.
THEMES = {"System": Qt.ColorScheme.Unknown, "Light": Qt.ColorScheme.Light, "Dark": Qt.ColorScheme.Dark}


class MainWindow(QMainWindow):
    def __init__(
        self,
        categories: CategoryService,
        transactions: TransactionService,
        importer: ImportService,
        rules: RuleService,
        budgets: BudgetService,
    ):
        super().__init__()
        self.setWindowTitle("Budget Tracker")
        self.resize(900, 600)
        self.settings = app_settings()

        # One tab per feature; later milestones add Charts...
        self.tabs = tabs = QTabWidget()
        tabs.addTab(TransactionsView(transactions, categories, importer, rules), "Transactions")
        tabs.addTab(BudgetsView(budgets, categories), "Budgets")
        tabs.addTab(RulesView(rules, categories), "Rules")
        tabs.addTab(CategoriesView(categories), "Categories")
        # Each view reloads when shown, so edits made in one tab appear in the others.
        tabs.currentChanged.connect(lambda i: tabs.widget(i).refresh())
        # Redraw on light/dark switches too, so theme-dependent colours (budget bars) update.
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: tabs.currentWidget().refresh())
        # Settings sits at the right end of the tab bar instead of in a separate menu bar.
        tabs.setCornerWidget(self._settings_button(), Qt.Corner.TopRightCorner)

        credit = QLabel("Built by SkimMilk.EXE")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setForegroundRole(QPalette.ColorRole.PlaceholderText)  # muted grey that follows the theme
        font = credit.font()
        font.setPointSizeF(font.pointSizeF() * 0.85)
        credit.setFont(font)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 4)  # keep the tabs flush with the window edges
        layout.addWidget(tabs)
        layout.addWidget(credit)
        self.setCentralWidget(central)

    def _settings_button(self) -> QToolButton:
        menu = QMenu(self)
        theme = self.settings.value("theme", "System")
        self._add_choice_menu(menu, "&Theme", {n: n for n in THEMES}, theme, self.set_theme)
        self.set_theme(theme if theme in THEMES else "System")
        months = {key: label for key, (label, _fmt) in MONTH_FORMATS.items()}
        current = self.settings.value("month_format", "numbers")
        self._add_choice_menu(menu, "&Month format", months, current, self.set_month_format)
        dates = {key: label for key, (label, _fmt, _qt) in DATE_FORMATS.items()}
        current = self.settings.value("date_format", "iso")
        self._add_choice_menu(menu, "&Date format", dates, current, self.set_date_format)

        button = QToolButton()
        button.setText("Settings")
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)  # open the menu on click
        button.setAutoRaise(True)  # flat until hovered, like the tabs next to it
        button.setStyleSheet("QToolButton { padding: 2px 10px; } QToolButton::menu-indicator { image: none; }")
        return button

    def _add_choice_menu(
        self, menu: QMenu, title: str, options: dict[str, str], current: str, on_pick: Callable[[str], None]
    ) -> None:
        """A submenu of mutually exclusive choices (key -> label), with `current` checked."""
        submenu = menu.addMenu(title)
        group = QActionGroup(submenu)  # makes the actions mutually exclusive, like radio buttons
        for key, label in options.items():
            action = submenu.addAction(label)
            action.setCheckable(True)
            action.setChecked(key == current)
            group.addAction(action)
            action.triggered.connect(lambda _checked, k=key: on_pick(k))

    def set_theme(self, name: str) -> None:
        QGuiApplication.styleHints().setColorScheme(THEMES[name])
        self.settings.setValue("theme", name)

    def set_month_format(self, key: str) -> None:
        self.settings.setValue("month_format", key)
        self.tabs.currentWidget().refresh()  # relabel month pickers (other tabs refresh when shown)

    def set_date_format(self, key: str) -> None:
        self.settings.setValue("date_format", key)
        self.tabs.currentWidget().refresh()  # redraw dates (other tabs refresh when shown)
