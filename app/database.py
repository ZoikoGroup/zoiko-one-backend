"""
database.py
-----------
Sets up the connection to Neon PostgreSQL using SQLAlchemy + Psycopg2.

Key concepts for beginners:
  - engine      = the actual connection to your database
  - SessionLocal = a "factory" that creates database sessions
  - Base        = all your models (tables) must inherit from this

How a request works:
  1. Request comes in  -> a new DB session opens
  2. We do DB work     -> read/write data
  3. Request ends      -> session closes (commit or rollback)
"""

from sqlalchemy import create_engine, inspect  # type: ignore[import]
from sqlalchemy.orm import sessionmaker, declarative_base  # type: ignore[import]

from app.config import settings


# -- 1. Create the Engine (Optimized for Neon PostgreSQL) ---------------------
# pool_pre_ping=True: Tests the connection before use to ensure it's alive.
# pool_recycle=1800: Closes idle connections every 30 minutes to prevent Neon's 
#                     "scale-to-zero" architecture from unexpectedly dropping connections.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,          # Slightly reduced size is safer for serverless connection pool limits
    max_overflow=10,
    pool_recycle=1800,    # Added to handle Neon idle timeout drops
)


# -- 2. Create the Session Factory -------------------------------------------
# Each time you call SessionLocal() you get a fresh database session.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# -- 3. Base Class for All Models -------------------------------------------
Base = declarative_base()


# -- 4. Helper: get list of tables from the database -------------------------
def get_table_names() -> list[str]:
    inspector = inspect(engine)
    return inspector.get_table_names()


# -- 5. Dependency: get_db ---------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()