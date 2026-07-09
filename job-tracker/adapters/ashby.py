import requests
from .base import BaseAdapter, RawJob


class AshbyAdapter(BaseAdapter):
    def fetch_jobs(self, company: dict):
        url = company["API Endpoint"]
        resp = requests.get(url, headers=self.headers(company), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for j in data.get("jobs", []):
            jobs.append(RawJob(
                external_id=str(j.get("id")),
                title=j.get("title", ""),
                location=j.get("location") or j.get("locationName"),
                department=j.get("department") or (j.get("team") or {}).get("name") if isinstance(j.get("team"), dict) else j.get("department"),
                url=j.get("jobUrl") or j.get("applyUrl") or company.get("Careers URL"),
                posted_date=j.get("publishedAt"),
                description=j.get("descriptionPlain") or j.get("descriptionHtml"),
            ))
        return jobs
