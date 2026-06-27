"""fix_userrole_enum_add_hr_admin

Revision ID: 4c1e59a8b0d9
Revises: 9cd78f7dbd4c
Create Date: 2026-06-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4c1e59a8b0d9'
down_revision: Union[str, None] = '9cd78f7dbd4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# All expected UserRole values (uppercase names to match CaseInsensitiveEnum)
EXPECTED_ROLES = [
    "ADMIN",
    "HR_ADMIN",
    "HR_MANAGER",
    "MANAGER",
    "EMPLOYEE",
    "SUPER_ADMIN",
]


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT unnest(enum_range(NULL::userrole))::text")
    ).fetchall()
    existing = {r[0] for r in result}
    for val in EXPECTED_ROLES:
        if val not in existing:
            op.execute(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum.
    # This migration is additive only.
    pass
