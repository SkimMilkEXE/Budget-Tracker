import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.connection import connect
from budget_tracker.services.categories import CategoryService
from budget_tracker.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BudgetTracker")  # AppDataLocation is derived from this

    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(data_dir / "budget.db")

    window = MainWindow(CategoryService(CategoryRepository(conn)))
    window.show()
    return app.exec()  # Qt's event loop; returns when the last window closes


if __name__ == "__main__":
    sys.exit(main())
