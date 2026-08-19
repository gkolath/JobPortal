#!/usr/bin/env python3
"""Seed two user accounts for the job portal."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from locations import DEFAULT_LOCATIONS_JSON
from auth import hash_password
from database import SessionLocal, init_db
from models import SearchProfile, User
from config import settings


def main():
    init_db()
    db = SessionLocal()

    users = [
        {"name": "George", "email": "gkolath85@hotmail.com", "password": "changeme123"},
        {"name": "Friend", "email": "friend@example.com", "password": "changeme123"},
    ]

    for u in users:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if existing:
            print(f"Exists: {u['email']}")
            continue
        user = User(
            name=u["name"],
            email=u["email"],
            password_hash=hash_password(u["password"]),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(SearchProfile(
            user_id=user.id,
            location=settings.default_location,
            country="in",
            locations_json=DEFAULT_LOCATIONS_JSON,
        ))
        db.commit()
        print(f"Created: {u['email']} / {u['password']}")

    db.close()
    print("Done. Change passwords after first login.")


if __name__ == "__main__":
    main()
