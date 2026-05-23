import sqlite3
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "grants.db"

REQUIRED_COLUMNS = {
    "id", "file_name", "call_code", "title",
    "beneficiary_text", "activity_text", "indicator_text", "consortium_allowed", "activity_count",
    "submission_start", "submission_end", "min_support", "max_support", "total_budget_huf",
    "support_type", "support_logic_text", "own_fund_required", "own_fund_percent",
    "advance_percent", "advance_max", "project_duration_months",
    "location_text", "project_count", "zsc_category", "intent",
    "risk_score", "risk_category", "llm_summary", "llm_demo", "processed_at"
}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    call_code TEXT,
    title TEXT,
    beneficiary_text TEXT,
    activity_text TEXT,
    indicator_text TEXT,
    consortium_allowed TEXT,
    activity_count INTEGER,
    submission_start TEXT,
    submission_end TEXT,
    min_support INTEGER,
    max_support INTEGER,
    total_budget_huf INTEGER,
    support_type TEXT,
    support_logic_text TEXT,
    own_fund_required TEXT,
    own_fund_percent INTEGER,
    advance_percent INTEGER,
    advance_max INTEGER,
    project_duration_months INTEGER,
    location_text TEXT,
    project_count INTEGER,
    zsc_category TEXT,
    intent TEXT,
    risk_score REAL,
    risk_category TEXT,
    llm_summary TEXT,
    llm_demo TEXT,
    processed_at TEXT
)
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _existing_columns(conn) -> set[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grants'")
    if not cursor.fetchone():
        return set()
    cursor.execute("PRAGMA table_info(grants)")
    return {row[1] for row in cursor.fetchall()}


def create_table(conn, reset_if_incompatible: bool = True):
    """Létrehozza a grants táblát, régi hibás séma esetén újraépíti.

    A korábbi próbafutásokból megmaradhatott olyan grants.db, amelyből hiányzott
    például a file_name mező. Ez okozta a 'table grants has no column named file_name'
    hibát. Ez a függvény ezt automatikusan javítja.
    """
    cursor = conn.cursor()
    existing = _existing_columns(conn)
    if existing and not REQUIRED_COLUMNS.issubset(existing):
        missing = sorted(REQUIRED_COLUMNS - existing)
        if reset_if_incompatible:
            print(f"⚠️ Régi/hibás adatbázis séma. Újraépítés. Hiányzó mezők: {', '.join(missing)}")
            cursor.execute("DROP TABLE IF EXISTS grants")
        else:
            raise RuntimeError(f"Hiányzó adatbázis mezők: {missing}")
    cursor.execute(CREATE_SQL)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_grants_call_code ON grants(call_code)")
    conn.commit()


def clear_table(conn):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grants")
    conn.commit()


def delete_existing_by_call_code(conn, call_code):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grants WHERE call_code = ?", (call_code,))
    conn.commit()


def insert_record(conn, data):
    create_table(conn)
    cols = [
        "file_name", "call_code", "title",
        "beneficiary_text", "activity_text", "indicator_text", "consortium_allowed", "activity_count",
        "submission_start", "submission_end",
        "min_support", "max_support", "total_budget_huf",
        "support_type", "support_logic_text", "own_fund_required", "own_fund_percent",
        "advance_percent", "advance_max",
        "project_duration_months", "location_text", "project_count",
        "zsc_category", "intent",
        "risk_score", "risk_category",
        "llm_summary", "llm_demo", "processed_at",
    ]
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO grants ({', '.join(cols)}) VALUES ({placeholders})"
    values = [data.get(c) for c in cols]
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()


def get_existing_llm(conn, call_code):
    cursor = conn.cursor()
    cursor.execute("SELECT llm_demo FROM grants WHERE call_code = ? LIMIT 1", (call_code,))
    result = cursor.fetchone()
    return result[0] if result else None
