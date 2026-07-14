"""
Deterministic location gate.

Goal: alert for India-based roles and remote/global roles, even when the
remote role happens to be based outside India.

Lenient by design (matches this project's recall-over-precision philosophy):
if the location signal is missing, generic, or ambiguous -- e.g. Unberry's
list endpoint only exposes workplace type ("on_site"/"remote"), not an
actual city -- this ALLOWS the job through rather than rejecting it. A wrong
"allow" costs you glancing at one extra irrelevant JD; a wrong "reject"
silently costs you a real posting forever, which is the worse failure mode
per this project's stated priorities.
"""

from utils import contains_any_keyword

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "anywhere", "global"]

INDIA_KEYWORDS = [
    "india", "bengaluru", "bangalore", "mumbai", "pune", "delhi",
    "new delhi", "gurugram", "gurgaon", "noida", "hyderabad", "chennai",
    "kolkata", "ahmedabad", "jaipur", "lucknow", "indore", "coimbatore",
    "kochi", "kerala", "tamil nadu", "karnataka", "maharashtra",
    "haryana", "uttar pradesh", "telangana",
]

# Deliberately unambiguous, multi-word terms only. Bare "us"/"uk" are
# excluded on purpose -- "us" collides constantly with the pronoun ("join
# us", "reach out to us"), which would wrongly reject India-based postings
# that use it in ordinary JD copy.
NON_INDIA_KEYWORDS = [
    "united states", "usa", "u.s.a", "san francisco", "new york",
    "california", "london", "united kingdom", "singapore",
    "china", "shenzhen", "shanghai", "hangzhou", "hong kong", "dubai",
    "uae", "latam", "mexico", "indonesia", "vietnam",
    "philippines", "malaysia", "australia", "canada",
]


def passes_location_filter(job) -> bool:
    """Allow India roles, remote/global roles, and anything ambiguous.
    Only reject when there's an explicit, unambiguous non-India signal and
    nothing suggesting remote/India."""
    title = str(job.title or "")
    location = str(job.location or "")
    description = str(job.description or "")
    combined_text = f"{title} {location} {description[:500]}".lower()

    if contains_any_keyword(combined_text, REMOTE_KEYWORDS):
        return True
    if contains_any_keyword(combined_text, INDIA_KEYWORDS):
        return True
    if contains_any_keyword(combined_text, NON_INDIA_KEYWORDS):
        return False

    # No clear signal either way (e.g. Unberry only exposes a workplace
    # type, not a city) -- lean lenient rather than drop it.
    return True