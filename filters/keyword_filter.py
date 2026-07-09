"""
Fast, free first-pass filter. Deliberately LENIENT: the goal is to never
silently drop a genuine posting, even at the cost of occasionally letting an
irrelevant one through to the Telegram alert. It only excludes when there's
a fairly confident signal the role is wrong (frontend/UX, non-tech function
like Sales/Marketing, or clearly experienced/senior).

TECH_SIGNAL_KEYWORDS is intentionally broad ("any tech fresher role except
frontend/UX", per your instructions) rather than narrowly Backend/AI-only.

Future extension point: TECH_SIGNAL_KEYWORDS is the one list meant to later
be replaced/augmented by keywords auto-extracted from a resume, instead of
being hardcoded -- not built yet, just designed so that swap is easy later.
"""

from utils import contains_any_keyword, extract_min_years

# Roles/functions that are clearly not what you're looking for, regardless
# of seniority -- checked first so they short-circuit everything else.
NON_TECH_DEPARTMENTS = {
    "sales", "marketing", "business development", "human resources", "hr",
    "finance", "legal", "customer success", "customer support",
    "recruitment", "talent acquisition", "people", "operations",
}

NON_TECH_ROLE_KEYWORDS = [
    "business development", "account executive", "key account manager",
    "channel partner", "social media", "brand manager", "bde",
    "sales executive", "sales manager", "recruiter", "talent acquisition",
]

FRONTEND_UX_EXCLUDE_KEYWORDS = [
    "frontend", "front-end", "front end", "ui/ux", "ui developer",
    "ux designer", "ui designer", "product designer", "visual designer",
]

# Broad on purpose -- matches per your "any tech fresher role, no language
# preference" instruction. Add resume-derived keywords here later.
TECH_SIGNAL_KEYWORDS = [
    "engineer", "engineering", "developer", "software", "backend",
    "back-end", "back end", "full stack", "fullstack", "sde", "sdet",
    "data", "ai", "ml", "machine learning", "rag", "llm", "python",
    "postgres", "postgresql", "devops", "sre", "site reliability",
    "platform engineer", "infrastructure", "cloud", "kubernetes",
    "qa engineer", "fde", "forward deployed", "technical",
]

TECH_DEPARTMENT_KEYWORDS = ["engineering", "technology", "product", "data"]

# Title-level hard signals of seniority that keyword text alone reveals.
# Deliberately conservative (only very explicit markers) to stay lenient.
HARD_SENIORITY_TITLE_KEYWORDS = [
    "senior", "staff", "principal", "architect", "director", "vp ",
    "head of", "sde 2", "sde ii", "sde-2", "sde 3", "sde iii", "sde-3",
    "manager",
]

MAX_ACCEPTABLE_MIN_YEARS = 2  # >= this many years required -> excluded


def passes_keyword_filter(job) -> bool:
    """job is a RawJob (or anything with .title/.description/.department/
    .min_experience/.experience_text attributes)."""
    text = f"{job.title} {job.description or ''}"
    dept = (job.department or "").lower()

    # 1. Clearly the wrong function entirely (Sales/Marketing/HR/etc.)
    if dept in NON_TECH_DEPARTMENTS or contains_any_keyword(text, NON_TECH_ROLE_KEYWORDS):
        return False

    # 2. Explicitly excluded per your preference
    if contains_any_keyword(text, FRONTEND_UX_EXCLUDE_KEYWORDS):
        return False

    # 3. Must look like *some* tech/engineering role at all
    looks_technical = contains_any_keyword(text, TECH_SIGNAL_KEYWORDS) or any(
        k in dept for k in TECH_DEPARTMENT_KEYWORDS
    )
    if not looks_technical:
        return False

    # 4. Title-level seniority markers
    if contains_any_keyword(text, HARD_SENIORITY_TITLE_KEYWORDS):
        return False

    # 5. Structured experience signal, when the ATS provides one (Keka,
    # Unberry) -- more trustworthy than free-text parsing.
    if job.min_experience is not None and job.min_experience > MAX_ACCEPTABLE_MIN_YEARS:
        return False

    # 6. Free-text "N years" mentions as a fallback signal
    min_years_mentioned = extract_min_years(text)
    if min_years_mentioned is not None and min_years_mentioned > MAX_ACCEPTABLE_MIN_YEARS:
        return False

    # Lenient default: let it through. The LLM stage (and worst case, you
    # skimming the JD) makes the final call -- better than risking a miss.
    return True
