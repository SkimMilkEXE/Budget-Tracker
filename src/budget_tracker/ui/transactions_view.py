from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from budget_tracker.models import NO_CATEGORY, Transaction
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService, read_rows
from budget_tracker.services.money import format_cents
from budget_tracker.services.transactions import TransactionError, TransactionService
from budget_tracker.ui.import_dialog import ImportDialog

UNCATEGORIZED = "Uncategorized"


class TransactionTableModel(QAbstractTableModel):
    """Model/view: the model owns the rows and answers "what goes in cell (r, c)?";
    QTableView just asks and draws. Qt calls data() once per cell per *role*:
    DisplayRole is the text, UserRole is our raw value used for sorting."""

    HEADERS = ["Date", "Description", "Category", "Amount"]

    def __init__(self):
        super().__init__()
        self.rows: list[Transaction] = []
        self.category_names: dict[int, str] = {}

    def set_rows(self, rows: list[Transaction], category_names: dict[int, str]) -> None:
        self.beginResetModel()  # tells attached views to drop everything and re-ask
        self.rows, self.category_names = rows, category_names
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        tx = self.rows[index.row()]
        col = index.column()
        category = self.category_names.get(tx.category_id, UNCATEGORIZED)
        if role == Qt.ItemDataRole.DisplayRole:
            return [tx.date.isoformat(), tx.description, category, format_cents(tx.amount_cents)][col]
        if role == Qt.ItemDataRole.UserRole:
            return [tx.date.isoformat(), tx.description.lower(), category.lower(), tx.amount_cents][col]
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 3:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None


class TransactionDialog(QDialog):
    """Add/edit form. `on_save(**values)` does the saving; if it raises
    TransactionError the message is shown and the dialog stays open."""

    def __init__(self, parent, title, categories, on_save, tx: Transaction | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.on_save = on_save

        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.kind = QComboBox()
        self.kind.addItems(["Expense", "Income"])
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("12.34")
        self.description = QLineEdit()
        self.category = QComboBox()
        self.category.addItem(UNCATEGORIZED, None)
        for c in categories:
            self.category.addItem(c.name, c.id)

        if tx:
            self.date.setDate(QDate(tx.date.year, tx.date.month, tx.date.day))
            self.kind.setCurrentIndex(0 if tx.amount_cents < 0 else 1)
            self.amount.setText(format_cents(abs(tx.amount_cents)))
            self.description.setText(tx.description)
            self.category.setCurrentIndex(max(0, self.category.findData(tx.category_id)))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Date:", self.date)
        form.addRow("Type:", self.kind)
        form.addRow("Amount:", self.amount)
        form.addRow("Description:", self.description)
        form.addRow("Category:", self.category)
        form.addRow(buttons)

    def accept(self):
        try:
            self.on_save(
                when=self.date.date().toPython(),
                description=self.description.text(),
                amount=self.amount.text(),
                is_expense=self.kind.currentIndex() == 0,
                category_id=self.category.currentData(),
            )
        except TransactionError as e:
            QMessageBox.warning(self, "Can't save transaction", str(e))
            return
        super().accept()


class TransactionsView(QWidget):
    def __init__(self, transactions: TransactionService, categories: CategoryService, importer: ImportService):
        super().__init__()
        self.transactions = transactions
        self.categories = categories
        self.importer = importer

        # Filter bar
        self.month = QComboBox()
        self.category = QComboBox()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search descriptions…")
        self.search.setClearButtonEnabled(True)
        self.month.currentIndexChanged.connect(self.reload_table)
        self.category.currentIndexChanged.connect(self.reload_table)
        self.search.textChanged.connect(self.reload_table)

        add_btn = QPushButton("Add…")
        self.edit_btn = QPushButton("Edit…")
        self.delete_btn = QPushButton("Delete")
        add_btn.clicked.connect(self.add)
        import_btn = QPushButton("Import CSV…")
        import_btn.clicked.connect(self.import_csv)
        self.edit_btn.clicked.connect(self.edit)
        self.delete_btn.clicked.connect(self.delete)

        # Table: view -> proxy (sorting on header click) -> model (our data)
        self.model = TransactionTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)  # sort by raw values, not display text
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self.edit)
        self.table.selectionModel().selectionChanged.connect(self.update_buttons)

        bar = QHBoxLayout()
        for w in (import_btn, add_btn, self.edit_btn, self.delete_btn):
            bar.addWidget(w)
        bar.addStretch()
        bar.addWidget(self.month)
        bar.addWidget(self.category)
        bar.addWidget(self.search)

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        """Reload filter choices (categories/months may have changed) and the table."""
        self._category_list = self.categories.list()
        _refill(self.month, "All months", [(m, m) for m in self.transactions.months()])
        categories = [(UNCATEGORIZED, NO_CATEGORY)] + [(c.name, c.id) for c in self._category_list]
        _refill(self.category, "All categories", categories)
        self.reload_table()

    def reload_table(self) -> None:
        rows = self.transactions.list(self.month.currentData(), self.category.currentData(), self.search.text())
        self.model.set_rows(rows, {c.id: c.name for c in self._category_list})
        self.update_buttons()

    def update_buttons(self) -> None:
        has_selection = self.selected() is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def selected(self) -> Transaction | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self.model.rows[self.proxy.mapToSource(rows[0]).row()]  # proxy row != model row once sorted

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import bank CSV", "", "CSV files (*.csv);;All files (*)")
        if not path:
            return
        try:
            rows = read_rows(path)
        except OSError as e:
            QMessageBox.warning(self, "Can't open file", str(e))
            return
        dialog = ImportDialog(self, self.importer, Path(path), rows)
        if dialog.exec():
            self.refresh()
            QMessageBox.information(self, "Import complete", f"Imported {dialog.imported} transactions.")

    def add(self) -> None:
        if TransactionDialog(self, "Add transaction", self._category_list, self.transactions.add).exec():
            self.refresh()

    def edit(self) -> None:
        if not (tx := self.selected()):
            return

        def save(**values):
            self.transactions.update(tx.id, **values)

        if TransactionDialog(self, "Edit transaction", self._category_list, save, tx).exec():
            self.refresh()

    def delete(self) -> None:
        if not (tx := self.selected()):
            return
        answer = QMessageBox.question(
            self, "Delete transaction", f'Delete "{tx.description}" ({format_cents(tx.amount_cents)})?'
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.transactions.delete(tx.id)
            self.refresh()


def _refill(combo: QComboBox, all_label: str, items: list[tuple[str, object]]) -> None:
    """Replace a filter combo's items, keeping the current choice if it still exists."""
    current = combo.currentData()
    combo.blockSignals(True)  # don't fire currentIndexChanged for every intermediate state
    combo.clear()
    combo.addItem(all_label, None)
    for label, value in items:
        combo.addItem(label, value)
    combo.setCurrentIndex(max(0, combo.findData(current)))
    combo.blockSignals(False)
