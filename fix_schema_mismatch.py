"""
fix_schema_mismatch.py - Final
Drops ALL FKs to learning_courses, recreates the table, re-adds FKs, fixes assets.
"""

from sqlalchemy import inspect, text
from app.database import engine, Base

# Must import models so table metadata registers on Base
from app.modules.hr.models import *  # noqa: F401, F403


def column_exists(table, column):
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def run():
    all_tables = ["learning_enrollments", "learning_assessments", "learning_calendar_events", "learning_path_items"]

    # Step 1: Drop all FKs referencing learning_courses
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for table in all_tables:
                for fk in inspect(engine).get_foreign_keys(table):
                    if fk["referred_table"] == "learning_courses":
                        conn.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {fk['name']}"))
                        print(f"[OK] Dropped FK {fk['name']} on {table}")

            # Step 2: Drop learning_courses
            conn.execute(text("DROP TABLE IF EXISTS learning_courses"))
            print("[OK] Dropped learning_courses")
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"[!!] Failed step 1/2: {e}")
            raise

    # Step 3: Recreate learning_courses via model
    Base.metadata.create_all(bind=engine)
    col_list = [c["name"] for c in inspect(engine).get_columns("learning_courses")]
    print(f"[OK] Recreated learning_courses with: {col_list}")

    # Step 4: Re-add all FKs
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            existing = {}
            for table in all_tables:
                for fk in inspect(engine).get_foreign_keys(table):
                    existing.setdefault(table, []).append(fk["name"])

            refs = [
                ("learning_enrollments", "course_id", "learning_enrollments_ibfk_1"),
                ("learning_assessments", "course_id", "learning_assessments_ibfk_1"),
                ("learning_calendar_events", "course_id", "learning_calendar_events_ibfk_1"),
                ("learning_path_items", "course_id", "learning_path_items_ibfk_2"),
            ]
            for table, col, fk_name in refs:
                if fk_name not in existing.get(table, []):
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} "
                        f"FOREIGN KEY ({col}) REFERENCES learning_courses(id) ON DELETE CASCADE"
                    ))
                    print(f"[OK] Re-added FK {fk_name} on {table}")

            trans.commit()
            print("[OK] All FKs re-added")
        except Exception as e:
            trans.rollback()
            print(f"[!!] Failed step 4: {e}")
            raise

    # Step 5: Fix assets table
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            missing = [
                ("category", "VARCHAR(100) NULL"),
                ("serial_number", "VARCHAR(200) NULL"),
                ("department", "VARCHAR(100) NULL"),
                ("purchase_date", "DATE NULL"),
                ("purchase_cost", "NUMERIC(10,2) NULL"),
            ]
            for col, dtype in missing:
                if not column_exists("assets", col):
                    conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col} {dtype}"))
                    print(f"  [OK] Added assets.{col}")

            if not column_exists("assets", "condition"):
                conn.execute(text("ALTER TABLE assets ADD COLUMN `condition` VARCHAR(20) NULL"))
                print("  [OK] Added assets.condition")

            for col, dtype in [
                ("retired_at", "DATETIME NULL"),
                ("updated_at", "DATETIME NULL ON UPDATE CURRENT_TIMESTAMP"),
                ("deleted_at", "DATETIME NULL"),
            ]:
                if not column_exists("assets", col):
                    conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col} {dtype}"))
                    print(f"  [OK] Added assets.{col}")

            trans.commit()
            print("[OK] Assets columns fixed!")
        except Exception as e:
            trans.rollback()
            print(f"[!!] Failed step 5: {e}")
            raise

    print("=" * 60)
    print("[OK] All schema mismatches fixed! Restart backend.")
    print("=" * 60)


if __name__ == "__main__":
    run()
