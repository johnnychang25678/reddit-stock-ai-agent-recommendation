import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(
    DATABASE_URL,
    # for logging SQL queries, set environment variable SQL_ECHO=1
    echo=os.getenv("SQL_ECHO", "") == "1",
)

SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_session():
    """Context-managed session with commit/rollback semantics."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
