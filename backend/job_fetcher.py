import logging
from datetime import datetime
from typing import List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _parse_adzuna_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


async def fetch_adzuna_jobs(keywords: str, location: str, country: str, max_pages: int = 2) -> List[dict]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        logger.warning("Adzuna credentials not configured")
        return []

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": keywords,
                "where": location,
                "results_per_page": 20,
                "content-type": "application/json",
            }
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                logger.exception("Adzuna fetch failed page %s", page)
                break

            for item in data.get("results", []):
                company = item.get("company", {}) or {}
                loc = item.get("location", {}) or {}
                display_loc = loc.get("display_name", location)
                results.append({
                    "external_id": str(item.get("id", "")),
                    "source": "adzuna",
                    "title": item.get("title", ""),
                    "company": company.get("display_name", ""),
                    "location": display_loc,
                    "description": item.get("description", ""),
                    "url": item.get("redirect_url", ""),
                    "posted_at": _parse_adzuna_date(item.get("created")),
                })
    return results


async def fetch_jsearch_jobs(keywords: str, location: str, max_pages: int = 2) -> List[dict]:
    if not settings.rapidapi_key:
        return []

    results = []
    headers = {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            params = {"query": f"{keywords} in {location}", "page": str(page), "num_pages": "1"}
            try:
                resp = await client.get(
                    "https://jsearch.p.rapidapi.com/search",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                logger.exception("JSearch fetch failed page %s", page)
                break

            for item in data.get("data", []):
                results.append({
                    "external_id": item.get("job_id", item.get("job_link", "")),
                    "source": "jsearch",
                    "title": item.get("job_title", ""),
                    "company": item.get("employer_name", ""),
                    "location": item.get("job_city", location),
                    "description": item.get("job_description", ""),
                    "url": item.get("job_apply_link", item.get("job_link", "")),
                    "posted_at": _parse_adzuna_date(item.get("job_posted_at_datetime_utc")),
                })
    return results


def build_search_keywords(skills: List[str], titles: List[str], extra: str = "") -> str:
    parts = []
    if titles:
        parts.append(titles[0])
    if skills:
        parts.extend(skills[:5])
    if extra:
        parts.append(extra)
    return " ".join(parts) if parts else "software engineer"
