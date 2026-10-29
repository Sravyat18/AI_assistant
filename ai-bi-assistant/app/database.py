import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "sales.db"


def get_db_path() -> str:
    return os.getenv("DB_PATH", str(DEFAULT_DB_PATH))


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: str | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                order_date TEXT NOT NULL,
                product TEXT NOT NULL,
                category TEXT NOT NULL,
                region TEXT NOT NULL,
                sales_channel TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL,
                discount_amount REAL NOT NULL,
                status TEXT NOT NULL,
                data_quality_flags TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_file TEXT NOT NULL,
                rows_seen INTEGER NOT NULL,
                rows_inserted INTEGER NOT NULL,
                rows_flagged INTEGER NOT NULL
            )
        """)
