"""Minimal URL History — SQLite-backed key-value store.

Public API (the only seam tests exercise):
    save_url(url)       → id | dedup by exact URL string
    get_all()           → list[dict] sorted newest-first
    clear()             → delete everything
"""
import os
import sqlite3
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _init():
    """Create table if not exists."""
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS urls (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE NOT NULL,
                timestamp   TEXT NOT NULL
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_urls_url ON urls(url)")


# ── public API ───────────────────────────────────────────────────────────────

def save_url(url: str) -> int:
    """Insert or ignore (dedup). Returns the id."""
    ts = datetime.datetime.now().isoformat()
    with _conn() as c:
        try:
            cur = c.execute(
                "INSERT INTO urls (url, timestamp) VALUES (?, ?)",
                (url, ts),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Already saved — return existing id
            row = c.execute("SELECT id FROM urls WHERE url=?", (url,)).fetchone()
            return row[0] if row else None


def get_all() -> list[dict]:
    rows = _conn().execute(
        "SELECT id, url, timestamp FROM urls ORDER BY id DESC"
    ).fetchall()
    return [{"id": r[0], "url": r[1], "timestamp": r[2], "status": "ok"} for r in rows]


def clear():
    with _conn() as c:
        c.execute("DELETE FROM urls")


_init()
