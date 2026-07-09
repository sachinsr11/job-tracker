"""
Shared helpers used across adapters.

pick(): different ATS platforms name the same concept differently
  (title / jobTitle / positionName). Rather than writing brittle code that
  breaks the moment a field name is slightly off, we try a list of candidate
  keys and take whichever exists.

find_job_list(): for ATS platforms we haven't hardcoded a parser for yet,
  this walks an unknown JSON blob and heuristically finds the list of job
  postings inside it (looks for a list of dicts where most dicts have a
  "title"-ish key). Useful as a fallback / first pass when reverse-engineering
  a brand new ATS -- run this first to see what it finds, then hardcode a
  proper adapter once you know the real shape.
"""

import re
import html as html_module
from typing import Any, List, Optional

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:-|to)?\s*\d*\s*\+?\s*years?", re.IGNORECASE)


def clean_html(raw: Optional[str]) -> str:
    """Strip HTML tags and decode entities so job descriptions are plain text
    for keyword matching / LLM prompts. Handles both raw HTML (Keka, Kula)
    and double-entity-encoded HTML (CareerPuck uses &lt;p&gt; etc)."""
    if not raw:
        return ""
    unescaped = html_module.unescape(raw)
    no_tags = _TAG_RE.sub(" ", unescaped)
    return _WHITESPACE_RE.sub(" ", no_tags).strip()


def extract_min_years(text: str) -> Optional[int]:
    """Best-effort: find the smallest 'N years' style number mentioned in text.
    Catches '5+ years', '3-5 years', '1 to 3 years' etc. Not perfect, but a
    useful secondary signal alongside any structured experience field."""
    if not text:
        return None
    nums = [int(m) for m in _YEARS_RE.findall(text)]
    return min(nums) if nums else None


def contains_keyword(text: str, keyword: str) -> bool:
    """Word-boundary keyword match. Needed for short tokens like 'ai' or 'ml'
    where plain substring matching would false-positive inside words like
    'maintain' or 'html'."""
    pattern = r"(?<![a-zA-Z])" + re.escape(keyword) + r"(?![a-zA-Z])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def contains_any_keyword(text: str, keywords: List[str]) -> bool:
    return any(contains_keyword(text, kw) for kw in keywords)


def pick(d: dict, keys: List[str], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


TITLE_HINTS = ("title", "jobtitle", "name", "positionname", "position")


def _looks_like_job(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    keys_lower = {k.lower() for k in d.keys()}
    return any(hint in k for k in keys_lower for hint in TITLE_HINTS)


def find_job_list(obj: Any) -> Optional[List[dict]]:
    """Recursively search obj for the most likely list of job postings."""
    if isinstance(obj, list):
        if obj and all(_looks_like_job(item) for item in obj[:3]):
            return obj
        # search inside list items too
        for item in obj:
            found = find_job_list(item)
            if found:
                return found
    elif isinstance(obj, dict):
        for v in obj.values():
            found = find_job_list(v)
            if found:
                return found
    return None
