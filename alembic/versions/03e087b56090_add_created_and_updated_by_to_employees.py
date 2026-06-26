"""add_created_and_updated_by_to_employees

Revision ID: 03e087b56090
Revises: 
Create Date: 2026-06-25 18:37:58.681142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa  # type: ignore[import]


# revision identifiers, used by Alembic.
revision: str = '03e087b56090'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("created_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True))
    op.add_column("employees", sa.Column("updated_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "updated_by")
    op.drop_column("employees", "created_by")
