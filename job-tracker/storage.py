"""
Tracks which jobs we've already seen/alerted on, so re-running the poller
doesn't re-notify for the same posting. One SQLite file, zero setup needed.
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "job_tracker.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            dedup_key TEXT PRIMARY KEY,
            company TEXT,
            title TEXT,
            url TEXT,
            first_seen TEXT
        )
    """)
    conn.commit()
    return conn


def make_dedup_key(company: str, external_id: str) -> str:
    return f"{company}::{external_id}"


def is_new(conn, company: str, external_id: str) -> bool:
    key = make_dedup_key(company, external_id)
    row = conn.execute("SELECT 1 FROM seen_jobs WHERE dedup_key = ?", (key,)).fetchone()
    return row is None


def mark_seen(conn, company: str, external_id: str, title: str, url: str):
    key = make_dedup_key(company, external_id)
    conn.execute(
        "INSERT OR IGNORE INTO seen_jobs (dedup_key, company, title, url, first_seen) VALUES (?, ?, ?, ?, ?)",
        (key, company, title, url, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
