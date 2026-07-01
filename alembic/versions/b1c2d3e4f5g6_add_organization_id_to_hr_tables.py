"""add_organization_id_to_missing_hr_tables

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Map of table -> (column_type, nullable, has_index)
TABLES: dict[str, tuple] = {
    # Learning module tables
    "learning_courses":             (sa.Integer, True, True),
    "learning_enrollments":         (sa.Integer, True, True),
    "learning_paths":              (sa.Integer, True, True),
    "learning_path_items":         (sa.Integer, True, True),
    "learning_certifications":     (sa.Integer, True, True),
    "learning_skills":             (sa.Integer, True, True),
    "learning_quiz_attempts":      (sa.Integer, True, True),
    "learning_training_programs":  (sa.Integer, True, True),
    "learning_training_program_assignments": (sa.Integer, True, True),
    "learning_calendar_events":    (sa.Integer, True, True),
}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table, (col_type, nullable, has_index) in TABLES.items():
        # Check if table exists
        tables_in_db = inspector.get_table_names()
        if table not in tables_in_db:
            print(f"[migrate] Table '{table}' does not exist yet — skipping")
            continue

        # Check if organization_id column already exists
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        if "organization_id" in existing_cols:
            print(f"[migrate] Column 'organization_id' already exists in '{table}'")
            continue

        # Add column (nullable=True to be safe with existing data)
        op.add_column(
            table,
            sa.Column("organization_id", col_type, sa.ForeignKey("organizations.id"), nullable=True)
        )
        print(f"[migrate] Added 'organization_id' to '{table}'")

        # Add index if needed
        if has_index:
            try:
                op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
                print(f"[migrate] Created index ix_{table}_organization_id")
            except Exception:
                print(f"[migrate] Index ix_{table}_organization_id already exists or failed — continuing")
    
    # Also check critical non-learning HR tables
    # These are created by Base.metadata.create_all() so should already have org_id,
    # but we verify to be safe
    extra_tables = [
        "departments", "attendance_records", "shifts", "shift_rosters",
        "holidays", "leave_requests", "leave_type_configs", "leave_settings",
        "leave_balances", "assets", "asset_maintenance_requests", "asset_requests",
        "asset_categories", "asset_reports", "pay_grades", "compensation_bands",
        "salary_components", "salary_structures", "employee_compensations",
        "salary_revisions", "allowances", "benefits", "employee_benefits",
        "compliance_records", "engagement_surveys", "ess_requests",
        "onboarding_new_hires", "onboarding_preboarding_tasks", "onboarding_documents",
        "onboarding_checklists", "onboarding_checklist_items", "onboarding_orientations",
        "onboarding_orientation_attendees", "onboarding_activities",
        "performance_reviews", "performance_goals", "performance_kpis",
        "performance_feedback", "performance_appraisals",
        "recruitment_candidates", "recruitment_requisitions", "recruitment_interviews",
        "recruitment_offers", "recruitment_documents", "recruitment_applications",
        "recruitment_interview_feedback", "recruitment_offer_approvals",
        "travel_requests", "travel_approvals", "travel_expenses", "travel_receipts",
        "travel_policies", "travel_settings",
        "workforce_plans", "wf_plans", "wf_headcounts", "wf_successions", "wf_reports",
        "employee_profiles", "employee_reporting", "employee_lifecycle", "employee_history",
        "designations", "hr_documents",
    ]
    for table in extra_tables:
        if table not in {t for t in inspector.get_table_names()}:
            print(f"[migrate] Table '{table}' does not exist yet — skipping")
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        if "organization_id" in existing_cols:
            continue
        op.add_column(
            table,
            sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True)
        )
        print(f"[migrate] Added 'organization_id' to '{table}' (extra safety check)")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    all_tables = list(TABLES.keys()) + [
        "departments", "attendance_records", "shifts", "shift_rosters",
        "holidays", "leave_requests", "leave_type_configs", "leave_settings",
        "leave_balances", "assets", "asset_maintenance_requests", "asset_requests",
        "asset_categories", "asset_reports", "pay_grades", "compensation_bands",
        "salary_components", "salary_structures", "employee_compensations",
        "salary_revisions", "allowances", "benefits", "employee_benefits",
        "compliance_records", "engagement_surveys", "ess_requests",
        "onboarding_new_hires", "onboarding_preboarding_tasks", "onboarding_documents",
        "onboarding_checklists", "onboarding_checklist_items", "onboarding_orientations",
        "onboarding_orientation_attendees", "onboarding_activities",
        "performance_reviews", "performance_goals", "performance_kpis",
        "performance_feedback", "performance_appraisals",
        "recruitment_candidates", "recruitment_requisitions", "recruitment_interviews",
        "recruitment_offers", "recruitment_documents", "recruitment_applications",
        "recruitment_interview_feedback", "recruitment_offer_approvals",
        "travel_requests", "travel_approvals", "travel_expenses", "travel_receipts",
        "travel_policies", "travel_settings",
        "workforce_plans", "wf_plans", "wf_headcounts", "wf_successions", "wf_reports",
        "employee_profiles", "employee_reporting", "employee_lifecycle", "employee_history",
        "designations", "hr_documents",
    ]
    for table in all_tables:
        if table not in {t for t in inspector.get_table_names()}:
            continue
        try:
            op.drop_column(table, "organization_id")
            print(f"[migrate] Dropped 'organization_id' from '{table}'")
        except Exception:
            print(f"[migrate] Could not drop 'organization_id' from '{table}' — continuing")
