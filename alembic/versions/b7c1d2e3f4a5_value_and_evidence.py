"""value workstreams: assumptions, evidence, plans, campaign workflow

Revision ID: b7c1d2e3f4a5
Revises: a3215a8bac2a
Create Date: 2026-10-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a3215a8bac2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("share_links", sa.Column("expires_at", sa.String(), nullable=True))
    op.add_column("financial_models", sa.Column("assumptions_json", sa.Text(), nullable=True))
    op.add_column("roadmap_items", sa.Column("owner", sa.String(), nullable=True))
    op.add_column("roadmap_items", sa.Column("due_date", sa.String(), nullable=True))
    op.add_column("roadmap_items", sa.Column("status", sa.String(), nullable=True, server_default="not_started"))
    op.add_column("roadmap_items", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("roadmap_items", sa.Column("created_at", sa.String(), nullable=True))
    op.add_column("roadmap_items", sa.Column("updated_at", sa.String(), nullable=True))

    op.create_table(
        "assessment_assumptions",
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id"), primary_key=True),
        sa.Column("staff", sa.Integer(), nullable=True),
        sa.Column("hourly_rate", sa.Float(), nullable=True),
        sa.Column("working_hours_per_month", sa.Float(), nullable=True),
        sa.Column("max_savings_share", sa.Float(), nullable=True),
        sa.Column("annual_revenue", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
    )
    op.create_table(
        "evidence_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )
    op.create_index("ix_evidence_attachments_assessment", "evidence_attachments", ["assessment_id"])
    op.create_table(
        "campaign_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_token", sa.String(), sa.ForeignKey("collect_campaigns.token"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
    )
    op.create_index("ix_campaign_comments_token", "campaign_comments", ["campaign_token"])
    op.create_table(
        "campaign_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_token", sa.String(), sa.ForeignKey("collect_campaigns.token"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )
    op.create_index("ix_campaign_approvals_token", "campaign_approvals", ["campaign_token"])


def downgrade() -> None:
    op.drop_index("ix_campaign_approvals_token", table_name="campaign_approvals")
    op.drop_table("campaign_approvals")
    op.drop_index("ix_campaign_comments_token", table_name="campaign_comments")
    op.drop_table("campaign_comments")
    op.drop_index("ix_evidence_attachments_assessment", table_name="evidence_attachments")
    op.drop_table("evidence_attachments")
    op.drop_table("assessment_assumptions")
    op.drop_column("roadmap_items", "updated_at")
    op.drop_column("roadmap_items", "created_at")
    op.drop_column("roadmap_items", "notes")
    op.drop_column("roadmap_items", "status")
    op.drop_column("roadmap_items", "due_date")
    op.drop_column("roadmap_items", "owner")
    op.drop_column("financial_models", "assumptions_json")
    op.drop_column("share_links", "expires_at")
