import re
from typing import List, Tuple


SENIORITY_KEYWORDS = {
    "junior": 1, "entry": 1, "associate": 2, "mid": 3, "senior": 4,
    "lead": 5, "principal": 6, "staff": 6, "director": 7, "head": 7,
}


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9+#.]+", text.lower()))


def title_score(resume_titles: List[str], job_title: str) -> float:
    if not resume_titles or not job_title:
        return 0.0
    job_tokens = _tokenize(job_title)
    best = 0.0
    for title in resume_titles:
        title_tokens = _tokenize(title)
        if not title_tokens:
            continue
        overlap = len(job_tokens & title_tokens) / max(len(title_tokens), 1)
        best = max(best, overlap)
    return min(best * 100, 100.0)


def skill_score(resume_skills: List[str], description: str, job_title: str) -> float:
    if not resume_skills:
        return 0.0
    haystack = f"{job_title} {description}".lower()
    matched = sum(1 for s in resume_skills if _skill_in_text(s, haystack))
    return min((matched / len(resume_skills)) * 100, 100.0)


def _skill_in_text(skill: str, text: str) -> bool:
    if " " in skill or "+" in skill or "/" in skill:
        return skill in text
    return bool(re.search(rf"\b{re.escape(skill)}\b", text))


def seniority_score(years: int, job_title: str, description: str) -> float:
    text = f"{job_title} {description}".lower()
    job_level = 3
    for kw, level in SENIORITY_KEYWORDS.items():
        if kw in text:
            job_level = level
    if years <= 2:
        user_level = 2
    elif years <= 5:
        user_level = 3
    elif years <= 8:
        user_level = 4
    else:
        user_level = 5
    diff = abs(job_level - user_level)
    return max(0.0, 100.0 - diff * 25)


TECH_JOB_MARKERS = (
    "software engineer", "software developer", "full stack", "fullstack",
    "backend", "frontend", "devops", "sde", "java developer", "python developer",
    "react developer", "data engineer", "ml engineer",
)

OPS_HR_MARKERS = (
    "chief of staff", "operations", "human resources", " hr ", "people ops",
    "strategy", "program manager", "project manager", "business partner",
)


def _resume_is_ops_hr(skills: List[str], titles: List[str]) -> bool:
    hay = " ".join(titles + skills).lower()
    return any(m in hay for m in OPS_HR_MARKERS)


def _job_is_pure_tech(job_title: str) -> bool:
    lower = job_title.lower()
    return any(m in lower for m in TECH_JOB_MARKERS)


def compute_score(
    resume_skills: List[str],
    resume_titles: List[str],
    years_experience: int,
    job_title: str,
    description: str,
) -> Tuple[float, str]:
    t = title_score(resume_titles, job_title)
    s = skill_score(resume_skills, description, job_title)
    e = seniority_score(years_experience, job_title, description)
    score = 0.35 * t + 0.45 * s + 0.20 * e

    # Demote pure software roles when resume is HR/ops/strategy
    if _resume_is_ops_hr(resume_skills, resume_titles) and _job_is_pure_tech(job_title):
        score *= 0.25

    score = round(score, 1)

    if score >= 75:
        label = "close"
    elif score >= 55:
        label = "good"
    else:
        label = "weak"
    return score, label
