"""add meta_json to outbox_events

Revision ID: 4ef99f3c9bb6
Revises: 35a9f0df264a
Create Date: 2026-02-20 18:53:18.098846

"""
import sqlalchemy as sa

from typing import Sequence, Union
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4ef99f3c9bb6'
down_revision: Union[str, Sequence[str], None] = '35a9f0df264a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column(
            "meta_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("outbox_events", "meta_json")
