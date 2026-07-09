"""
Base interface all ATS adapters implement.

Design: every adapter's job is ONLY to turn one ATS's weird JSON shape into a
list of RawJob objects. Nothing else in the pipeline (storage, filtering,
notifying) needs to know anything ATS-specific. This means adding a new ATS
later is just "write one new file that returns RawJob objects" -- everything
downstream keeps working unchanged.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RawJob:
    external_id: str          # unique ID from the ATS (for dedup)
    title: str
    location: Optional[str]
    department: Optional[str]
    url: str
    posted_date: Optional[str]
    description: Optional[str] = None
    company: Optional[str] = None   # filled in by main.py after fetch
    min_experience: Optional[float] = None   # structured "years required" if the ATS exposes it
    experience_text: Optional[str] = None    # raw experience string, e.g. Keka's "5+ Years"


class BaseAdapter:
    """Every adapter implements fetch_jobs(company_row) -> List[RawJob]."""

    def fetch_jobs(self, company: dict) -> List[RawJob]:
        raise NotImplementedError

    def headers(self, company: dict) -> dict:
        """Parse the 'Special Headers' column (format: 'Key: Value, Key2: Value2')."""
        raw = company.get("Special Headers") or company.get("Special Header")
        h = {}
        if raw:
            for pair in str(raw).split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    h[k.strip()] = v.strip()
        return h
