"""
Tracks which jobs we've already seen/alerted on, so re-running the poller
doesn't re-notify for the same posting. Uses Supabase (hosted Postgres)
instead of local SQLite so state survives across ephemeral CI runners
(e.g. GitHub Actions) without needing to commit a binary db file to git.

Requires SUPABASE_URL and SUPABASE_KEY (service_role key) as env vars.
"""

import os
from datetime import datetime, timezone
from supabase import create_client, Client


def get_conn() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def make_dedup_key(company: str, external_id: str) -> str:
    return f"{company}::{external_id}"


def is_new(conn: Client, company: str, external_id: str) -> bool:
    key = make_dedup_key(company, external_id)
    resp = conn.table("seen_jobs").select("dedup_key").eq("dedup_key", key).execute()
    return len(resp.data) == 0


def mark_seen(conn: Client, company: str, external_id: str, title: str, url: str):
    key = make_dedup_key(company, external_id)
    conn.table("seen_jobs").upsert({
        "dedup_key": key,
        "company": company,
        "title": title,
        "url": url,
        "first_seen": datetime.now(timezone.utc).isoformat(),
    }).execute()