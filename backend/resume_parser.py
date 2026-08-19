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
    "php", "laravel", "go", "golang", "rust", "blockchain", "cybersecurity",
]

TITLE_PATTERNS = [
    r"(?:^|\n)\s*((?:senior|sr\.?|lead|principal|staff|junior|jr\.?|associate|head of)\s+)?"
    r"([a-zA-Z][a-zA-Z\s/&-]{2,40}(?:engineer|developer|manager|analyst|designer|architect|consultant|specialist|director|lead))",
    r"(?:^|\n)\s*([A-Z][a-zA-Z\s/&-]{2,40}(?:Engineer|Developer|Manager|Analyst|Designer|Architect|Consultant|Specialist|Director|Lead))",
]

EXPERIENCE_PATTERN = re.compile(
    r"(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
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


def extract_skills(text: str) -> List[str]:
    lower = text.lower()
    found = []
    for skill in SKILL_DICTIONARY:
        if skill in lower:
            found.append(skill)
    return sorted(set(found))


def extract_titles(text: str) -> List[str]:
    titles = []
    for pattern in TITLE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            groups = [g for g in match.groups() if g]
            title = " ".join(groups).strip()
            if 3 < len(title) < 60:
                titles.append(title.title())
    if not titles:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:15]:
            if any(kw in line.lower() for kw in ["engineer", "developer", "manager", "analyst", "designer"]):
                titles.append(line[:60])
                break
    return list(dict.fromkeys(titles))[:5]


def extract_years_experience(text: str) -> int:
    matches = EXPERIENCE_PATTERN.findall(text)
    if matches:
        return max(int(m) for m in matches)
    return 0


def parse_resume(path: Path) -> Tuple[str, List[str], List[str], int]:
    raw = extract_text(path)
    skills = extract_skills(raw)
    titles = extract_titles(raw)
    years = extract_years_experience(raw)
    return raw, skills, titles, years


def to_json_list(items: List[str]) -> str:
    return json.dumps(items)
