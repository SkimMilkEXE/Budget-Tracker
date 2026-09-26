import sqlite3
from pathlib import Path

# Each entry upgrades the schema by one version. Append new entries; never edit old ones.
# PRAGMA user_version records how many have been applied.
MIGRATIONS = [
    """
    CREATE TABLE categories (
        id   INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE
    );
    INSERT INTO categories (name) VALUES
        ('Groceries'), ('Dining'), ('Rent'), ('Utilities'),
        ('Transport'), ('Entertainment'), ('Subscriptions'), ('Income');
    """,
    """
    CREATE TABLE transactions (
        id           INTEGER PRIMARY KEY,
        date         TEXT NOT NULL,              -- YYYY-MM-DD
        description  TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,           -- negative = expense, positive = income
        category_id  INTEGER REFERENCES categories(id) ON DELETE SET NULL
    );
    CREATE INDEX idx_transactions_date ON transactions(date);
    """,
]


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the database (":memory:" for tests) and bring its schema up to date."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for i, script in enumerate(MIGRATIONS[version:], start=version + 1):
        conn.executescript(f"BEGIN; {script} PRAGMA user_version = {i}; COMMIT;")
