"""add_organization_address_fields

Revision ID: a1b2c3d4e5f6
Revises: 4c1e59a8b0d9
Create Date: 2026-06-30 08:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4c1e59a8b0d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns("organizations")}

    columns = [
        ("address", sa.Text()),
        ("country", sa.String(100)),
        ("state", sa.String(100)),
        ("city", sa.String(100)),
        ("timezone", sa.String(100)),
        ("currency", sa.String(3)),
        ("industry", sa.String(200)),
    ]
    for col_name, col_type in columns:
        if col_name not in existing:
            op.add_column("organizations", sa.Column(col_name, col_type, nullable=True))
            print(f"[migrate] Added column '{col_name}' to organizations table")
        else:
            print(f"[migrate] Column '{col_name}' already exists in organizations table")


def downgrade() -> None:
    columns = ["address", "country", "state", "city", "timezone", "currency", "industry"]
    for col in columns:
        op.drop_column("organizations", col)
