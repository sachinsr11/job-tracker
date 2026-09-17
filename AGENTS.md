# Job Tracker — AGENTS.md

## Run the poller
```bash
pip install -r requirements.txt
cp .env.example .env   # 5 required vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY (service_role)
python main.py                        # normal run — writes to Supabase, sends Telegram alerts
python main.py --debug                # fetch + print only: no Supabase/Telegram writes, no env vars needed — use when adding a new ATS
python main.py path/to/sheet.xlsx     # custom spreadsheet path (default: Startup_ATS_DB.xlsx)
```

## Architecture
- `main.py` reads an xlsx spreadsheet → dispatches each company row to its ATS adapter → deduplicates via Supabase → runs 3-stage filter → sends Telegram alert
- **Add a new ATS**: write `adapters/<name>.py` with a class implementing `fetch_jobs(company) -> List[RawJob]`, then add one line to `ADAPTER_REGISTRY` in `main.py`
- **Spreadsheet columns actually read**: `Company`, `ATS Provider` (lowercased = registry key), `API Endpoint`, `Careers URL` (fallback alert link), `Special Headers` (`Key: Value, Key2: Value2`, parsed by `BaseAdapter.headers()` in `adapters/base.py`)
- `READY_STATUSES` in `main.py` is dead code — the sheet's status column does NOT gate polling; any row with Company + API Endpoint is polled
- `RawJob` dataclass is in `adapters/base.py` — the shared contract between all adapters and the pipeline
- Use `utils.pick()` and `utils.find_job_list()` when reverse-engineering an unfamiliar ATS JSON shape

## Pipeline order
1. `storage.is_new()` — Supabase dedup (table: `seen_jobs`)
2. `filters/keyword_filter.py` — cheap first pass: role match + hard-exclude senior/staff/frontend/etc
3. `filters/location_filter.py` — allow India + remote, reject explicit non-India
4. `filters/llm_classifier.py` — Groq API (Llama 3.3 70B) — only called when keyword + location filters pass
5. Send Telegram alert
- Filtered-out jobs are still `mark_seen()`d — editing filter code will NOT re-alert jobs already in `seen_jobs`

## Key conventions
- **Lenient filtering**: deliberate recall-over-precision. Keyword filter tolerates false positives. LLM only suppresses alerts with `is_entry_level: false + confidence: high`.
- **No tests** — verify changes by running `python main.py --debug`.
- **CI**: GitHub Actions `.github/workflows/poll.yml` runs every 25 min (Python 3.12, pip cache). All env vars via GitHub Secrets. `workflow_dispatch:` lets you trigger manually.

## Storage note
`README.md` claims SQLite (`job_tracker.db`), but `storage.py` uses **Supabase** exclusively (`supabase.Client`, table `seen_jobs`). Trust the code, not the README — the repo-root `job_tracker.db` is an unused leftover. Requires `SUPABASE_URL` and `SUPABASE_KEY` (service_role key, not anon).

## Known constraints
- Several adapters can't extract a job-detail URL (Keka, Kula, Unberry) — they fall back to the company's careers page
- Workday, Gem, "Manual Only" companies are not yet implemented
- No formatter/linter config exists — follow existing code style manually (4-space indent, double quotes, type hints, module docstrings)
