from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resume: Mapped["Resume"] = relationship(back_populates="user", uselist=False)
    search_profile: Mapped["SearchProfile"] = relationship(back_populates="user", uselist=False)
    job_matches: Mapped[list["JobMatch"]] = relationship(back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    titles_json: Mapped[str] = mapped_column(Text, default="[]")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    search_query: Mapped[str] = mapped_column(String(500), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="resume")


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    country: Mapped[str] = mapped_column(String(10), default="in")
    location: Mapped[str] = mapped_column(String(120), default="Bangalore")
    locations_json: Mapped[str] = mapped_column(Text, default="[]")
    extra_keywords: Mapped[str] = mapped_column(String(500), default="")

    user: Mapped["User"] = relationship(back_populates="search_profile")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("external_id", "source", name="uq_job_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    matches: Mapped[list["JobMatch"]] = relationship(back_populates="job")


class JobMatch(Base):
    __tablename__ = "jobs_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    label: Mapped[str] = mapped_column(String(20), default="weak")
    fit_reason: Mapped[str] = mapped_column(Text, default="")
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="job_matches")
    job: Mapped["Job"] = relationship(back_populates="matches")
