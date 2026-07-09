import requests
from .base import BaseAdapter, RawJob


class LeverAdapter(BaseAdapter):
    def fetch_jobs(self, company: dict):
        url = company["API Endpoint"]
        resp = requests.get(url, headers=self.headers(company), timeout=15)
        resp.raise_for_status()
        data = resp.json()  # Lever returns a bare list
        jobs = []
        for j in data:
            categories = j.get("categories", {}) or {}
            jobs.append(RawJob(
                external_id=str(j.get("id")),
                title=j.get("text", ""),
                location=categories.get("location"),
                department=categories.get("team") or categories.get("department"),
                url=j.get("hostedUrl") or j.get("applyUrl"),
                posted_date=str(j.get("createdAt")) if j.get("createdAt") else None,
                description=j.get("descriptionPlain") or j.get("description"),
            ))
        return jobs
