from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (  # noqa: F401
        Job,
        JobMatch,
        Resume,
        SearchProfile,
        User,
    )

    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    inspector = inspect(engine)
    if "search_profiles" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("search_profiles")}
    if "locations_json" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE search_profiles ADD COLUMN locations_json TEXT DEFAULT '[]'")
            )
