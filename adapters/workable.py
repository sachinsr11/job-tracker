import requests
from .base import BaseAdapter, RawJob


class WorkableAdapter(BaseAdapter):
    def fetch_jobs(self, company: dict):
        url = company["API Endpoint"]
        resp = requests.get(url, headers=self.headers(company), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for j in data.get("jobs", []):
            loc = j.get("location") or {}
            location_str = loc.get("location_str") if isinstance(loc, dict) else loc
            jobs.append(RawJob(
                external_id=str(j.get("id") or j.get("shortcode")),
                title=j.get("title", ""),
                location=location_str,
                department=j.get("department"),
                url=j.get("url") or j.get("application_url"),
                posted_date=j.get("published_on") or j.get("created_at"),
                description=j.get("description"),
            ))
        return jobs
