import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from budget_tracker.db.budget_repo import BudgetRepository
from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.connection import connect
from budget_tracker.db.profile_repo import ProfileRepository
from budget_tracker.db.rule_repo import RuleRepository
from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.services.budgets import BudgetService
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService
from budget_tracker.services.reports import ReportService
from budget_tracker.services.rules import RuleService
from budget_tracker.services.transactions import TransactionService
from budget_tracker.ui.main_window import MainWindow

ASSETS = Path(__file__).parent / "assets"


def main() -> int:
    if sys.platform == "win32":
        # Give the app its own taskbar identity; otherwise Windows groups it under python.exe
        # and shows Python's icon instead of ours.
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BudgetTracker")

    app = QApplication(sys.argv)
    app.setApplicationName("BudgetTracker")  # AppDataLocation is derived from this
    app.setWindowIcon(QIcon(str(ASSETS / "budget-icon.ico")))  # every window and dialog inherits it

    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
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
    )
    window.show()
    return app.exec()  # Qt's event loop; returns when the last window closes


if __name__ == "__main__":
    sys.exit(main())
