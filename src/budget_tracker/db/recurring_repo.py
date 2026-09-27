import sqlite3

from budget_tracker.models import RecurringItem


class RecurringRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def confirmed(self) -> list[RecurringItem]:
        rows = self.conn.execute(
            "SELECT id, name, amount_cents, frequency FROM recurring_items "
            "WHERE dismissed = 0 ORDER BY name COLLATE NOCASE"
        )
        return [RecurringItem(*r) for r in rows]

    def known_names(self) -> set[str]:
        """Upper-cased names of every item, confirmed or dismissed: these aren't suggested again."""
        return {r[0].upper() for r in self.conn.execute("SELECT name FROM recurring_items")}

    def add(self, name: str, amount_cents: int, frequency: str, dismissed: bool = False) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO recurring_items (name, amount_cents, frequency, dismissed) VALUES (?, ?, ?, ?)",
                (name, amount_cents, frequency, dismissed),
            )

    def update(self, item_id: int, name: str, amount_cents: int, frequency: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE recurring_items SET name = ?, amount_cents = ?, frequency = ? WHERE id = ?",
                (name, amount_cents, frequency, item_id),
            )

    def dismissed_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM recurring_items WHERE dismissed = 1").fetchone()[0]

    def clear_dismissed(self) -> int:
        """Forget every "not recurring" choice. Returns how many were cleared."""
        with self.conn:
            return self.conn.execute("DELETE FROM recurring_items WHERE dismissed = 1").rowcount

    def delete(self, item_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM recurring_items WHERE id = ?", (item_id,))
