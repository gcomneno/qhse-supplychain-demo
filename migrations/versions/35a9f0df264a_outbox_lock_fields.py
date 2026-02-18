"""outbox lock fields

Revision ID: 35a9f0df264a
Revises: 3369a975eb48
Create Date: 2026-02-18 06:58:32.853235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35a9f0df264a'
down_revision: Union[str, Sequence[str], None] = '3369a975eb48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("locked_by", sa.String(length=64), nullable=True))
    op.add_column("outbox_events", sa.Column("locked_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_outbox_status_locked_at",
        "outbox_events",
        ["status", "locked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_status_locked_at", table_name="outbox_events")
    op.drop_column("outbox_events", "locked_at")
    op.drop_column("outbox_events", "locked_by")
