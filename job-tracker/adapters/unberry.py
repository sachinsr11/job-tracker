import requests
from .base import BaseAdapter, RawJob


class UnberryAdapter(BaseAdapter):
    """Confirmed schema from a live sample:
    {"row": [{"metadata": [{"page","hasNext",...}], "data": [{"_id","jobTitle",
    "jobFunction","jobExperienceLevel","minExperience","maxExperience",
    "publishedAt", ...}]}]}

    This endpoint returns job CARDS only -- no description text -- but it
    does give structured minExperience/maxExperience fields, which is a more
    reliable fresher-signal than parsing title text. No job-detail URL is
    present either, so alerts link to the careers page rather than the
    specific posting.
    """

    MAX_PAGES = 3

    def fetch_jobs(self, company: dict):
        base_url = company["API Endpoint"]
        jobs = []
        for page in range(1, self.MAX_PAGES + 1):
            url = base_url.replace("page=1", f"page={page}") if "page=1" in base_url else base_url
            resp = requests.get(url, headers=self.headers(company), timeout=15)
            resp.raise_for_status()
            page_jobs, has_next = self.parse(resp.json(), company)
            jobs.extend(page_jobs)
            if not page_jobs or not has_next:
                break
        return jobs

    def parse(self, payload: dict, company: dict):
        rows = payload.get("row") or []
        block = rows[0] if rows else {}
        raw_list = block.get("data", [])
        metadata = (block.get("metadata") or [{}])[0]

        jobs = []
        for j in raw_list:
            min_exp = j.get("minExperience")
            max_exp = j.get("maxExperience")
            exp_text = f"{min_exp}-{max_exp} years" if min_exp is not None else None
            jobs.append(RawJob(
                external_id=str(j.get("_id")),
                title=j.get("jobTitle", ""),
                location=j.get("jobLocationType"),
                department=j.get("jobFunction"),
                url=company.get("Careers URL"),
                posted_date=j.get("publishedAt"),
                description=None,
                min_experience=min_exp,
                experience_text=exp_text,
            ))
        return jobs, bool(metadata.get("hasNext"))
