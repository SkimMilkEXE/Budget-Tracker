import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from budget_tracker.db.budget_repo import BudgetRepository
from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.connection import connect
from budget_tracker.db.profile_repo import ProfileRepository
from budget_tracker.db.recurring_repo import RecurringRepository
from budget_tracker.db.rule_repo import RuleRepository
from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.services.budgets import BudgetService
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService
from budget_tracker.services.recurring_detection import RecurringService
from budget_tracker.services.reports import ReportService
from budget_tracker.services.rules import RuleService
from budget_tracker.services.transactions import TransactionService
from budget_tracker.ui.main_window import MainWindow
from budget_tracker.ui.settings import APP_NAME, app_settings

ASSETS = Path(__file__).parent / "assets"
OLD_NAME = "BudgetTracker"  # the app's name before it became SkimWise


def move_old_data_dir(data_dir: Path) -> None:
    """One-time move of the data folder saved under the old app name, so renaming the app loses nothing."""
    old_dir = data_dir.parent / OLD_NAME
    if old_dir.is_dir() and not data_dir.exists():
        old_dir.rename(data_dir)  # the database (and anything else) moves with the folder


def copy_old_settings(old: QSettings, new: QSettings) -> None:
    """One-time copy of preferences saved under the old app name (only if none exist under the new one)."""
    if old.allKeys() and not new.allKeys():
        for key in old.allKeys():
            new.setValue(key, old.value(key))


def main() -> int:
    if sys.platform == "win32":
        # Give the app its own taskbar identity; otherwise Windows groups it under python.exe
        # and shows Python's icon instead of ours.
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_NAME)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)  # AppDataLocation is derived from this
    app.setWindowIcon(QIcon(str(ASSETS / "budget-icon.ico")))  # every window and dialog inherits it

    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    move_old_data_dir(data_dir)
    copy_old_settings(QSettings(OLD_NAME, OLD_NAME), app_settings())
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(data_dir / "budget.db")

    tx_repo, rule_repo, cat_repo = TransactionRepository(conn), RuleRepository(conn), CategoryRepository(conn)
    window = MainWindow(
        CategoryService(cat_repo),
        TransactionService(tx_repo),
        ImportService(tx_repo, ProfileRepository(conn), rule_repo),
        RuleService(rule_repo, tx_repo),
        BudgetService(BudgetRepository(conn), tx_repo, cat_repo),
        ReportService(tx_repo, cat_repo),
        RecurringService(RecurringRepository(conn), tx_repo),
    )
    window.show()
    return app.exec()  # Qt's event loop; returns when the last window closes


if __name__ == "__main__":
    sys.exit(main())
