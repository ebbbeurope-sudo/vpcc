import sqlite3
import threading
from contextlib import contextmanager

from .config import DB_PATH

_lock = threading.Lock()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS binding_codes (
                code TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                token TEXT NOT NULL,
                last_seen INTEGER,
                online INTEGER DEFAULT 0
            )
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_code(code: str, user_id: int, created_at: int):
    with _lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM binding_codes WHERE user_id = ?", (user_id,))
            conn.execute(
                "INSERT INTO binding_codes (code, user_id, created_at) VALUES (?, ?, ?)",
                (code, user_id, created_at),
            )


def get_code_user(code: str) -> sqlite3.Row:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM binding_codes WHERE code = ?", (code,)
        ).fetchone()


def delete_code(code: str):
    with _lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM binding_codes WHERE code = ?", (code,))


def user_pc_count(user_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM pcs WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["c"]


def add_pc(user_id: int, name: str, token: str) -> int:
    with _lock:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO pcs (user_id, name, token) VALUES (?, ?, ?)",
                (user_id, name, token),
            )
    return cur.lastrowid


def get_pc_by_token(token: str) -> sqlite3.Row:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM pcs WHERE token = ?", (token,)).fetchone()


def get_user_pcs(user_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM pcs WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()