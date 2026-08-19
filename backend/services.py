import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from job_fetcher import (
    build_search_keywords,
    fetch_adzuna_jobs,
    fetch_apify_linkedin_jobs,
    fetch_jsearch_jobs,
)
from locations import DEFAULT_LOCATIONS_JSON, parse_locations
from config import settings
from llm import openai_enabled, score_job_with_llm
from matcher import compute_score, label_from_score
from models import Job, JobMatch, Resume, SearchProfile, User
from search_query import filter_skills

logger = logging.getLogger(__name__)


def clear_all_jobs(db: Session) -> None:
    """Remove stale listings so a new resume doesn't keep old tech jobs."""
    db.query(JobMatch).delete()
    db.query(Job).delete()
    db.commit()


def _get_or_create_search_profile(db: Session, user: User) -> SearchProfile:
    profile = db.query(SearchProfile).filter(SearchProfile.user_id == user.id).first()
    if not profile:
        profile = SearchProfile(user_id=user.id, locations_json=DEFAULT_LOCATIONS_JSON)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def upsert_job(db: Session, data: dict) -> Job:
    job = (
        db.query(Job)
        .filter(Job.external_id == data["external_id"], Job.source == data["source"])
        .first()
    )
    if job:
        job.title = data["title"]
        job.company = data.get("company", "")
        job.location = data.get("location", "")
        job.description = data.get("description", "")
        job.url = data.get("url", "")
        job.fetched_at = datetime.utcnow()
    else:
        job = Job(**data)
        db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _resume_summary(resume: Resume, skills: List[str], titles: List[str]) -> str:
    return (
        f"Titles: {', '.join(titles)}\n"
        f"Skills: {', '.join(skills)}\n"
        f"Years experience: {resume.years_experience}\n"
        f"Resume excerpt:\n{(resume.raw_text or '')[:3000]}"
    )


async def match_jobs_for_user(db: Session, user: User) -> int:
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if not resume:
        return 0

    skills = filter_skills(json.loads(resume.skills_json or "[]"))
    titles = json.loads(resume.titles_json or "[]")
    jobs = db.query(Job).all()
    summary = _resume_summary(resume, skills, titles)

    # Heuristic pass first
    candidates: List[tuple] = []  # (job, heuristic_score, label)
    for job in jobs:
        score, label = compute_score(
            skills, titles, resume.years_experience, job.title, job.description
        )
        if score < settings.min_job_score and label == "weak":
            existing = (
                db.query(JobMatch)
                .filter(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
                .first()
            )
            if existing and not existing.saved and not existing.applied:
                db.delete(existing)
            continue
        candidates.append((job, score, label))

    # LLM re-score top candidates (by heuristic), capped
    llm_results: dict = {}  # job_id -> (score, reason)
    if openai_enabled() and candidates:
        ranked = sorted(candidates, key=lambda x: x[1], reverse=True)
        to_score = [
            (job, h_score)
            for job, h_score, _ in ranked
            if h_score >= settings.min_job_score
        ][: settings.openai_max_score_jobs]

        sem = asyncio.Semaphore(max(1, settings.openai_score_concurrency))

        async def _score_one(job: Job, h_score: float):
            async with sem:
                result = await score_job_with_llm(summary, job.title, job.description or "")
                if result:
                    llm_results[job.id] = result

        await asyncio.gather(*[_score_one(job, h) for job, h in to_score])

    count = 0
    for job, h_score, h_label in candidates:
        fit_reason = ""
        score = h_score
        if job.id in llm_results:
            llm_score, fit_reason = llm_results[job.id]
            score = round(0.35 * h_score + 0.65 * llm_score, 1)
            label = label_from_score(score)
        else:
            label = h_label

        match = (
            db.query(JobMatch)
            .filter(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
            .first()
        )
        if match:
            match.score = score
            match.label = label
            match.fit_reason = fit_reason
            match.updated_at = datetime.utcnow()
        else:
            match = JobMatch(
                user_id=user.id,
                job_id=job.id,
                score=score,
                label=label,
                fit_reason=fit_reason,
            )
            db.add(match)
        count += 1
    db.commit()
    return count


async def refresh_jobs_for_user(db: Session, user: User) -> tuple:
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    profile = _get_or_create_search_profile(db, user)
    skills = filter_skills(json.loads(resume.skills_json) if resume else [])
    titles = json.loads(resume.titles_json) if resume else []
    extra = profile.extra_keywords
    if resume and getattr(resume, "search_query", ""):
        keywords = resume.search_query
        if extra:
            keywords = f"{keywords} {extra}".strip()
    else:
        keywords = build_search_keywords(skills, titles, extra)
    locations = parse_locations(profile.locations_json, profile.location, profile.country)
    logger.info("Job search keywords for user %s: %s", user.id, keywords)

    clear_all_jobs(db)

    all_fetched = []
    cities = [loc["city"] for loc in locations]
    for loc in locations:
        adzuna = await fetch_adzuna_jobs(keywords, loc["city"], loc["country"])
        jsearch = await fetch_jsearch_jobs(keywords, loc["city"])
        all_fetched.extend(adzuna + jsearch)

    apify_jobs = await fetch_apify_linkedin_jobs(titles, keywords, cities)
    all_fetched.extend(apify_jobs)

    seen = set()
    unique = []
    for item in all_fetched:
        key = (item["external_id"], item["source"])
        if key not in seen and item.get("title"):
            seen.add(key)
            unique.append(item)

    for data in unique:
        upsert_job(db, data)

    matched = await match_jobs_for_user(db, user)
    return len(unique), matched


async def refresh_all_jobs(db: Session) -> tuple:
    users = db.query(User).all()
    all_fetched = []

    for user in users:
        resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        profile = _get_or_create_search_profile(db, user)
        skills = filter_skills(json.loads(resume.skills_json) if resume else [])
        titles = json.loads(resume.titles_json) if resume else []
        extra = profile.extra_keywords
        if resume and getattr(resume, "search_query", ""):
            keywords = resume.search_query
            if extra:
                keywords = f"{keywords} {extra}".strip()
        else:
            keywords = build_search_keywords(skills, titles, extra)
        locations = parse_locations(
            profile.locations_json, profile.location, profile.country
        )
        logger.info("Job search keywords for user %s: %s", user.id, keywords)

        cities = [loc["city"] for loc in locations]
        for loc in locations:
            adzuna = await fetch_adzuna_jobs(keywords, loc["city"], loc["country"])
            jsearch = await fetch_jsearch_jobs(keywords, loc["city"])
            all_fetched.extend(adzuna + jsearch)

        apify_jobs = await fetch_apify_linkedin_jobs(titles, keywords, cities)
        all_fetched.extend(apify_jobs)

    # Replace the board so old software listings don't stick around
    clear_all_jobs(db)

    seen = set()
    unique = []
    for item in all_fetched:
        key = (item["external_id"], item["source"])
        if key not in seen and item.get("title"):
            seen.add(key)
            unique.append(item)

    for data in unique:
        upsert_job(db, data)

    match_count = 0
    for user in users:
        match_count += await match_jobs_for_user(db, user)

    return len(unique), match_count
