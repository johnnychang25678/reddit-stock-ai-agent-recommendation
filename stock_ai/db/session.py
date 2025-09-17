import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Global variables to hold engine and session factory
_engine = None
_SessionLocal = None


def _get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        db_target = os.getenv("DB_TARGET", "LOCAL")
        if db_target == "LOCAL":
            database_url = os.getenv("DATABASE_URL_LOCAL")
        elif db_target == "REMOTE":
            database_url = os.getenv("DATABASE_URL_REMOTE")
        
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        _engine = create_engine(
            database_url,
            # for logging SQL queries, set environment variable SQL_ECHO=1
            echo=os.getenv("SQL_ECHO", "") == "1",
        )
    return _engine


def _get_session_local():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_session():
    """Context-managed session with commit/rollback semantics."""
    SessionLocal = _get_session_local()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(database_url: str | None = None):
    global _engine, _SessionLocal
    
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    
    # Reset globals to force recreation
    _engine = None
    _SessionLocal = None
    
    # Trigger creation
    _get_engine()
    _get_session_local()


def reset_db():
    """Reset database connection. Useful for testing."""
    global _engine, _SessionLocal
    
    if _engine:
        _engine.dispose()
    
    _engine = None
    _SessionLocal = None