"""
Shared database utilities.

Provides get_engine() and get_session() factory functions backed by the
DATABASE_URL environment variable.  SessionLocal is a convenience alias
for get_session so callers can write ``SessionLocal()`` to obtain a session.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

_engine = None
_session_factory = None


def get_engine():
    """Return the singleton SQLAlchemy engine created from DATABASE_URL."""
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session():
    """Return a new SQLAlchemy session bound to the shared engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory()


# Convenience alias: SessionLocal() returns a new session, matching the
# common FastAPI / SQLAlchemy naming convention.
SessionLocal = get_session
