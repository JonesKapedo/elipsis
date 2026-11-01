"""orders, entitlements, and re-score reminders

Revision ID: c4d5e6f7a8b9
Revises: a9b8c7d6e5f4
Create Date: 2026-11-01 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c4d5e6f7a8b9'
down_revision: str | Sequence[str] | None = 'd1e2f3a4b5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('tax_minor', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('provider_reference', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('paid_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_reference', name='uq_orders_provider_reference'),
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index('ix_orders_status', ['status'])
        batch_op.create_index('ix_orders_user', ['user_id'])

    op.create_table(
        'entitlements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('assessment_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('starts_at', sa.String(), nullable=True),
        sa.Column('expires_at', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('entitlements', schema=None) as batch_op:
        batch_op.create_index('ix_entitlements_assessment', ['assessment_id'])
        batch_op.create_index('ix_entitlements_user', ['user_id'])

    op.create_table(
        'rescore_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('cycle', sa.Integer(), nullable=False),
        sa.Column('due_at', sa.String(), nullable=True),
        sa.Column('sent_at', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'cycle', name='uq_rescore_reminder_cycle'),
    )


def downgrade() -> None:
    op.drop_table('rescore_reminders')
    with op.batch_alter_table('entitlements', schema=None) as batch_op:
        batch_op.drop_index('ix_entitlements_user')
        batch_op.drop_index('ix_entitlements_assessment')
    op.drop_table('entitlements')
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index('ix_orders_user')
        batch_op.drop_index('ix_orders_status')
    op.drop_table('orders')
