import re
from typing import List

# Short tokens that often match by accident inside other words/URLs
FALSE_POSITIVE_SKILLS = {"go", "git", "r", "c", "qa", "etl", "nlp", "seo"}

ROLE_QUERY_HINTS = {
    "chief of staff": "Chief of Staff OR Operations Manager OR Strategy",
    "operations": "Operations Manager OR Head of Operations",
    "hr": "HR Manager OR Human Resources OR People Operations",
    "human resources": "HR Manager OR Human Resources",
    "strategy": "Strategy Manager OR Strategic Planning",
    "project management": "Project Manager OR Program Manager",
}


def clean_title(title: str) -> str:
    t = title.strip()
    if re.search(r"linkedin|https?://|www\.|@", t, re.I):
        return ""
    if len(t) > 80:
        return ""
    junk = ["visionary", "partnered", "managing strategic", "years of"]
    if any(j in t.lower() for j in junk):
        return ""
    return t


def primary_role_query(titles: List[str], skills: List[str], extra: str = "") -> str:
    """Build an Adzuna/JSearch query focused on role, not tech stack."""
    cleaned_titles = [clean_title(t) for t in titles]
    cleaned_titles = [t for t in cleaned_titles if t]

    primary = cleaned_titles[0].split("/")[0].strip() if cleaned_titles else ""

    # Prefer known role hints from titles/skills
    hay = " ".join(cleaned_titles + skills).lower()
    for key, query in ROLE_QUERY_HINTS.items():
        if key in hay or key in primary.lower():
            base = query
            if extra:
                return f"{base} {extra}".strip()
            return base

    safe_skills = [
        s for s in skills
        if s.lower() not in FALSE_POSITIVE_SKILLS and len(s) > 2
    ][:3]

    parts = []
    if primary:
        parts.append(primary)
    parts.extend(safe_skills)
    if extra:
        parts.append(extra)

    return " ".join(parts) if parts else "operations manager"


def filter_skills(skills: List[str]) -> List[str]:
    return [s for s in skills if s.lower() not in FALSE_POSITIVE_SKILLS]
