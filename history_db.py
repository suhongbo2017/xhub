"""Minimal URL History — SQLite-backed key-value store.

Public API (the only seam tests exercise):
    save_url(url)         → int | dedup by exact URL string
    save_download(record) → int | append download result metadata
    get_all()             → list[dict] sorted newest-first
    clear()               → delete everything
"""
import os
import sqlite3
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _init():
    """Create table with migration support."""
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS urls (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE NOT NULL,
                timestamp   TEXT NOT NULL,
                title       TEXT DEFAULT '',
                duration    INTEGER DEFAULT 0,
                quality     TEXT DEFAULT 'unknown',
                is_m3u8     BOOLEAN DEFAULT 0,
                source_url  TEXT DEFAULT ''
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


def save_download(record: dict) -> int:
    """Append a download result record.

    ``record`` should have: url, title, duration, quality, is_m3u8, source_url.
    """
    m3u8_flag = 1 if record.get("is_m3u8", False) else 0
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO urls (url, timestamp, title, duration, quality, is_m3u8, source_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                record.get("url", ""),
                datetime.datetime.now().isoformat(),
                record.get("title", ""),
                record.get("duration", 0),
                record.get("quality", "unknown"),
                m3u8_flag,
                record.get("source_url", ""),
            ),
        )
        return cur.lastrowid


def get_all() -> list[dict]:
    """Return all records ordered newest-first with normalized fields."""
    rows = _conn().execute(
        "SELECT id, url, timestamp, title, duration, quality, is_m3u8, source_url "
        "FROM urls ORDER BY id DESC"
    ).fetchall()
    return [
        {
            "id": r[0],
            "url": r[1],
            "timestamp": r[2],
            "status": "ok",
            "title": r[3] or "",
            "duration": r[4] or 0,
            "quality": r[5] or "unknown",
            "is_m3u8": bool(int(r[6])) if r[6] is not None else False,
            "source_url": r[7] or "",
        }
        for r in rows
    ]


def clear():
    """Delete all history records."""
    with _conn() as c:
        c.execute("DELETE FROM urls")


_init()
