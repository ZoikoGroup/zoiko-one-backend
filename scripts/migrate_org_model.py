"""
Migration: Add on_hold_at and domain columns to organizations table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from sqlalchemy import text

def run():
    db = SessionLocal()
    try:
        # Check if on_hold_at column exists
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='organizations' AND column_name='on_hold_at'
        """)).fetchone()
        if not result:
            print("Adding on_hold_at column...")
            db.execute(text("ALTER TABLE organizations ADD COLUMN on_hold_at TIMESTAMP NULL"))
        else:
            print("on_hold_at column already exists.")

        # Check if domain column exists
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='organizations' AND column_name='domain'
        """)).fetchone()
        if not result:
            print("Adding domain column...")
            db.execute(text("ALTER TABLE organizations ADD COLUMN domain VARCHAR(255) NULL"))
        else:
            print("domain column already exists.")

        db.commit()
        print("Migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run()
