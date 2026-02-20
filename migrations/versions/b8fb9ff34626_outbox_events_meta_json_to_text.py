"""outbox_events meta_json to text

Revision ID: b8fb9ff34626
Revises: 4ef99f3c9bb6
Create Date: 2026-02-20 18:57:10.817096

"""
import sqlalchemy as sa

from typing import Sequence, Union
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8fb9ff34626'
down_revision: Union[str, Sequence[str], None] = '4ef99f3c9bb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert jsonb -> text (safe) e allinea al modello attuale (Text, default "{}")
    op.alter_column(
        "outbox_events",
        "meta_json",
        existing_type=postgresql.JSONB(),
        type_=sa.Text(),
        postgresql_using="meta_json::text",
        existing_nullable=True,
    )
    op.alter_column(
        "outbox_events",
        "meta_json",
        nullable=False,
        server_default=sa.text("'{}'"),
        existing_type=sa.Text(),
    )


def downgrade() -> None:
    # Revert text -> jsonb (best-effort). Se ci sono stringhe non-JSON, questo può fallire.
    op.alter_column(
        "outbox_events",
        "meta_json",
        existing_type=sa.Text(),
        type_=postgresql.JSONB(),
        postgresql_using="meta_json::jsonb",
        existing_nullable=False,
    )
    op.alter_column(
        "outbox_events",
        "meta_json",
        server_default=None,
        existing_type=postgresql.JSONB(),
    )
