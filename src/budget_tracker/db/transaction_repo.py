from __future__ import annotations  # our list() methods shadow the builtin inside class bodies

import sqlite3
from dataclasses import replace
from datetime import date

from budget_tracker.models import NO_CATEGORY, Transaction

_COLUMNS = "id, date, description, amount_cents, category_id"


def _row(row) -> Transaction:
    id_, iso, description, cents, category_id = row
    return Transaction(id_, date.fromisoformat(iso), description, cents, category_id)


class TransactionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list(self, month: str | None = None, category_id: int | None = None, search: str = "") -> list[Transaction]:
        """month is "YYYY-MM"; None/empty arguments mean "don't filter on this"."""
        where, params = [], []
        if month:
            where.append("substr(date, 1, 7) = ?")
            params.append(month)
        if category_id == NO_CATEGORY:
            where.append("category_id IS NULL")
        elif category_id is not None:
            where.append("category_id = ?")
            params.append(category_id)
        if search:
            where.append("instr(lower(description), lower(?)) > 0")
            params.append(search)
        sql = f"SELECT {_COLUMNS} FROM transactions"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY date DESC, id DESC"
        return [_row(r) for r in self.conn.execute(sql, params)]

    def months(self) -> list[str]:
        """Every "YYYY-MM" that has at least one transaction, newest first."""
        rows = self.conn.execute("SELECT DISTINCT substr(date, 1, 7) FROM transactions ORDER BY 1 DESC")
        return [r[0] for r in rows]

    def spending_by_category(self, month: str) -> dict[int, int]:
        """category id -> net spending in cents for "YYYY-MM" (expenses minus refunds)."""
        rows = self.conn.execute(
            "SELECT category_id, -SUM(amount_cents) FROM transactions "
            "WHERE substr(date, 1, 7) = ? AND category_id IS NOT NULL GROUP BY category_id",
            (month,),
        )
        return dict(rows)

    def add(self, tx: Transaction) -> Transaction:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO transactions (date, description, amount_cents, category_id) VALUES (?, ?, ?, ?)",
                (tx.date.isoformat(), tx.description, tx.amount_cents, tx.category_id),
            )
        return replace(tx, id=cur.lastrowid)

    def add_many(self, txs: list[Transaction]) -> None:
        with self.conn:  # one database transaction: all rows are saved, or none
            self.conn.executemany(
                "INSERT INTO transactions (date, description, amount_cents, category_id) VALUES (?, ?, ?, ?)",
                [(t.date.isoformat(), t.description, t.amount_cents, t.category_id) for t in txs],
            )

    def keys_between(self, start: date, end: date) -> list[tuple[date, str, int]]:
        """(date, description, amount_cents) of every transaction in [start, end], for duplicate checks."""
        rows = self.conn.execute(
            "SELECT date, description, amount_cents FROM transactions WHERE date BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        )
        return [(date.fromisoformat(d), desc, cents) for d, desc, cents in rows]

    def update(self, tx: Transaction) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET date = ?, description = ?, amount_cents = ?, category_id = ? WHERE id = ?",
                (tx.date.isoformat(), tx.description, tx.amount_cents, tx.category_id, tx.id),
            )

    def set_categories(self, changes: list[tuple[int, int | None]]) -> None:
        """Apply (transaction id, category id) pairs in one database transaction."""
        with self.conn:
            self.conn.executemany("UPDATE transactions SET category_id = ? WHERE id = ?", [(c, t) for t, c in changes])

    def delete(self, tx_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
