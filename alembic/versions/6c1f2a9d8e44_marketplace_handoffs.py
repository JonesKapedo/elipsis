"""marketplace signed handoffs

Revision ID: 6c1f2a9d8e44
Revises: 5b7b51e54c7c
Create Date: 2026-10-24 01:05:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '6c1f2a9d8e44'
down_revision: str | Sequence[str] | None = '5b7b51e54c7c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'marketplace_handoffs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('partner', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('expires_at', sa.String(), nullable=False),
        sa.Column('used_at', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['physical_assessment_requests.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti', name='uq_marketplace_handoff_jti'),
    )
    with op.batch_alter_table('marketplace_handoffs', schema=None) as batch_op:
        batch_op.create_index('ix_marketplace_handoffs_expires', ['expires_at'])
        batch_op.create_index('ix_marketplace_handoffs_request', ['request_id'])


def downgrade() -> None:
    with op.batch_alter_table('marketplace_handoffs', schema=None) as batch_op:
        batch_op.drop_index('ix_marketplace_handoffs_request')
        batch_op.drop_index('ix_marketplace_handoffs_expires')
    op.drop_table('marketplace_handoffs')
