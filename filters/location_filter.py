"""
Deterministic location gate.

Goal: alert only for India-based roles, plus remote/global roles even when
they are outside India.
"""

from utils import contains_any_keyword


REMOTE_KEYWORDS = [
    "remote", "work from home", "wfh", "anywhere", "global",
]

INDIA_KEYWORDS = [
    "india", "ind", "bengaluru", "bangalore", "mumbai", "pune", "delhi",
    "new delhi", "gurugram", "gurgaon", "noida", "hyderabad", "chennai",
    "kolkata", "ahmedabad", "jaipur", "lucknow", "indore", "coimbatore",
    "kochi", "kerala", "tamil nadu", "karnataka", "maharashtra",
    "haryana", "uttar pradesh", "telangana",
]

NON_INDIA_KEYWORDS = [
    "united states", "usa", "u.s.", "us ", "san francisco", "new york",
    "california", "london", "united kingdom", "uk ", "singapore",
    "china", "shenzhen", "shanghai", "hangzhou", "hong kong", "dubai",
    "uae", "europe", "latam", "mexico", "indonesia", "vietnam",
    "philippines", "malaysia", "australia", "canada",
]

GENERIC_LOCATION_VALUES = {"", "none", "null", "on_site", "onsite", "on-site", "hybrid"}


def passes_location_filter(job) -> bool:
    """Allow India roles and remote/global roles.

    Reject roles that are clearly outside India unless they are explicitly
    remote. Unknown/generic location values are rejected to keep alerts
    geographically focused.
    """
    location = str(job.location or "").strip()
    title = str(job.title or "")
    description = str(job.description or "")

    location_text = location.lower()
    combined_text = f"{title} {location} {description[:500]}".lower()

    if contains_any_keyword(combined_text, REMOTE_KEYWORDS):
        return True

    if contains_any_keyword(combined_text, INDIA_KEYWORDS):
        return True

    if contains_any_keyword(combined_text, NON_INDIA_KEYWORDS):
        return False

    if location_text in GENERIC_LOCATION_VALUES:
        return False

    return False
