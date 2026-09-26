from PySide6.QtWidgets import QMainWindow, QTabWidget

from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService
from budget_tracker.services.transactions import TransactionService
from budget_tracker.ui.categories_view import CategoriesView
from budget_tracker.ui.transactions_view import TransactionsView


class MainWindow(QMainWindow):
    def __init__(self, categories: CategoryService, transactions: TransactionService, importer: ImportService):
        super().__init__()
        self.setWindowTitle("Budget Tracker")
        self.resize(900, 600)

        # One tab per feature; later milestones add Budgets, Charts...
        tabs = QTabWidget()
        tabs.addTab(TransactionsView(transactions, categories, importer), "Transactions")
        tabs.addTab(CategoriesView(categories), "Categories")
        # Each view reloads when shown, so edits made in one tab appear in the others.
        tabs.currentChanged.connect(lambda i: tabs.widget(i).refresh())
        self.setCentralWidget(tabs)
