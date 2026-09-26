from PySide6.QtWidgets import QMainWindow, QTabWidget

from budget_tracker.services.categories import CategoryService
from budget_tracker.ui.categories_view import CategoriesView


class MainWindow(QMainWindow):
    def __init__(self, categories: CategoryService):
        super().__init__()
        self.setWindowTitle("Budget Tracker")
        self.resize(900, 600)

        # One tab per feature; later milestones add Transactions, Budgets, Charts...
        tabs = QTabWidget()
        tabs.addTab(CategoriesView(categories), "Categories")
        self.setCentralWidget(tabs)
