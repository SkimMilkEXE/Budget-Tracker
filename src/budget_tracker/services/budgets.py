from dataclasses import dataclass
from datetime import date

from budget_tracker.db.budget_repo import BudgetRepository
from budget_tracker.db.category_repo import CategoryRepository
from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.services.money import parse_cents

NEAR_LIMIT = 0.8  # at or above this fraction of the limit counts as "near"
OK, NEAR, OVER = "ok", "near", "over"


class BudgetError(ValueError):
    """A user-facing validation error; the message is safe to show in the UI."""


@dataclass(frozen=True)
class BudgetLine:
    category_id: int
    category: str
    limit_cents: int
    spent_cents: int  # net: refunds reduce it; never below 0

    @property
    def fraction(self) -> float:
        return self.spent_cents / self.limit_cents

    @property
    def left_cents(self) -> int:
        """Negative when over budget."""
        return self.limit_cents - self.spent_cents

    @property
    def level(self) -> str:
        if self.spent_cents > self.limit_cents:
            return OVER
        return NEAR if self.fraction >= NEAR_LIMIT else OK


class BudgetService:
    def __init__(self, budgets: BudgetRepository, transactions: TransactionRepository, categories: CategoryRepository):
        self.budgets = budgets
        self.transactions = transactions
        self.categories = categories

    def lines(self, month: str) -> list[BudgetLine]:
        """One line per budgeted category for "YYYY-MM", in category name order."""
        limits = self.budgets.limits()
        spent = self.transactions.spending_by_category(month)
        return [
            BudgetLine(c.id, c.name, limits[c.id], max(0, spent.get(c.id, 0)))
            for c in self.categories.list()
            if c.id in limits
        ]

    def months(self, today: date | None = None) -> list[str]:
        """Months to offer in the picker, newest first: every month with transactions, plus this one."""
        current = (today or date.today()).strftime("%Y-%m")
        return sorted(set(self.transactions.months()) | {current}, reverse=True)

    def set_limit(self, category_id: int | None, amount: str) -> None:
        if category_id is None:
            raise BudgetError("Choose a category.")
        try:
            cents = abs(parse_cents(amount))
        except ValueError:
            raise BudgetError("Enter a monthly limit like 400 or 250.50.") from None
        if cents == 0:
            raise BudgetError("The limit must be more than zero.")
        self.budgets.set(category_id, cents)

    def remove(self, category_id: int) -> None:
        self.budgets.delete(category_id)
