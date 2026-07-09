import re
import requests
from .base import BaseAdapter, RawJob
from utils import clean_html


def _parse_experience_years(experience_text):
    """Keka gives experience as a string like '5+ Years' or '0-1 Years'.
    Extract the leading number as a rough minimum-years signal."""
    if not experience_text:
        return None
    m = re.search(r"(\d+)", experience_text)
    return int(m.group(1)) if m else None


class KekaAdapter(BaseAdapter):
    """Confirmed schema from a live sample: a bare JSON array of job objects,
    each with title, description (HTML), departmentName, jobLocations (list),
    experience (string like '5+ Years'), publishedOn.
    NOTE: this endpoint doesn't expose a direct apply/job-detail URL, so we
    fall back to the company's careers page -- fine for a Telegram alert,
    just means you land on the board rather than the exact posting.
    """

    def fetch_jobs(self, company: dict):
        url = company["API Endpoint"]
        resp = requests.get(url, headers=self.headers(company), timeout=15)
        resp.raise_for_status()
        return self.parse(resp.json(), company)

    def parse(self, data, company: dict):
        raw_list = data if isinstance(data, list) else data.get("data", [])
        jobs = []
        for j in raw_list:
            locations = j.get("jobLocations") or []
            location_str = ", ".join(l.get("name", "") for l in locations if l.get("name")) or None
            experience_text = j.get("experience")
            jobs.append(RawJob(
                external_id=str(j.get("id")),
                title=j.get("title", ""),
                location=location_str,
                department=j.get("departmentName"),
                url=company.get("Careers URL"),
                posted_date=j.get("publishedOn"),
                description=clean_html(j.get("description") or j.get("excerpt")),
                min_experience=_parse_experience_years(experience_text),
                experience_text=experience_text,
            ))
        return jobs
