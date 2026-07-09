import requests
from .base import BaseAdapter, RawJob
from utils import clean_html


class KulaAdapter(BaseAdapter):
    """Confirmed schema from a live sample:
    {"data": [{"id","title","ats_job": {"job_description","ats_department":
    {"name"},"offices":[{"location"}]}}]}
    No direct apply URL or posted date in this response, so both fall back
    to safe defaults.
    """

    def fetch_jobs(self, company: dict):
        url = company["API Endpoint"]
        resp = requests.get(url, headers=self.headers(company), timeout=15)
        resp.raise_for_status()
        return self.parse(resp.json(), company)

    def parse(self, data: dict, company: dict):
        raw_list = data.get("data", [])
        jobs = []
        for j in raw_list:
            ats_job = j.get("ats_job") or {}
            dept = ats_job.get("ats_department") or {}
            offices = ats_job.get("offices") or []
            location_str = offices[0].get("location") if offices else None
            jobs.append(RawJob(
                external_id=str(j.get("id")),
                title=j.get("title", ""),
                location=location_str,
                department=dept.get("name"),
                url=company.get("Careers URL"),
                posted_date=None,
                description=clean_html(ats_job.get("job_description")),
            ))
        return jobs
