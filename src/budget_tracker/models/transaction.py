from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Transaction:
    id: int | None  # None until saved
    date: date
    description: str
    amount_cents: int  # negative = expense, positive = income
    category_id: int | None = None
