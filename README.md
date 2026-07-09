# Job Tracker

Polls Indian startup ATS endpoints for new fresher-friendly Backend/AI
postings and pushes them to Telegram, minutes after they're published --
before they hit LinkedIn/Naukri.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY
```

Put your `Startup_ATS_DB.xlsx` in this folder (or pass its path as an arg).

## Usage

```bash
# First time on a new ATS: confirm field names before trusting output
python main.py --debug

# Normal run
python main.py
python main.py path/to/other_sheet.xlsx
```

Run on a schedule with cron (every 15-30 min) or a GitHub Actions scheduled
workflow -- this is intentionally stateless between runs except for
`job_tracker.db` (SQLite), which tracks which postings have already been
alerted on so you don't get duplicate pings.

## Architecture

```
main.py            orchestrator: reads xlsx -> dispatches by ATS -> filters -> alerts
adapters/           one file per ATS, each turns that ATS's raw JSON into RawJob objects
storage.py          SQLite dedup tracking (seen_jobs table)
filters/
  keyword_filter.py cheap first pass: role match + hard-exclude senior/staff/etc
  llm_classifier.py Groq call (only for postings that pass keyword_filter)
notifier.py         Telegram alert
```

**Why the adapter pattern:** every ATS returns differently-shaped JSON.
Rather than one tangled parser with special cases everywhere, each ATS gets
an isolated adapter implementing one method: `fetch_jobs(company) -> List[RawJob]`.
Adding ATS #9 later means writing one new file and adding one line to the
registry in `main.py` -- nothing else changes.

**Why two-stage filtering:** the keyword filter is free and kills the
majority of irrelevant postings (wrong role, obviously senior) instantly.
Only postings that survive that get an LLM call, which keeps API usage (and
cost) low even though the classifier used to catch mislabeled "fresher"
roles is doing real reasoning, not just keyword matching.

## Adding a new ATS

1. Find a company using that ATS, open DevTools -> Network -> XHR, reload
   their careers page, find the JSON request.
2. Add a row to the spreadsheet with the endpoint.
3. Write `adapters/newats.py` implementing `fetch_jobs()`, using `pick()`
   and `find_job_list()` from `utils.py` if the field names aren't obvious
   yet -- run `--debug` to see the raw response and refine.
4. Register it in `ADAPTER_REGISTRY` in `main.py`.

## Known gaps (v1)

- Workday and Gem (GraphQL) adapters aren't implemented yet -- both need
  POST request bodies captured from DevTools rather than a simple GET.
- Companies marked "Manual Only" in the sheet (no discoverable API) aren't
  covered -- that's a separate generic HTML-diff watcher, not yet built.
- Keka/Kula/Unberry don't expose a direct job-detail URL in their list
  endpoints, so alerts link to the company's careers page rather than the
  exact posting -- still enough to find and apply fast.

## Filter philosophy (lenient, not strict)

By design, this filters out only what it's fairly confident is wrong (Sales/
Marketing/HR roles, frontend/UX, or explicit senior/5+-years signals). It
does NOT require an exact "Backend" or "AI" keyword match -- any recognizably
technical role passes, per the instruction to catch anything a fresher could
plausibly apply to rather than risk missing one. The LLM step mirrors this:
an alert is only suppressed when the model is confidently saying "not
entry-level", not merely uncertain.

**Planned future extension (not built yet):** `TECH_SIGNAL_KEYWORDS` in
`filters/keyword_filter.py` is currently a hardcoded list (python, RAG, AI,
Postgres, backend, etc). The intent is to eventually replace/augment this
list with keywords auto-extracted from a resume rather than hardcoding them,
so the filter targets your specific stack automatically.
