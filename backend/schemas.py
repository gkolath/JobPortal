from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class ResumeOut(BaseModel):
    file_name: str
    skills: List[str]
    titles: List[str]
    years_experience: int
    uploaded_at: datetime
    search_query: str = ""

    class Config:
        from_attributes = True


class LocationItem(BaseModel):
    city: str
    country: str


class SearchProfileUpdate(BaseModel):
    country: Optional[str] = None
    location: Optional[str] = None
    locations: Optional[List[LocationItem]] = None
    extra_keywords: Optional[str] = None


class SearchProfileOut(BaseModel):
    country: str
    location: str
    locations: List[LocationItem]
    extra_keywords: str

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_at: Optional[datetime]
    score: float
    label: str
    saved: bool
    applied: bool
    notes: str

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    saved: Optional[bool] = None
    applied: Optional[bool] = None
    notes: Optional[str] = None


class DashboardStats(BaseModel):
    close_matches: int
    good_matches: int
    weak_matches: int
    total_jobs: int
    saved_count: int
    applied_count: int
    has_resume: bool


class RefreshResponse(BaseModel):
    jobs_fetched: int
    matches_updated: int
