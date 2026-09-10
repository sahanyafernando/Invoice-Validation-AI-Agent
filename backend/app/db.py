from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

url = settings.sqlalchemy_database_url
connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

engine = create_engine(
    url,
    connect_args=connect_args,
    pool_pre_ping=True,
    # Keep a small client-side pool: plenty for a hackathon/API demo and kind
    # to Supabase connection limits.
    pool_size=5 if not url.startswith("sqlite") else 5,
    max_overflow=5 if not url.startswith("sqlite") else 10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
