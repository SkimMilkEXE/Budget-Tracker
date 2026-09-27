"""Every service the UI needs, built for one database connection."""

import sqlite3
from dataclasses import dataclass

from budget_tracker.db.budget_repo import BudgetRepository
from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.profile_repo import ProfileRepository
from budget_tracker.db.recurring_repo import RecurringRepository
from budget_tracker.db.rule_repo import RuleRepository
from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.services.backup import BackupService
from budget_tracker.services.budgets import BudgetService
from budget_tracker.services.categories import CategoryService
from budget_tracker.services.csv_import import ImportService
from budget_tracker.services.recurring_detection import RecurringService
from budget_tracker.services.reports import ReportService
from budget_tracker.services.rules import RuleService
from budget_tracker.services.transactions import TransactionService


@dataclass(frozen=True)
class AppServices:
    categories: CategoryService
    transactions: TransactionService
    importer: ImportService
    rules: RuleService
    budgets: BudgetService
    reports: ReportService
    recurring: RecurringService
    backup: BackupService


def build_services(conn: sqlite3.Connection) -> AppServices:
    tx, rules, cats = TransactionRepository(conn), RuleRepository(conn), CategoryRepository(conn)
    return AppServices(
        categories=CategoryService(cats),
        transactions=TransactionService(tx),
        importer=ImportService(tx, ProfileRepository(conn), rules),
        rules=RuleService(rules, tx),
        budgets=BudgetService(BudgetRepository(conn), tx, cats),
        reports=ReportService(tx, cats),
        recurring=RecurringService(RecurringRepository(conn), tx),
        backup=BackupService(conn),
    )
