import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from job_fetcher import build_search_keywords, fetch_adzuna_jobs, fetch_jsearch_jobs
from locations import DEFAULT_LOCATIONS_JSON, parse_locations
from matcher import compute_score
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


def match_jobs_for_user(db: Session, user: User) -> int:
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if not resume:
        return 0

    skills = filter_skills(json.loads(resume.skills_json or "[]"))
    titles = json.loads(resume.titles_json or "[]")
    jobs = db.query(Job).all()
    count = 0

    for job in jobs:
        score, label = compute_score(
            skills, titles, resume.years_experience, job.title, job.description
        )
        match = (
            db.query(JobMatch)
            .filter(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
            .first()
        )
        if match:
            match.score = score
            match.label = label
            match.updated_at = datetime.utcnow()
        else:
            match = JobMatch(
                user_id=user.id, job_id=job.id, score=score, label=label
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
    keywords = build_search_keywords(skills, titles, profile.extra_keywords)
    locations = parse_locations(profile.locations_json, profile.location, profile.country)
    logger.info("Job search keywords for user %s: %s", user.id, keywords)

    clear_all_jobs(db)

    all_fetched = []
    for loc in locations:
        adzuna = await fetch_adzuna_jobs(keywords, loc["city"], loc["country"])
        jsearch = await fetch_jsearch_jobs(keywords, loc["city"])
        all_fetched.extend(adzuna + jsearch)

    seen = set()
    unique = []
    for item in all_fetched:
        key = (item["external_id"], item["source"])
        if key not in seen and item.get("title"):
            seen.add(key)
            unique.append(item)

    for data in unique:
        upsert_job(db, data)

    matched = match_jobs_for_user(db, user)
    return len(unique), matched


async def refresh_all_jobs(db: Session) -> tuple:
    users = db.query(User).all()
    all_fetched = []

    for user in users:
        resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        profile = _get_or_create_search_profile(db, user)
        skills = filter_skills(json.loads(resume.skills_json) if resume else [])
        titles = json.loads(resume.titles_json) if resume else []
        keywords = build_search_keywords(skills, titles, profile.extra_keywords)
        locations = parse_locations(
            profile.locations_json, profile.location, profile.country
        )
        logger.info("Job search keywords for user %s: %s", user.id, keywords)

        for loc in locations:
            adzuna = await fetch_adzuna_jobs(keywords, loc["city"], loc["country"])
            jsearch = await fetch_jsearch_jobs(keywords, loc["city"])
            all_fetched.extend(adzuna + jsearch)

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
        match_count += match_jobs_for_user(db, user)

    return len(unique), match_count
