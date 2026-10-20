"""workspace intelligence: reviews, share analytics, audit trail

Revision ID: c8d2e3f4a5b6
Revises: b7c1d2e3f4a5
Create Date: 2026-10-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("review_due_at", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("share_links", sa.Column("last_viewed_at", sa.String(), nullable=True))
    op.add_column("share_links", sa.Column("view_count", sa.Integer(), nullable=True, server_default="0"))
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )
    op.create_index("ix_audit_events_org", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_created", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created", table_name="audit_events")
    op.drop_index("ix_audit_events_org", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_column("share_links", "view_count")
    op.drop_column("share_links", "last_viewed_at")
    op.drop_column("assessments", "review_note")
    op.drop_column("assessments", "review_due_at")
