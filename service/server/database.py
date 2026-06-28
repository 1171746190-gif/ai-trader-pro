"""
Database Module

数据库初始化、连接和管理
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any, Iterable, Optional, Sequence

from config import DATABASE_URL

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - dependency is optional until PostgreSQL is enabled
    psycopg = None
    dict_row = None


_BASE_DIR = os.path.dirname(__file__)
_DEFAULT_SQLITE_DB_PATH = os.path.join(_BASE_DIR, "data", "clawtrader.db")
_SQLITE_DB_PATH = os.getenv("DB_PATH", _DEFAULT_SQLITE_DB_PATH)
_POSTGRES_NOW_TEXT_SQL = (
    "to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', "
    "'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')"
)
_SQLITE_INTERVAL_PATTERN = re.compile(
    r"datetime\s*\(\s*'now'\s*,\s*'([+-]?\d+)\s+([A-Za-z]+)'\s*\)",
    flags=re.IGNORECASE,
)
_SQLITE_NOW_PATTERN = re.compile(r"datetime\s*\(\s*'now'\s*\)", flags=re.IGNORECASE)
_SQLITE_AUTOINCREMENT_PATTERN = re.compile(
    r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
    flags=re.IGNORECASE,
)
_SQLITE_REAL_PATTERN = re.compile(r"\bREAL\b", flags=re.IGNORECASE)
_ALTER_ADD_COLUMN_PATTERN = re.compile(
    r"\bALTER\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s+ADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS)",
    flags=re.IGNORECASE,
)
_POSTGRES_RETRYABLE_SQLSTATES = {"40001", "40P01", "55P03"}


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def get_database_backend_name() -> str:
    return "postgresql" if using_postgres() else "sqlite"


def begin_write_transaction(cursor: Any) -> None:
    """Start a write transaction using syntax compatible with the active backend."""
    if using_postgres():
        cursor.execute("BEGIN")
        return
    cursor.execute("BEGIN IMMEDIATE")


def is_retryable_db_error(exc: Exception) -> bool:
    """Return True when the error is a transient write conflict worth retrying."""
    if isinstance(exc, sqlite3.OperationalError):
        message = str(exc).lower()
        return "database is locked" in message or "database is busy" in message

    sqlstate = getattr(exc, "sqlstate", None)
    if not sqlstate:
        cause = getattr(exc, "__cause__", None)
        sqlstate = getattr(cause, "sqlstate", None)
    if sqlstate in _POSTGRES_RETRYABLE_SQLSTATES:
        return True

    message = str(exc).lower()
    return any(
        fragment in message
        for fragment in (
            "could not serialize access",
            "deadlock detected",
            "lock not available",
            "database is locked",
            "database is busy",
        )
    )


def _replace_unquoted_question_marks(sql: str) -> str:
    """Translate sqlite-style placeholders to psycopg placeholders."""
    result: list[str] = []
    i = 0
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False

    while i < len(sql):
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < len(sql) else ""

        if in_line_comment:
            result.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            result.append(char)
            if char == "*" and next_char == "/":
                result.append(next_char)
                i += 2
                in_block_comment = False
            else:
                i += 1
            continue

        if not in_single and not in_double and char == "-" and next_char == "-":
            result.append(char)
            result.append(next_char)
            i += 2
            in_line_comment = True
            continue

        if not in_single and not in_double and char == "/" and next_char == "*":
            result.append(char)
            result.append(next_char)
            i += 2
            in_block_comment = True
            continue

        if char == "'" and not in_double:
            result.append(char)
            if in_single and next_char == "'":
                result.append(next_char)
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue

        if char == '"' and not in_single:
            in_double = not in_double
            result.append(char)
            i += 1
            continue

        if char == "?" and not in_single and not in_double:
            result.append("%s")
            i += 1
            continue

        result.append(char)
        i += 1

    return "".join(result)


def _escape_psycopg_percent_literals(sql: str) -> str:
    """Escape literal percent signs before psycopg placeholder parsing."""
    result: list[str] = []
    i = 0
    while i < len(sql):
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < len(sql) else ""
        if char == "%":
            result.append("%%")
            i += 2 if next_char == "%" else 1
            continue
        result.append(char)
        i += 1
    return "".join(result)


def _replace_sqlite_datetime_functions(sql: str) -> str:
    def replace_interval(match: re.Match[str]) -> str:
        amount = match.group(1)
        unit = match.group(2)
        return f"to_char((CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + INTERVAL '{amount} {unit}', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')"

    sql = _SQLITE_INTERVAL_PATTERN.sub(replace_interval, sql)
    sql = _SQLITE_NOW_PATTERN.sub(_POSTGRES_NOW_TEXT_SQL, sql)
    return sql


def _adapt_sql_for_postgres(sql: str) -> str:
    adapted = sql
    adapted = _SQLITE_AUTOINCREMENT_PATTERN.sub("SERIAL PRIMARY KEY", adapted)
    adapted = _SQLITE_REAL_PATTERN.sub("DOUBLE PRECISION", adapted)
    adapted = _ALTER_ADD_COLUMN_PATTERN.sub(r"ALTER TABLE \1 ADD COLUMN IF NOT EXISTS ", adapted)
    adapted = _replace_sqlite_datetime_functions(adapted)
    adapted = _escape_psycopg_percent_literals(adapted)
    adapted = _replace_unquoted_question_marks(adapted)
    return adapted


# ==================== Connection ====================

_db_connection: Optional[Any] = None


def get_db_connection() -> Any:
    """Get database connection (singleton)."""
    global _db_connection
    
    if _db_connection is not None:
        return _db_connection
    
    if using_postgres():
        if psycopg is None:
            raise RuntimeError("psycopg not installed but DATABASE_URL is set")
        _db_connection = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    else:
        os.makedirs(os.path.dirname(_SQLITE_DB_PATH), exist_ok=True)
        _db_connection = sqlite3.connect(_SQLITE_DB_PATH)
        _db_connection.row_factory = sqlite3.Row
    
    return _db_connection


def get_db() -> Any:
    """Alias for get_db_connection."""
    return get_db_connection()


def close_db() -> None:
    """Close database connection."""
    global _db_connection
    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None


def get_database_status() -> dict[str, Any]:
    """Get database connection status."""
    return {
        "backend": get_database_backend_name(),
        "connected": _db_connection is not None,
        "path": None if using_postgres() else _SQLITE_DB_PATH,
    }


# ==================== SQL Execution ====================

def execute_sql(sql: str, params: Optional[Sequence[Any]] = None) -> Any:
    """Execute SQL with backend adaptation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if using_postgres():
        sql = _adapt_sql_for_postgres(sql)
    
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    
    conn.commit()
    return cursor


def execute_many(sql: str, params_list: Iterable[Sequence[Any]]) -> None:
    """Execute SQL with multiple parameter sets."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if using_postgres():
        sql = _adapt_sql_for_postgres(sql)
    
    cursor.executemany(sql, params_list)
    conn.commit()


# ==================== Schema ====================

_INIT_SQL = """
-- Core tables
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    email TEXT,
    password_hash TEXT,
    token TEXT,
    token_expires_at TEXT,
    wallet_address TEXT,
    identity_status TEXT DEFAULT 'normal',
    is_verified INTEGER DEFAULT 0,
    initial_balance REAL DEFAULT 100000,
    cash_balance REAL DEFAULT 100000,
    points INTEGER DEFAULT 0,
    role TEXT DEFAULT 'user',
    created_at TEXT DEFAULT datetime('now'),
    updated_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS user_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT datetime('now')
);

-- Signals
CREATE TABLE IF NOT EXISTS signal_sequence (
    id INTEGER PRIMARY KEY AUTOINCREMENT
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER REFERENCES agents(id),
    agent_name TEXT,
    message_type TEXT NOT NULL,
    market TEXT,
    title TEXT,
    content TEXT,
    symbol TEXT,
    action TEXT,
    price REAL,
    quantity REAL,
    side TEXT,
    symbols TEXT,
    tags TEXT,
    challenge_key TEXT,
    quality_score REAL,
    points_earned INTEGER DEFAULT 0,
    executed_at TEXT,
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS signal_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL REFERENCES signals(id),
    agent_id INTEGER REFERENCES agents(id),
    content TEXT NOT NULL,
    created_at TEXT DEFAULT datetime('now')
);

-- Social
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leader_id INTEGER NOT NULL REFERENCES agents(id),
    follower_id INTEGER NOT NULL REFERENCES agents(id),
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT datetime('now'),
    UNIQUE(leader_id, follower_id)
);

-- Trading
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    token_id TEXT,
    outcome TEXT,
    side TEXT,
    quantity REAL DEFAULT 0,
    entry_price REAL,
    current_price REAL,
    opened_at TEXT,
    leader_id INTEGER,
    created_at TEXT DEFAULT datetime('now'),
    updated_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS profit_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    total_pnl REAL DEFAULT 0,
    cash_balance REAL,
    position_value REAL,
    total_value REAL,
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS points_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    points INTEGER NOT NULL,
    type TEXT,
    reference_id INTEGER,
    reason TEXT,
    experiment_key TEXT,
    variant_key TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT datetime('now')
);

-- Challenges
CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    market TEXT DEFAULT 'us-stock',
    start_at TEXT,
    end_at TEXT,
    initial_balance REAL DEFAULT 100000,
    status TEXT DEFAULT 'active',
    created_by INTEGER,
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS challenge_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_key TEXT NOT NULL,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    current_balance REAL,
    total_pnl REAL DEFAULT 0,
    rank INTEGER,
    joined_at TEXT DEFAULT datetime('now'),
    UNIQUE(challenge_key, agent_id)
);

CREATE TABLE IF NOT EXISTS challenge_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_key TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    action TEXT,
    symbol TEXT,
    price REAL,
    quantity REAL,
    pnl REAL,
    executed_at TEXT,
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_key TEXT,
    mission_key TEXT,
    name TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    role TEXT DEFAULT 'member',
    joined_at TEXT DEFAULT datetime('now'),
    UNIQUE(team_id, agent_id)
);

-- Experiments
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    target_type TEXT DEFAULT 'agent',
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS experiment_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_key TEXT NOT NULL,
    variant_key TEXT NOT NULL,
    weight REAL DEFAULT 50,
    config TEXT,
    UNIQUE(experiment_key, variant_key)
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_key TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    variant_key TEXT NOT NULL,
    assigned_at TEXT DEFAULT datetime('now'),
    UNIQUE(experiment_key, agent_id)
);

CREATE TABLE IF NOT EXISTS experiment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    payload TEXT,
    created_at TEXT DEFAULT datetime('now')
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    type TEXT,
    message TEXT NOT NULL,
    metadata TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT datetime('now')
);

-- Market data
CREATE TABLE IF NOT EXISTS market_news_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    data TEXT,
    created_at TEXT DEFAULT datetime('now')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_signals_agent ON signals(agent_id);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(message_type);
CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(market);
CREATE INDEX IF NOT EXISTS idx_positions_agent ON positions(agent_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_leader ON subscriptions(leader_id);
CREATE INDEX IF NOT EXISTS idx_experiment_events ON experiment_events(experiment_key, event_type);
CREATE INDEX IF NOT EXISTS idx_notifications_agent ON notifications(agent_id, is_read);
"""


def init_database() -> None:
    """Initialize database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if using_postgres():
        sql = _adapt_sql_for_postgres(_INIT_SQL)
    else:
        sql = _INIT_SQL
    
    cursor.executescript(sql)
    conn.commit()
    print("[Database] Initialized successfully")


# ==================== Query Helpers ====================

def query_one(sql: str, params: Optional[Sequence[Any]] = None) -> Optional[dict]:
    """Execute query and return first row as dict."""
    cursor = execute_sql(sql, params)
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        return None
    return dict(row)


def query_all(sql: str, params: Optional[Sequence[Any]] = None) -> list[dict]:
    """Execute query and return all rows as list of dicts."""
    cursor = execute_sql(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def insert_and_get_id(sql: str, params: Optional[Sequence[Any]] = None) -> int:
    """Insert row and return auto-generated ID."""
    cursor = execute_sql(sql, params)
    row_id = cursor.lastrowid
    cursor.close()
    return row_id


def count_rows(table: str, where: str = "1=1", params: Optional[Sequence[Any]] = None) -> int:
    """Count rows in table matching condition."""
    result = query_one(f"SELECT COUNT(*) as count FROM {table} WHERE {where}", params)
    return result["count"] if result else 0
