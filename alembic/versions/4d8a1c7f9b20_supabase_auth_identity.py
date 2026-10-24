"""supabase auth identity

Revision ID: 4d8a1c7f9b20
Revises: 6c1f2a9d8e44
Create Date: 2026-10-24 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4d8a1c7f9b20"
down_revision: str | Sequence[str] | None = "6c1f2a9d8e44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("supabase_id", sa.String(), nullable=True))
        batch_op.create_index("ix_users_supabase_id", ["supabase_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_supabase_id")
        batch_op.drop_column("supabase_id")
