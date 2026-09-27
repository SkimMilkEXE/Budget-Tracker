"""Smoke tests for the real window: every tab builds and shows the demo data, and the main flows
work end to end. Runs offscreen against an in-memory database; settings go to a temp .ini file."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

import budget_tracker.ui.settings as settings
from budget_tracker.db.budget_repo import BudgetRepository
from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.connection import connect
from budget_tracker.db.profile_repo import ProfileRepository
from budget_tracker.db.recurring_repo import RecurringRepository
from budget_tracker.db.rule_repo import RuleRepository
from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.services.budgets import BudgetService
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService, read_rows
from budget_tracker.services.recurring_detection import RecurringService
from budget_tracker.services.reports import ReportService
from budget_tracker.services.rules import RuleService
from budget_tracker.services.transactions import TransactionService
from budget_tracker.ui.import_dialog import ImportDialog
from budget_tracker.ui.main_window import MainWindow
from budget_tracker.ui.rules_view import RuleDialog

DEMO = Path(__file__).parent / "fixtures" / "demo_transactions.csv"


@pytest.fixture
def window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    # Never touch the real registry: every app_settings() call gets a temp .ini file instead.
    ini = str(tmp_path / "settings.ini")
    monkeypatch.setattr(settings, "QSettings", lambda *_: QSettings(ini, QSettings.Format.IniFormat))
    # Message boxes would block waiting for a click; answer "Yes" / "OK" automatically.
    monkeypatch.setattr(QMessageBox, "information", lambda *_: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)

    conn = connect(":memory:")
    tx, rules, cats = TransactionRepository(conn), RuleRepository(conn), CategoryRepository(conn)
    w = MainWindow(
        CategoryService(cats),
        TransactionService(tx),
        ImportService(tx, ProfileRepository(conn), rules),
        RuleService(rules, tx),
        BudgetService(BudgetRepository(conn), tx, cats),
        ReportService(tx, cats),
        RecurringService(RecurringRepository(conn), tx),
    )
    w.show()
    yield w
    w.close()
    app.processEvents()


def tab(w, name):
    index = next(i for i in range(w.tabs.count()) if w.tabs.tabText(i) == name)
    w.tabs.setCurrentIndex(index)  # triggers the view's refresh(), like a user click
    return w.tabs.currentWidget()


def import_demo(w):
    view = tab(w, "Transactions")
    dialog = ImportDialog(view, view.importer, DEMO, read_rows(DEMO), {})
    assert dialog.summary.text().startswith("527 new")
    dialog.profile_name.setText("Demo Bank")
    dialog.accept()
    view.refresh()
    return view


def test_tabs_in_order(window):
    names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert names == ["Transactions", "Budgets", "Charts", "Subscriptions", "Rules", "Categories"]


def test_import_then_filter(window):
    view = import_demo(window)
    assert view.proxy.rowCount() == 527
    view.month.setCurrentIndex(view.month.findData("2026-02"))
    assert {view.model.rows[i].date.month for i in range(view.proxy.rowCount())} == {2}
    view.search.setText("netflix")
    assert view.proxy.rowCount() == 1


def test_manual_categorize_offers_rule_that_fills_in_the_rest(window, monkeypatch):
    view = import_demo(window)
    dining = next(c.id for c in view._category_list if c.name == "Dining")
    monkeypatch.setattr(RuleDialog, "exec", lambda self: (self.accept(), self.result())[1])  # user clicks OK
    view._offer_rule("STARBUCKS #10293", dining)
    assert [r.pattern for r in view.rules.list()] == ["STARBUCKS"]
    view.search.setText("starbucks")
    assert all(view.model.rows[i].category_id == dining for i in range(view.proxy.rowCount()))


def test_budgets_tab_shows_progress(window):
    import_demo(window)
    budgets = tab(window, "Budgets")
    groceries = next(c.id for c in budgets.categories.list() if c.name == "Groceries")
    budgets.budgets.set_limit(groceries, "400")
    budgets.refresh()
    assert budgets.table.rowCount() == 1
    assert budgets.table.cellWidget(0, 1) is not None  # the progress bar
    assert budgets.summary.text().startswith("Total:")


def test_charts_tab_draws_all_three(window):
    import_demo(window)
    charts = tab(window, "Charts")
    charts.month.setCurrentIndex(charts.month.findData("2026-09"))
    assert charts.by_category.chart().series()  # uncategorized spending still charts
    bar_sets = charts.income_expenses.chart().series()[0].barSets()
    assert [b.label() for b in bar_sets] == ["Income", "Expenses"]
    assert bar_sets[0].count() == 12  # Oct 2025 - Sep 2026


def test_subscriptions_confirm(window):
    import_demo(window)
    subs = tab(window, "Subscriptions")
    detected = subs.suggestions.rowCount()
    assert detected >= 5
    subs.suggestions.selectRow(0)
    subs.confirm()
    assert subs.table.rowCount() == 1 and subs.suggestions.rowCount() == detected - 1
    assert "/ month" in subs.total.text()


def test_settings_menu_changes_formats_and_theme(window):
    import_demo(window)
    menu = window.tabs.cornerWidget().menu()
    submenu = {a.text().replace("&", ""): a.menu() for a in menu.actions()}
    assert set(submenu) == {"Theme", "Month format", "Date format"}

    next(a for a in submenu["Date format"].actions() if a.text() == "Aug 31, 2026").trigger()
    view = window.tabs.currentWidget()
    assert view.proxy.index(0, 0).data() == "Sep 29, 2026"

    # (The offscreen test platform has no system theme, so we check the saved choice, not the colours.)
    next(a for a in submenu["Theme"].actions() if a.text() == "Dark").trigger()
    assert settings.app_settings().value("theme") == "Dark"  # saved to the temp .ini, not the registry


def test_window_remembers_geometry(window):
    window.resize(1000, 700)
    window.close()
    assert settings.app_settings().value("geometry")
