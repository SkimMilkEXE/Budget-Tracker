from __future__ import annotations  # our list() methods shadow the builtin inside class bodies

from datetime import date

from budget_tracker.db.transaction_repo import TransactionRepository
from budget_tracker.models import Transaction
from budget_tracker.services.money import parse_cents


class TransactionError(ValueError):
    """A user-facing validation error; the message is safe to show in the UI."""


class TransactionService:
    def __init__(self, repo: TransactionRepository):
        self.repo = repo

    def list(self, month: str | None = None, category_id: int | None = None, search: str = "") -> list[Transaction]:
        return self.repo.list(month, category_id, search.strip())

    def months(self) -> list[str]:
        return self.repo.months()

    def add(self, when: date, description: str, amount: str, is_expense: bool, category_id: int | None) -> Transaction:
        return self.repo.add(_build(None, when, description, amount, is_expense, category_id))

    def update(
        self, tx_id: int, when: date, description: str, amount: str, is_expense: bool, category_id: int | None
    ) -> None:
        self.repo.update(_build(tx_id, when, description, amount, is_expense, category_id))

    def delete(self, tx_id: int) -> None:
        self.repo.delete(tx_id)


def _build(tx_id, when, description, amount, is_expense, category_id) -> Transaction:
    description = " ".join(description.split())
    if not description:
        raise TransactionError("Description can't be empty.")
    try:
        cents = abs(parse_cents(amount))  # the sign comes from is_expense, not the text
    except ValueError:
        raise TransactionError("Enter an amount like 12.34.") from None
    if cents == 0:
        raise TransactionError("Amount can't be zero.")
    return Transaction(tx_id, when, description, -cents if is_expense else cents, category_id)
