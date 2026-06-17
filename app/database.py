"""
database.py
-----------
Sets up the connection to PostgreSQL using SQLAlchemy.

Key concepts for beginners:
  - engine      = the actual connection to your database
  - SessionLocal = a "factory" that creates database sessions
  - Base        = all your models (tables) must inherit from this

How a request works:
  1. Request comes in  → a new DB session opens
  2. We do DB work     → read/write data
  3. Request ends      → session closes (commit or rollback)
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings


# ── 1. Create the Engine ──────────────────────────────────────────────────────
# The engine manages the actual connection pool to PostgreSQL.
# pool_pre_ping=True means SQLAlchemy will test the connection before using it
# (prevents "server closed connection" errors after idle time).
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
    )


# ── 2. Create the Session Factory ─────────────────────────────────────────────
# Each time you call SessionLocal() you get a fresh database session.
# autocommit=False → we manually commit (gives us control over transactions)
# autoflush=False  → we manually flush (prevents accidental early writes)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── 3. Base Class for All Models ──────────────────────────────────────────────
# Every table model you create (Employee, Department, etc.) will do:
#     class Employee(Base): ...
# This is how SQLAlchemy knows which classes represent database tables.
Base = declarative_base()


# ── 4. Dependency: get_db ─────────────────────────────────────────────────────
# This is a FastAPI "dependency" — a reusable function injected into routes.
# The `yield` makes it a context manager:
#   - Code BEFORE yield  = setup   (open session)
#   - Code AFTER yield   = teardown (close session, even if error occurred)
def get_db():
    db = SessionLocal()
    try:
        yield db          # ← the route function receives this `db` object
    finally:
        db.close()        # ← always closes, even if an exception happened
