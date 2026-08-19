"""Optional OpenAI enrichment for resume parsing and job relevance.

Set OPENAI_API_KEY in the environment to enable. Without it, heuristic
parsing/scoring continues to work.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Tuple

import httpx

from config import settings

logger = logging.getLogger(__name__)


def openai_enabled() -> bool:
    return bool(getattr(settings, "openai_api_key", "") or "")


async def _chat_json(system: str, user_content: str, timeout: float = 60.0) -> Optional[dict]:
    if not openai_enabled():
        return None
    prompt = {
        "model": settings.openai_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=prompt,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception:
        logger.exception("OpenAI chat request failed")
        return None


async def enrich_resume_with_llm(raw_text: str) -> Optional[dict]:
    """Return skills, titles, years, search_query, linkedin_titles or None."""
    if not openai_enabled() or not raw_text.strip():
        return None

    data = await _chat_json(
        (
            "Extract a job-search profile from a resume. "
            "Return JSON with keys: "
            "skills (array of strings), "
            "titles (array of 1-3 target job titles for display), "
            "linkedin_titles (array of 1-3 short LinkedIn job-search title strings, no fluff), "
            "years_experience (integer), "
            "search_query (short job-board search string for Adzuna/JSearch, "
            "focused on senior role titles, no junior/entry roles)."
        ),
        raw_text[:12000],
        timeout=90.0,
    )
    if not data:
        return None

    titles = [str(t) for t in data.get("titles", [])][:5]
    linkedin_titles = [str(t) for t in data.get("linkedin_titles", [])][:3]
    if not linkedin_titles:
        linkedin_titles = titles[:3]

    return {
        "skills": [str(s).lower() for s in data.get("skills", [])][:25],
        "titles": titles or linkedin_titles,
        "linkedin_titles": linkedin_titles,
        "years_experience": int(data.get("years_experience") or 0),
        "search_query": str(data.get("search_query") or "").strip(),
    }


async def score_job_with_llm(
    resume_summary: str,
    job_title: str,
    job_description: str,
) -> Optional[Tuple[float, str]]:
    """Return (0-100 score, short fit reason) or None if unavailable."""
    data = await _chat_json(
        (
            "Score how well a job matches a candidate. "
            'Return JSON {"score": number 0-100, "reason": "1-2 short sentences"}. '
            "Explain why it fits or why it does not. "
            "Penalize junior/unrelated roles heavily."
        ),
        json.dumps(
            {
                "candidate": resume_summary[:4000],
                "job_title": job_title,
                "job_description": job_description[:3000],
            }
        ),
        timeout=30.0,
    )
    if not data:
        return None
    try:
        score = float(data.get("score", 0))
        reason = str(data.get("reason") or "").strip()[:500]
        return max(0.0, min(100.0, score)), reason
    except (TypeError, ValueError):
        return None


async def draft_cover_letter(
    candidate_name: str,
    resume_summary: str,
    job_title: str,
    company: str,
    job_description: str,
) -> Optional[str]:
    """Return a 200-350 word cover letter draft, or None."""
    data = await _chat_json(
        (
            "Write a tailored cover letter draft for this job application. "
            'Return JSON {"text": "..."}. '
            "Length 200-350 words. Professional, specific, no placeholders like [Your Name]. "
            "Use the candidate name provided. Do not invent employers or degrees not in the resume."
        ),
        json.dumps(
            {
                "candidate_name": candidate_name,
                "resume": resume_summary[:5000],
                "job_title": job_title,
                "company": company or "the company",
                "job_description": job_description[:3500],
            }
        ),
        timeout=60.0,
    )
    if not data:
        return None
    text = str(data.get("text") or "").strip()
    return text or None


async def analyze_skill_gaps_llm(
    skills: List[str],
    titles: List[str],
    job_snippets: List[dict],
) -> Optional[dict]:
    """Return missing_skills, suggested_skills, notes or None."""
    data = await _chat_json(
        (
            "Compare a candidate profile to target job postings. "
            "Return JSON with keys: "
            "missing_skills (array of skills frequently required but missing from the resume), "
            "suggested_skills (array of high-value skills to learn next), "
            "notes (2-4 sentences summarizing gaps)."
        ),
        json.dumps(
            {
                "skills": skills[:40],
                "titles": titles[:5],
                "jobs": job_snippets[:15],
            }
        ),
        timeout=60.0,
    )
    if not data:
        return None
    return {
        "missing_skills": [str(s) for s in data.get("missing_skills", [])][:20],
        "suggested_skills": [str(s) for s in data.get("suggested_skills", [])][:15],
        "notes": str(data.get("notes") or "").strip()[:1000],
    }
