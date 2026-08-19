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


async def enrich_resume_with_llm(raw_text: str) -> Optional[dict]:
    """Return {skills, titles, years_experience, search_query} or None."""
    if not openai_enabled() or not raw_text.strip():
        return None

    prompt = {
        "model": settings.openai_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract job-search profile from a resume. "
                    "Return JSON with keys: skills (array of strings), "
                    "titles (array of 1-3 target job titles), "
                    "years_experience (integer), "
                    "search_query (short job-search string for job boards, "
                    "focused on senior role titles, no junior/entry roles)."
                ),
            },
            {
                "role": "user",
                "content": raw_text[:12000],
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
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
            data = json.loads(content)
            return {
                "skills": [str(s).lower() for s in data.get("skills", [])][:25],
                "titles": [str(t) for t in data.get("titles", [])][:5],
                "years_experience": int(data.get("years_experience") or 0),
                "search_query": str(data.get("search_query") or "").strip(),
            }
    except Exception:
        logger.exception("OpenAI resume enrichment failed")
        return None


async def score_job_with_llm(
    resume_summary: str,
    job_title: str,
    job_description: str,
) -> Optional[float]:
    """Return 0-100 relevance score, or None if unavailable."""
    if not openai_enabled():
        return None

    prompt = {
        "model": settings.openai_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Score how well a job matches a candidate. "
                    'Return JSON {"score": number 0-100}. '
                    "Penalize junior/unrelated roles heavily."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "candidate": resume_summary[:4000],
                        "job_title": job_title,
                        "job_description": job_description[:3000],
                    }
                ),
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
            data = json.loads(content)
            return float(data.get("score", 0))
    except Exception:
        logger.exception("OpenAI job scoring failed")
        return None
