import asyncio
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
    from search_query import primary_role_query

    return primary_role_query(titles, skills, extra)


def _apify_job_titles(titles: List[str], keywords: str) -> List[str]:
    """Pick short LinkedIn search queries from resume titles / keywords."""
    cleaned: List[str] = []
    seen = set()
    for title in titles:
        text = (title or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text[:120])
        if len(cleaned) >= 3:
            return cleaned
    if cleaned:
        return cleaned
    phrase = (keywords or "").strip()
    if phrase:
        return [phrase[:120]]
    return []


def _normalize_apify_location(item: dict, fallback: str) -> str:
    loc = item.get("location")
    if isinstance(loc, dict):
        parsed = loc.get("parsed") or {}
        return (
            parsed.get("text")
            or loc.get("linkedinText")
            or fallback
        )
    if isinstance(loc, str) and loc.strip():
        return loc
    return fallback


def _parse_apify_job(item: dict, fallback_location: str) -> Optional[dict]:
    job_id = str(item.get("id") or "").strip()
    title = (item.get("title") or "").strip()
    if not job_id or not title:
        return None

    company = item.get("company") or {}
    company_name = ""
    if isinstance(company, dict):
        company_name = company.get("name") or ""
    elif isinstance(company, str):
        company_name = company

    apply = item.get("applyMethod") or {}
    url = (
        item.get("linkedinUrl")
        or (apply.get("companyApplyUrl") if isinstance(apply, dict) else "")
        or item.get("jobUrl")
        or item.get("url")
        or ""
    )

    return {
        "external_id": job_id,
        "source": "apify_linkedin",
        "title": title,
        "company": company_name,
        "location": _normalize_apify_location(item, fallback_location),
        "description": item.get("descriptionText") or item.get("description") or "",
        "url": url,
        "posted_at": _parse_adzuna_date(item.get("postedDate")),
    }


def _fetch_apify_linkedin_sync(
    job_titles: List[str], locations: List[str], max_items: int
) -> List[dict]:
    from apify_client import ApifyClient

    client = ApifyClient(token=settings.apify_token)
    run_input = {
        "jobTitles": job_titles,
        "locations": locations,
        "maxItems": max_items,
        "sortBy": "relevant",
        "postedLimit": settings.apify_posted_limit,
    }
    logger.info(
        "Apify LinkedIn search titles=%s locations=%s maxItems=%s",
        job_titles,
        locations,
        max_items,
    )
    run = client.actor(settings.apify_job_actor).call(
        run_input=run_input,
        timeout_secs=settings.apify_timeout_secs,
    )
    if not run:
        logger.warning("Apify actor returned no run payload")
        return []

    status = run.get("status")
    if status != "SUCCEEDED":
        logger.error("Apify actor finished with status %s", status)
        return []

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        return []

    fallback_location = locations[0] if locations else settings.default_location
    results: List[dict] = []
    for item in client.dataset(dataset_id).iterate_items():
        if not isinstance(item, dict):
            continue
        normalized = _parse_apify_job(item, fallback_location)
        if normalized:
            results.append(normalized)
    return results


async def fetch_apify_linkedin_jobs(
    titles: List[str],
    keywords: str,
    locations: List[str],
) -> List[dict]:
    """Fetch LinkedIn jobs via Apify Actor. No-ops if token is missing."""
    if not settings.apify_enabled:
        return []
    if not settings.apify_token:
        logger.warning("APIFY_TOKEN not configured — skipping LinkedIn scrape")
        return []

    job_titles = _apify_job_titles(titles, keywords)
    cities = [c for c in locations if c]
    if not job_titles or not cities:
        return []

    max_items = max(1, settings.apify_max_items)
    try:
        return await asyncio.to_thread(
            _fetch_apify_linkedin_sync, job_titles, cities, max_items
        )
    except Exception:
        logger.exception("Apify LinkedIn fetch failed")
        return []
