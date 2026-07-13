"""
Entry point. Run with:  python main.py [path_to_sheet.xlsx] [--debug]

--debug prints the raw JSON response for each company instead of running
the full pipeline -- use this the first time you point the script at a new
ATS to confirm/adjust field names in that adapter.
"""

import sys
import openpyxl
from dotenv import load_dotenv

from adapters.ashby import AshbyAdapter
from adapters.keka import KekaAdapter
from adapters.lever import LeverAdapter
from adapters.workable import WorkableAdapter
from adapters.careerpuck import CareerPuckAdapter
from adapters.kula import KulaAdapter
from adapters.unberry import UnberryAdapter

import storage
from filters.keyword_filter import passes_keyword_filter
from filters.location_filter import passes_location_filter
from filters.llm_classifier import classify_job
from notifier import send_telegram_alert

load_dotenv()

# Registry mapping the "ATS Provider" column value -> adapter instance.
# Adding a new ATS later = write adapters/newats.py, add one line here.
ADAPTER_REGISTRY = {
    "ashby": AshbyAdapter(),
    "keka": KekaAdapter(),
    "lever": LeverAdapter(),
    "workable": WorkableAdapter(),
    "careerpuck": CareerPuckAdapter(),
    "kula": KulaAdapter(),
    "unberry": UnberryAdapter(),
}

READY_STATUSES = {"🟢 working", "working", "🟢", "endpoint verified"}


def load_companies(xlsx_path: str) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h).strip() if h else "" for h in rows[0]]
    companies = []
    for row in rows[1:]:
        if not any(row):
            continue
        record = dict(zip(headers, row))
        if record.get("Company") and record.get("API Endpoint"):
            companies.append(record)
    return companies


def run_debug(companies: list[dict]):
    for company in companies:
        provider_key = str(company.get("ATS Provider", "")).strip().lower()
        adapter = ADAPTER_REGISTRY.get(provider_key)
        if not adapter:
            continue
        print(f"\n=== {company['Company']} ({provider_key}) ===")
        try:
            jobs = adapter.fetch_jobs(company)
            print(f"Parsed {len(jobs)} jobs. First job: {jobs[0] if jobs else 'none'}")
        except Exception as e:
            print(f"FAILED: {e}")


def run_pipeline(companies: list[dict]):
    conn = storage.get_conn()
    total_new, total_alerted = 0, 0

    for company in companies:
        name = company["Company"]
        provider_key = str(company.get("ATS Provider", "")).strip().lower()
        adapter = ADAPTER_REGISTRY.get(provider_key)
        if not adapter:
            continue  # not yet implemented (e.g. Workday, Gem, or Manual Only)

        try:
            jobs = adapter.fetch_jobs(company)
        except Exception as e:
            print(f"[{name}] fetch failed: {e}")
            continue

        for job in jobs:
            if not storage.is_new(conn, name, job.external_id):
                continue
            total_new += 1

            if not passes_keyword_filter(job):
                storage.mark_seen(conn, name, job.external_id, job.title, job.url)
                continue

            if not passes_location_filter(job):
                print(f"Filtered out by location: [{name}] {job.title} -> {job.location}")
                storage.mark_seen(conn, name, job.external_id, job.title, job.url)
                continue

            result = classify_job(job.title, job.description, job.location)
            is_confidently_not_entry_level = (
                result.get("is_entry_level") is False and result.get("confidence") == "high"
            )
            if not is_confidently_not_entry_level:
                if send_telegram_alert(name, job.title, job.url, result.get("reasoning", "")):
                    total_alerted += 1
                    print(f"ALERTED: [{name}] {job.title}")
                    storage.mark_seen(conn, name, job.external_id, job.title, job.url)
                else:
                    print(f"Alert failed, will retry next run: [{name}] {job.title}")
                    continue
            else:
                print(f"Filtered out: [{name}] {job.title} -> {result.get('reasoning')}")
                storage.mark_seen(conn, name, job.external_id, job.title, job.url)

    print(f"\nDone. {total_new} new postings seen, {total_alerted} alerts sent.")


if __name__ == "__main__":
    xlsx_path = "Startup_ATS_DB.xlsx"
    debug = False
    for arg in sys.argv[1:]:
        if arg == "--debug":
            debug = True
        else:
            xlsx_path = arg

    companies = load_companies(xlsx_path)
    print(f"Loaded {len(companies)} companies with endpoints from {xlsx_path}")

    if debug:
        run_debug(companies)
    else:
        run_pipeline(companies)
