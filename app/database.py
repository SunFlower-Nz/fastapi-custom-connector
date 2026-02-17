"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base, Department

# Only use check_same_thread for SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Default departments to seed on first run
DEFAULT_DEPARTMENTS = [
    {"name": "Engineering", "code": "ENG"},
    {"name": "Human Resources", "code": "HR"},
    {"name": "Finance", "code": "FIN"},
    {"name": "Marketing", "code": "MKT"},
    {"name": "Sales", "code": "SLS"},
    {"name": "Information Technology", "code": "IT"},
    {"name": "Operations", "code": "OPS"},
]


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def seed_departments() -> None:
    """Seed default departments if table is empty."""
    db: Session = SessionLocal()
    try:
        count = db.query(Department).count()
        if count == 0:
            for dept_data in DEFAULT_DEPARTMENTS:
                db.add(Department(**dept_data))
            db.commit()
    finally:
        db.close()


def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
