"""compliance document attachments

Revision ID: d1e2f3a4b5c6
Revises: a9b8c7d6e5f4
Create Date: 2026-10-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("compliance_documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attachment_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("attachment_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("attachment_backend", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("attachment_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("attachment_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("attachment_uploaded_at", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("compliance_documents", schema=None) as batch_op:
        batch_op.drop_column("attachment_uploaded_at")
        batch_op.drop_column("attachment_type")
        batch_op.drop_column("attachment_size")
        batch_op.drop_column("attachment_backend")
        batch_op.drop_column("attachment_key")
        batch_op.drop_column("attachment_name")
