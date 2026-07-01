"""add_created_by_to_assets

Revision ID: d5e6f7a8b9c0
Revises: 4c1e59a8b0d9
Create Date: 2026-07-01 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("created_by", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "created_by")
