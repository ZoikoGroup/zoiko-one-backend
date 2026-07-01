"""Merge multiple heads

Revision ID: 2ee2f272b209
Revises: 03e087b56090, 9b74a301c5c2
Create Date: 2026-06-26 10:46:51.691327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ee2f272b209'
down_revision: Union[str, None] = ('03e087b56090', '9b74a301c5c2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
