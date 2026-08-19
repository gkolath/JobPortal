import json
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from config import settings
from database import get_db, init_db
from locations import DEFAULT_LOCATIONS_JSON, parse_locations
from models import Job, JobMatch, Resume, SearchProfile, User
from resume_parser import parse_resume, to_json_list
from schemas import (
    DashboardStats,
    JobOut,
    JobStatusUpdate,
    LoginRequest,
    RefreshResponse,
    RegisterRequest,
    ResumeOut,
    SearchProfileOut,
    SearchProfileUpdate,
    LocationItem,
    TokenResponse,
    UserOut,
)
from services import match_jobs_for_user, refresh_all_jobs


def profile_to_out(profile: SearchProfile) -> SearchProfileOut:
    locs = parse_locations(profile.locations_json, profile.location, profile.country)
    return SearchProfileOut(
        country=profile.country,
        location=profile.location,
        locations=[LocationItem(**loc) for loc in locs],
        extra_keywords=profile.extra_keywords,
    )


app = FastAPI(title="Job Match Portal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.post("/api/auth/register", response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    count = db.query(User).count()
    if count >= settings.max_users:
        raise HTTPException(status_code=403, detail="Registration closed (max users reached)")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(SearchProfile(
        user_id=user.id,
        location=settings.default_location,
        locations_json=DEFAULT_LOCATIONS_JSON,
    ))
    db.commit()

    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@app.get("/api/users", response_model=List[UserOut])
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [UserOut.model_validate(u) for u in db.query(User).all()]


@app.post("/api/resumes/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "resume.pdf").suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    dest = settings.uploads_dir / f"{user.id}_{uuid.uuid4()}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        raw, skills, titles, years = parse_resume(dest)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not parse resume: {exc}")

    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if resume:
        resume.file_name = file.filename or dest.name
        resume.raw_text = raw
        resume.skills_json = to_json_list(skills)
        resume.titles_json = to_json_list(titles)
        resume.years_experience = years
        resume.uploaded_at = __import__("datetime").datetime.utcnow()
    else:
        resume = Resume(
            user_id=user.id,
            file_name=file.filename or dest.name,
            raw_text=raw,
            skills_json=to_json_list(skills),
            titles_json=to_json_list(titles),
            years_experience=years,
        )
        db.add(resume)
    db.commit()
    db.refresh(resume)

    match_jobs_for_user(db, user)

    return ResumeOut(
        file_name=resume.file_name,
        skills=skills,
        titles=titles,
        years_experience=resume.years_experience,
        uploaded_at=resume.uploaded_at,
    )


@app.get("/api/resumes/me", response_model=Optional[ResumeOut])
def get_my_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if not resume:
        return None
    return ResumeOut(
        file_name=resume.file_name,
        skills=json.loads(resume.skills_json),
        titles=json.loads(resume.titles_json),
        years_experience=resume.years_experience,
        uploaded_at=resume.uploaded_at,
    )


@app.get("/api/profile", response_model=SearchProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(SearchProfile).filter(SearchProfile.user_id == user.id).first()
    if not profile:
        profile = SearchProfile(
            user_id=user.id,
            location=settings.default_location,
            locations_json=DEFAULT_LOCATIONS_JSON,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile_to_out(profile)


@app.put("/api/profile", response_model=SearchProfileOut)
def update_profile(
    data: SearchProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(SearchProfile).filter(SearchProfile.user_id == user.id).first()
    if not profile:
        profile = SearchProfile(user_id=user.id)
        db.add(profile)
    if data.country is not None:
        profile.country = data.country
    if data.location is not None:
        profile.location = data.location
    if data.extra_keywords is not None:
        profile.extra_keywords = data.extra_keywords
    if data.locations is not None:
        profile.locations_json = json.dumps([loc.model_dump() for loc in data.locations])
        if data.locations:
            profile.location = data.locations[0].city
            profile.country = data.locations[0].country
    db.commit()
    db.refresh(profile)
    return profile_to_out(profile)


@app.post("/api/jobs/refresh", response_model=RefreshResponse)
async def refresh_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fetched, matched = await refresh_all_jobs(db)
    return RefreshResponse(jobs_fetched=fetched, matches_updated=matched)


@app.get("/api/jobs", response_model=List[JobOut])
def list_jobs(
    match: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    saved: Optional[bool] = Query(None),
    applied: Optional[bool] = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_id = user_id if user_id else current.id
    q = (
        db.query(JobMatch, Job)
        .join(Job, JobMatch.job_id == Job.id)
        .filter(JobMatch.user_id == target_id)
        .order_by(JobMatch.score.desc())
    )
    if match:
        q = q.filter(JobMatch.label == match)
    if saved is not None:
        q = q.filter(JobMatch.saved == saved)
    if applied is not None:
        q = q.filter(JobMatch.applied == applied)

    results = []
    for jm, job in q.all():
        results.append(
            JobOut(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                description=job.description[:500],
                url=job.url,
                source=job.source,
                posted_at=job.posted_at,
                score=jm.score,
                label=jm.label,
                saved=jm.saved,
                applied=jm.applied,
                notes=jm.notes,
            )
        )
    return results


@app.patch("/api/jobs/{job_id}/status")
def update_job_status(
    job_id: int,
    data: JobStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = (
        db.query(JobMatch)
        .filter(JobMatch.job_id == job_id, JobMatch.user_id == user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Job match not found")
    if data.saved is not None:
        match.saved = data.saved
    if data.applied is not None:
        match.applied = data.applied
    if data.notes is not None:
        match.notes = data.notes
    db.commit()
    return {"ok": True}


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    matches = db.query(JobMatch).filter(JobMatch.user_id == user.id)
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    return DashboardStats(
        close_matches=matches.filter(JobMatch.label == "close").count(),
        good_matches=matches.filter(JobMatch.label == "good").count(),
        total_jobs=matches.count(),
        saved_count=matches.filter(JobMatch.saved.is_(True)).count(),
        applied_count=matches.filter(JobMatch.applied.is_(True)).count(),
        has_resume=resume is not None,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


if settings.static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(settings.static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        index = settings.static_dir / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(__import__("os").getenv("PORT", "8000")))
