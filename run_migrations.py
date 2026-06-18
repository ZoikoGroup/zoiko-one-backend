"""
run_migrations.py
-----------------
Safe migration runner for Zoiko One MySQL database.
Uses SQLAlchemy introspection to check columns/indexes before creating them.
Usage:  python run_migrations.py
"""

import sys
from sqlalchemy import inspect, text
from app.database import engine


def column_exists(table, column):
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def index_exists(table, index_name):
    inspector = inspect(engine)
    indexes = [ix["name"] for ix in inspector.get_indexes(table)]
    return index_name in indexes


def foreign_key_exists(table, fk_name):
    inspector = inspect(engine)
    fks = [fk["name"] for fk in inspector.get_foreign_keys(table)]
    return fk_name in fks


def run():
    print("=" * 60)
    print("Zoiko One - Database Migration")
    print("=" * 60)

    with engine.connect() as conn:
        trans = conn.begin()

        try:
            # -- ASSETS MIGRATIONS --

            # 1. Asset table: new columns
            for col, dtype in [
                ("created_by", "INT NULL"),
                ("updated_by", "INT NULL"),
                ("warranty_expiry", "DATE NULL"),
                ("vendor", "VARCHAR(200) NULL"),
                ("location", "VARCHAR(200) NULL"),
            ]:
                if not column_exists("assets", col):
                    conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col} {dtype}"))
                    print(f"  [OK] Added column assets.{col}")
                else:
                    print(f"  [--] Skipped assets.{col} (exists)")

            for fk_name, col, ref in [
                ("fk_assets_created_by", "created_by", "employees(id) ON DELETE SET NULL"),
                ("fk_assets_updated_by", "updated_by", "employees(id) ON DELETE SET NULL"),
            ]:
                if not foreign_key_exists("assets", fk_name) and column_exists("assets", col):
                    conn.execute(text(f"ALTER TABLE assets ADD CONSTRAINT {fk_name} FOREIGN KEY ({col}) REFERENCES {ref}"))
                    print(f"  [OK] Added FK {fk_name}")

            # 2. AssetMaintenanceRequest: audit columns
            for col in ["created_by", "updated_by"]:
                if not column_exists("asset_maintenance_requests", col):
                    conn.execute(text(f"ALTER TABLE asset_maintenance_requests ADD COLUMN {col} INT NULL"))
                    print(f"  [OK] Added asset_maintenance_requests.{col}")

            for fk_name, col in [
                ("fk_maintenance_created_by", "created_by"),
                ("fk_maintenance_updated_by", "updated_by"),
            ]:
                if not foreign_key_exists("asset_maintenance_requests", fk_name) and column_exists("asset_maintenance_requests", col):
                    conn.execute(text(f"ALTER TABLE asset_maintenance_requests ADD CONSTRAINT {fk_name} FOREIGN KEY ({col}) REFERENCES employees(id) ON DELETE SET NULL"))
                    print(f"  [OK] Added FK {fk_name}")

            # 3. AssetRequest: audit columns
            for col in ["created_by", "updated_by"]:
                if not column_exists("asset_requests", col):
                    conn.execute(text(f"ALTER TABLE asset_requests ADD COLUMN {col} INT NULL"))
                    print(f"  [OK] Added asset_requests.{col}")

            for fk_name, col in [
                ("fk_asset_requests_created_by", "created_by"),
                ("fk_asset_requests_updated_by", "updated_by"),
            ]:
                if not foreign_key_exists("asset_requests", fk_name) and column_exists("asset_requests", col):
                    conn.execute(text(f"ALTER TABLE asset_requests ADD CONSTRAINT {fk_name} FOREIGN KEY ({col}) REFERENCES employees(id) ON DELETE SET NULL"))
                    print(f"  [OK] Added FK {fk_name}")

            # 4. AssetCategory: updated_at, created_by
            if not column_exists("asset_categories", "updated_at"):
                conn.execute(text("ALTER TABLE asset_categories ADD COLUMN updated_at DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP"))
                print("  [OK] Added asset_categories.updated_at")

            if not column_exists("asset_categories", "created_by"):
                conn.execute(text("ALTER TABLE asset_categories ADD COLUMN created_by INT NULL"))
                print("  [OK] Added asset_categories.created_by")

            if not foreign_key_exists("asset_categories", "fk_asset_categories_created_by") and column_exists("asset_categories", "created_by"):
                conn.execute(text("ALTER TABLE asset_categories ADD CONSTRAINT fk_asset_categories_created_by FOREIGN KEY (created_by) REFERENCES employees(id) ON DELETE SET NULL"))
                print("  [OK] Added FK fk_asset_categories_created_by")

            # 5. AssetSetting: created_at
            if not column_exists("asset_settings", "created_at"):
                conn.execute(text("ALTER TABLE asset_settings ADD COLUMN created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP"))
                print("  [OK] Added asset_settings.created_at")

            # -- INDEXES --

            indexes = [
                ("assets", "idx_assets_status", "status"),
                ("assets", "idx_assets_category", "category"),
                ("assets", "idx_assets_employee_id", "employee_id"),
                ("assets", "idx_assets_department", "department"),
                ("assets", "idx_assets_deleted_at", "deleted_at"),
                ("asset_maintenance_requests", "idx_maintenance_asset_id", "asset_id"),
                ("asset_maintenance_requests", "idx_maintenance_status", "status"),
                ("asset_requests", "idx_asset_requests_status", "status"),
                ("asset_requests", "idx_asset_requests_employee_id", "employee_id"),
                ("asset_categories", "idx_asset_categories_name", "name"),
                ("asset_categories", "idx_asset_categories_is_active", "is_active"),
                ("asset_reports", "idx_asset_reports_type", "report_type"),
                ("asset_settings", "idx_asset_settings_key", "setting_key"),
                # Learning indexes
                ("learning_courses", "idx_learning_courses_status", "status"),
                ("learning_courses", "idx_learning_courses_category", "category"),
                ("learning_enrollments", "idx_learning_enrollments_course_id", "course_id"),
                ("learning_enrollments", "idx_learning_enrollments_employee_id", "employee_id"),
                ("learning_enrollments", "idx_learning_enrollments_status", "status"),
                ("learning_paths", "idx_learning_path_is_active", "is_active"),
                ("learning_path_items", "idx_learning_path_items_path_id", "path_id"),
                ("learning_path_items", "idx_learning_path_items_course_id", "course_id"),
                ("learning_certifications", "idx_learning_certs_employee_id", "employee_id"),
                ("learning_certifications", "idx_learning_certs_status", "status"),
                ("learning_skills", "idx_learning_skills_employee_id", "employee_id"),
                ("learning_skills", "idx_learning_skills_name", "skill_name"),
                ("learning_assessments", "idx_learning_assessments_course_id", "course_id"),
                ("learning_assessments", "idx_learning_assessments_active", "is_active"),
                ("learning_assessment_questions", "idx_learning_questions_assessment_id", "assessment_id"),
                ("learning_quiz_attempts", "idx_quiz_attempts_assessment_id", "assessment_id"),
                ("learning_quiz_attempts", "idx_quiz_attempts_employee_id", "employee_id"),
                ("learning_quiz_attempts", "idx_quiz_attempts_status", "status"),
                ("learning_quiz_attempts", "idx_quiz_attempts_enrollment_id", "enrollment_id"),
                ("learning_training_programs", "idx_training_programs_status", "status"),
                ("learning_training_programs", "idx_training_programs_instructor", "instructor_id"),
                ("learning_training_program_assignments", "idx_training_assignments_program_id", "program_id"),
                ("learning_training_program_assignments", "idx_training_assignments_employee_id", "employee_id"),
                ("learning_calendar_events", "idx_calendar_events_date", "event_date"),
                ("learning_calendar_events", "idx_calendar_events_type", "event_type"),
                ("learning_calendar_events", "idx_calendar_events_course_id", "course_id"),
                ("learning_calendar_events", "idx_calendar_events_program_id", "program_id"),
            ]

            for table, ix_name, column in indexes:
                if not index_exists(table, ix_name):
                    try:
                        conn.execute(text(f"CREATE INDEX {ix_name} ON {table}({column})"))
                        print(f"  [OK] Created index {ix_name} ON {table}({column})")
                    except Exception as e:
                        print(f"  [!!] Failed index {ix_name}: {e}")
                else:
                    print(f"  [--] Skipped index {ix_name} (exists)")

            trans.commit()
            print("=" * 60)
            print("[OK] All migrations applied successfully!")
            print("=" * 60)

        except Exception as e:
            trans.rollback()
            print(f"[!!] Migration failed: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    run()
