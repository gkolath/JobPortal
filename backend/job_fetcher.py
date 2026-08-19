import asyncio
import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

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


def _parse_unix_ts(value) -> Optional[datetime]:
    try:
        if value is None:
            return None
        return datetime.utcfromtimestamp(int(value))
    except (TypeError, ValueError, OSError):
        return None


def _short_query(keywords: str, titles: List[str]) -> str:
    """Prefer a short role phrase — long board queries often return zero hits."""
    for t in titles:
        text = (t or "").strip()
        if text:
            return text[:80]
    return (keywords or "operations manager").strip()[:80]


def _text_matches(haystack: str, needles: List[str]) -> bool:
    hay = haystack.lower()
    for n in needles:
        token = (n or "").strip().lower()
        if len(token) < 3:
            continue
        if token in hay:
            return True
        # match individual significant words
        for w in re.findall(r"[a-z]{4,}", token):
            if w in hay:
                return True
    return False


async def fetch_adzuna_jobs(
    keywords: str, location: str, country: str, max_pages: int = 3
) -> List[dict]:
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
                "what": keywords[:120],
                "where": location,
                "results_per_page": 50,
                "content-type": "application/json",
            }
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                logger.exception("Adzuna fetch failed page %s country=%s", page, country)
                break

            batch = data.get("results", [])
            if not batch:
                break
            for item in batch:
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
                    "location": item.get("job_city", location) or location,
                    "description": item.get("job_description", ""),
                    "url": item.get("job_apply_link", item.get("job_link", "")),
                    "posted_at": _parse_adzuna_date(item.get("job_posted_at_datetime_utc")),
                })
    return results


async def fetch_remotive_jobs(titles: List[str], keywords: str) -> List[dict]:
    """Free Remotive remote-jobs API (no key)."""
    if not settings.remotive_enabled:
        return []
    query = _short_query(keywords, titles)
    url = f"https://remotive.com/api/remote-jobs?search={quote_plus(query)}&limit=50"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Remotive fetch failed")
        return []

    results = []
    for item in data.get("jobs", []):
        job_id = str(item.get("id") or item.get("url") or "")
        title = (item.get("title") or "").strip()
        if not job_id or not title:
            continue
        results.append({
            "external_id": job_id,
            "source": "remotive",
            "title": title,
            "company": item.get("company_name") or "",
            "location": item.get("candidate_required_location") or "Remote",
            "description": item.get("description") or "",
            "url": item.get("url") or "",
            "posted_at": _parse_adzuna_date(item.get("publication_date")),
        })
    logger.info("Remotive returned %s jobs for %r", len(results), query)
    return results


async def fetch_arbeitnow_jobs(titles: List[str], keywords: str, cities: List[str]) -> List[dict]:
    """Free Arbeitnow ATS job board API (no key) — filter by role + soft location."""
    if not settings.arbeitnow_enabled:
        return []

    needles = [t for t in titles if t][:5]
    if keywords:
        needles.append(keywords)

    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, settings.arbeitnow_max_pages + 1):
                resp = await client.get(
                    "https://www.arbeitnow.com/api/job-board-api",
                    params={"page": page},
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data") or []
                if not items:
                    break
                for item in items:
                    title = (item.get("title") or "").strip()
                    if not title:
                        continue
                    hay = " ".join(
                        [
                            title,
                            item.get("company_name") or "",
                            item.get("location") or "",
                            " ".join(item.get("tags") or []),
                            (item.get("description") or "")[:500],
                        ]
                    )
                    if needles and not _text_matches(hay, needles):
                        continue
                    loc = (item.get("location") or "").strip() or "Remote"
                    slug = item.get("slug") or item.get("url") or title
                    results.append({
                        "external_id": str(slug),
                        "source": "arbeitnow",
                        "title": title,
                        "company": item.get("company_name") or "",
                        "location": loc,
                        "description": item.get("description") or "",
                        "url": item.get("url") or "",
                        "posted_at": _parse_unix_ts(item.get("created_at")),
                    })
    except Exception:
        logger.exception("Arbeitnow fetch failed")
        return []

    logger.info("Arbeitnow matched %s jobs", len(results))
    return results[:150]


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


def _parse_apify_linkedin_job(item: dict, fallback_location: str) -> Optional[dict]:
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


def _run_apify_actor(actor_id: str, run_input: dict) -> List[dict]:
    from apify_client import ApifyClient

    client = ApifyClient(token=settings.apify_token)
    run = client.actor(actor_id).call(
        run_input=run_input,
        timeout_secs=settings.apify_timeout_secs,
    )
    if not run or run.get("status") != "SUCCEEDED":
        logger.error("Apify actor %s status=%s", actor_id, (run or {}).get("status"))
        return []
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        return []
    return [
        item
        for item in client.dataset(dataset_id).iterate_items()
        if isinstance(item, dict) and "error" not in item
    ]


def _fetch_apify_linkedin_sync(
    job_titles: List[str], locations: List[str], max_items: int
) -> List[dict]:
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
    items = _run_apify_actor(settings.apify_job_actor, run_input)
    fallback_location = locations[0] if locations else settings.default_location
    results: List[dict] = []
    for item in items:
        normalized = _parse_apify_linkedin_job(item, fallback_location)
        if normalized:
            results.append(normalized)
    return results


def _fetch_apify_indeed_sync(position: str, locations: List[str], max_items: int) -> List[dict]:
    """Run Indeed scraper once per city (actor accepts a single location)."""
    results: List[dict] = []
    for city in locations:
        run_input = {
            "position": position,
            "location": city,
            "maxItemsPerSearch": max_items,
            "parseCompanyDetails": False,
            "saveOnlyUniqueItems": True,
        }
        logger.info("Apify Indeed search position=%r location=%s", position, city)
        try:
            items = _run_apify_actor(settings.apify_indeed_actor, run_input)
        except Exception:
            logger.exception("Indeed scrape failed for %s", city)
            continue
        for item in items:
            title = (item.get("positionName") or item.get("title") or "").strip()
            job_id = str(
                item.get("id")
                or item.get("jobkey")
                or item.get("url")
                or item.get("externalApplyLink")
                or ""
            )
            if not title or not job_id:
                continue
            results.append({
                "external_id": job_id[:255],
                "source": "apify_indeed",
                "title": title,
                "company": item.get("company") or "",
                "location": item.get("location") or city,
                "description": item.get("description") or item.get("descriptionHTML") or "",
                "url": item.get("url") or item.get("externalApplyLink") or "",
                "posted_at": _parse_adzuna_date(item.get("postedAt") or item.get("postedDate")),
            })
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


async def fetch_apify_indeed_jobs(
    titles: List[str],
    keywords: str,
    locations: List[str],
) -> List[dict]:
    """Fetch Indeed jobs via Apify. Uses primary title × each city."""
    if not settings.apify_enabled or not settings.apify_indeed_enabled:
        return []
    if not settings.apify_token:
        return []

    position = _short_query(keywords, titles)
    cities = [c for c in locations if c][: settings.apify_indeed_max_cities]
    if not position or not cities:
        return []

    max_items = max(1, settings.apify_indeed_max_items)
    try:
        return await asyncio.to_thread(
            _fetch_apify_indeed_sync, position, cities, max_items
        )
    except Exception:
        logger.exception("Apify Indeed fetch failed")
        return []


COUNTRY_WHERE = {
    "in": "India",
    "ae": "United Arab Emirates",
    "sg": "Singapore",
    "gb": "United Kingdom",
    "us": "United States",
}


async def fetch_all_job_sources(
    titles: List[str],
    keywords: str,
    locations: List[dict],
) -> List[dict]:
    """Pull from Adzuna, JSearch, Remotive, Arbeitnow, LinkedIn, Indeed in parallel."""
    cities = [loc["city"] for loc in locations if loc.get("city")]
    short = _short_query(keywords, titles)

    tasks = []
    for loc in locations:
        country = (loc.get("country") or "in").lower()
        tasks.append(fetch_adzuna_jobs(short, loc["city"], country))
        # Broader country-level Adzuna search for thin city markets
        country_where = COUNTRY_WHERE.get(country, loc["city"])
        tasks.append(fetch_adzuna_jobs(short, country_where, country, max_pages=2))
        tasks.append(fetch_jsearch_jobs(short, loc["city"]))

    tasks.append(fetch_remotive_jobs(titles, keywords))
    tasks.append(fetch_arbeitnow_jobs(titles, keywords, cities))
    tasks.append(fetch_apify_linkedin_jobs(titles, keywords, cities))
    tasks.append(fetch_apify_indeed_jobs(titles, keywords, cities))

    batches = await asyncio.gather(*tasks, return_exceptions=True)
    all_fetched: List[dict] = []
    for batch in batches:
        if isinstance(batch, Exception):
            logger.exception("Job source failed: %s", batch)
            continue
        all_fetched.extend(batch)
    return all_fetched
