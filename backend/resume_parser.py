import json
import re
from pathlib import Path
from typing import List, Tuple

import fitz  # pymupdf
from docx import Document

SKILL_DICTIONARY = [
    "python", "java", "javascript", "typescript", "react", "node", "nodejs", "angular",
    "vue", "fastapi", "django", "flask", "spring", "sql", "postgresql", "mysql", "mongodb",
    "redis", "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "git",
    "linux", "agile", "scrum", "product management", "project management", "data analysis",
    "machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "computer vision",
    "excel", "power bi", "tableau", "salesforce", "marketing", "seo", "content writing",
    "communication", "leadership", "stakeholder management", "business analysis",
    "figma", "ui/ux", "html", "css", "tailwind", "next.js", "graphql", "rest api",
    "microservices", "kafka", "spark", "hadoop", "etl", "devops", "selenium", "testing",
    "qa", "android", "ios", "swift", "kotlin", "c++", "c#", ".net", "ruby", "rails",
    "php", "laravel", "golang", "rust", "blockchain", "cybersecurity",
    "chief of staff", "operations", "strategy", "strategic planning", "program management",
    "change management", "executive support", "business development", "partnerships",
    "venture capital", "private equity", "consulting", "mba", "financial modeling",
    "budgeting", "forecasting", "okrs", "kpi", "people management", "hiring",
    "human resources", "hr", "recruitment", "talent acquisition", "employee relations",
    "payroll", "onboarding", "workforce planning", "organizational development",
]

TITLE_KEYWORDS = [
    "chief of staff", "head of", "director", "vice president", "vp ", "manager",
    "engineer", "developer", "analyst", "consultant", "lead", "architect", "designer",
    "strategist", "coordinator", "specialist", "officer", "president", "founder",
]

EXPERIENCE_PATTERNS = [
    re.compile(
        r"(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:with|over|more than|nearly|about)\s+(\d{1,2})\+?\s*(?:years?|yrs?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:in|of)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{1,2})\+\s*(?:years?|yrs?)",
        re.IGNORECASE,
    ),
]
DATE_RANGE_PATTERN = re.compile(
    r"(?:19|20)\d{2}\s*[-–—]\s*(?:19|20)\d{2}|"
    r"(?:19|20)\d{2}\s*[-–—]\s*(?:present|current|now)",
    re.IGNORECASE,
)


def _extract_text_from_pdf(path: Path) -> str:
    doc = fitz.open(path)
    parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(parts)


def _extract_text_from_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(path)
    if suffix in (".docx", ".doc"):
        return _extract_text_from_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _skill_in_text(skill: str, text: str) -> bool:
    if " " in skill or "+" in skill or "/" in skill:
        return skill in text
    return bool(re.search(rf"\b{re.escape(skill)}\b", text))


def extract_skills(text: str) -> List[str]:
    from search_query import FALSE_POSITIVE_SKILLS, filter_skills

    lower = text.lower()
    found = []
    for skill in sorted(SKILL_DICTIONARY, key=len, reverse=True):
        if skill in FALSE_POSITIVE_SKILLS:
            continue
        if _skill_in_text(skill, lower):
            found.append(skill)
    return sorted(set(filter_skills(found)))


def _is_junk_title(title: str) -> bool:
    lower = title.lower()
    junk_phrases = ["managing", "partnered", "cross-functional", "multi-venture", "strategic alignment"]
    return any(p in lower for p in junk_phrases)


def extract_titles(text: str) -> List[str]:
    titles = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line in lines[:12]:
        clean = line.strip("•|- ")
        if re.search(r"@|https?://|www\.|linkedin", clean, re.I):
            continue
        if len(clean) > 70 or "years of" in clean.lower() or "visionary" in clean.lower():
            continue
        if 4 < len(clean) < 70:
            lower = clean.lower()
            if any(kw in lower for kw in TITLE_KEYWORDS):
                titles.append(clean.title() if clean.isupper() else clean)

    for line in lines[:8]:
        if "/" in line and len(line) < 70 and not re.search(r"linkedin|https?://", line, re.I):
            titles.append(line.strip())

    if not titles:
        for line in lines[:15]:
            if any(kw in line.lower() for kw in TITLE_KEYWORDS) and len(line) < 70:
                if not re.search(r"linkedin|https?://", line, re.I):
                    titles.append(line[:70])
                    break

    deduped = []
    for t in titles:
        if not _is_junk_title(t) and t not in deduped:
            deduped.append(t)
    return deduped[:5]


def extract_years_experience(text: str) -> int:
    found_years: List[int] = []
    for pattern in EXPERIENCE_PATTERNS:
        for m in pattern.findall(text):
            try:
                found_years.append(int(m))
            except ValueError:
                continue
    if found_years:
        # Cap at a realistic career length
        return min(max(found_years), 40)

    year_vals = set()
    for m in DATE_RANGE_PATTERN.finditer(text):
        chunk = m.group(0)
        for y in re.findall(r"(?:19|20)\d{2}", chunk):
            year_vals.add(int(y))

    if len(year_vals) >= 2:
        span = max(year_vals) - min(year_vals)
        return min(max(span, 0), 40)
    return 0


async def parse_resume_async(path: Path) -> Tuple[str, List[str], List[str], int, str]:
    """Parse resume; optionally enrich with OpenAI. Returns search_query hint."""
    raw = extract_text(path)
    skills = extract_skills(raw)
    titles = extract_titles(raw)
    years = extract_years_experience(raw)
    search_query = ""

    from llm import enrich_resume_with_llm

    enriched = await enrich_resume_with_llm(raw)
    if enriched:
        if enriched.get("skills"):
            skills = sorted(set(skills + enriched["skills"]))
        # Prefer LinkedIn-friendly titles when present (also used for Apify search)
        linkedin = enriched.get("linkedin_titles") or []
        if linkedin:
            titles = linkedin[:5]
        elif enriched.get("titles"):
            titles = enriched["titles"][:5]
        if enriched.get("years_experience"):
            years = max(years, enriched["years_experience"])
        search_query = enriched.get("search_query") or ""

    return raw, skills, titles, years, search_query


def parse_resume(path: Path) -> Tuple[str, List[str], List[str], int]:
    raw = extract_text(path)
    skills = extract_skills(raw)
    titles = extract_titles(raw)
    years = extract_years_experience(raw)
    return raw, skills, titles, years


def to_json_list(items: List[str]) -> str:
    return json.dumps(items)
