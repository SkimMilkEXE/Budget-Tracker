import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.connection import connect
from budget_tracker.db.profile_repo import ProfileRepository
from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService
from budget_tracker.services.transactions import TransactionService
from budget_tracker.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BudgetTracker")  # AppDataLocation is derived from this

    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(data_dir / "budget.db")

    tx_repo = TransactionRepository(conn)
    window = MainWindow(
        CategoryService(CategoryRepository(conn)),
        TransactionService(tx_repo),
        ImportService(tx_repo, ProfileRepository(conn)),
    )
    window.show()
    return app.exec()  # Qt's event loop; returns when the last window closes


if __name__ == "__main__":
    sys.exit(main())
