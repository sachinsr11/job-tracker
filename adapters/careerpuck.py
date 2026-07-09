import requests
from .base import BaseAdapter, RawJob
from utils import clean_html


class CareerPuckAdapter(BaseAdapter):
    """Confirmed schema from a live sample (CareerPuck wraps Greenhouse data
    internally): {"jobs": [{"permalink","title","content","location",
    "departments":[{"name":...}], "applyUrl","publicUrl","postedAt", ...}]}
    Parsing is split out from fetching so it can be unit-tested against a
    saved JSON sample without hitting the network.
    """

    def fetch_jobs(self, company: dict):
        url = company["API Endpoint"]
        resp = requests.get(url, headers=self.headers(company), timeout=15)
        resp.raise_for_status()
        return self.parse(resp.json(), company)

    def parse(self, data: dict, company: dict):
        jobs = []
        for j in data.get("jobs", []):
            departments = j.get("departments") or []
            dept_name = departments[0]["name"] if departments else None
            jobs.append(RawJob(
                external_id=str(j.get("permalink")),
                title=j.get("title", ""),
                location=j.get("location"),
                department=dept_name,
                url=j.get("applyUrl") or j.get("publicUrl") or company.get("Careers URL"),
                posted_date=j.get("postedAt"),
                description=clean_html(j.get("content")),
            ))
        return jobs
