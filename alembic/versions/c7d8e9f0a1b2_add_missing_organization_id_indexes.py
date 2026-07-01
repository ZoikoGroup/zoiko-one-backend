"""add_missing_organization_id_indexes

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5g6
Create Date: 2026-07-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables missing organization_id index
TABLES: list[tuple[str, str, str]] = [
    # (table, column, index_name)
    # HR module — critical
    ("employees",                   "organization_id", "ix_employees_organization_id"),
    ("pay_grades",                  "organization_id", "ix_pay_grades_organization_id"),
    ("compensation_bands",          "organization_id", "ix_compensation_bands_organization_id"),
    ("salary_components",           "organization_id", "ix_salary_components_organization_id"),
    ("salary_structures",           "organization_id", "ix_salary_structures_organization_id"),
    ("employee_compensations",      "organization_id", "ix_employee_compensations_organization_id"),
    ("salary_revisions",            "organization_id", "ix_salary_revisions_organization_id"),
    ("allowances",                  "organization_id", "ix_allowances_organization_id"),
    ("benefits",                    "organization_id", "ix_benefits_organization_id"),
    ("employee_benefits",           "organization_id", "ix_employee_benefits_organization_id"),
    # Super admin module
    ("super_admin_organization_products", "organization_id", "ix_super_admin_organization_products_organization_id"),
    ("super_admin_support_tickets", "organization_id", "ix_super_admin_support_tickets_organization_id"),
    ("super_admin_approval_history","organization_id", "ix_super_admin_approval_history_organization_id"),
    ("super_admin_security_events", "organization_id", "ix_super_admin_security_events_organization_id"),
    ("super_admin_login_activities","organization_id", "ix_super_admin_login_activities_organization_id"),
    # Special case — uses target_org_id instead of organization_id
    ("super_admin_notifications",   "target_org_id",   "ix_super_admin_notifications_target_org_id"),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table, column, index_name in TABLES:
        tables_in_db = inspector.get_table_names()
        if table not in tables_in_db:
            print(f"[migrate] Table '{table}' does not exist — skipping")
            continue

        # Check if column exists
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        if column not in existing_cols:
            print(f"[migrate] Column '{column}' does not exist in '{table}' — skipping")
            continue

        # Check if index already exists
        existing_indexes = {ix["name"] for ix in inspector.get_indexes(table)}
        if index_name in existing_indexes:
            print(f"[migrate] Index '{index_name}' already exists on '{table}' — skipping")
            continue

        try:
            op.create_index(index_name, table, [column])
            print(f"[migrate] Created index '{index_name}' on '{table}({column})'")
        except Exception as e:
            print(f"[migrate] Failed to create index '{index_name}': {e} — continuing")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table, column, index_name in TABLES:
        tables_in_db = inspector.get_table_names()
        if table not in tables_in_db:
            continue
        existing_indexes = {ix["name"] for ix in inspector.get_indexes(table)}
        if index_name not in existing_indexes:
            continue
        try:
            op.drop_index(index_name, table_name=table)
            print(f"[migrate] Dropped index '{index_name}' from '{table}'")
        except Exception as e:
            print(f"[migrate] Failed to drop index '{index_name}': {e} — continuing")
