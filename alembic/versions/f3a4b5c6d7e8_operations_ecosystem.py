"""operations ecosystem: metrics, incidents, documents, imports

Revision ID: f3a4b5c6d7e8
Revises: 281e6acfaa7b
Create Date: 2026-10-21 08:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = '281e6acfaa7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'operational_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('metric_key', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('period_end', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'metric_key', 'period_end'),
    )
    with op.batch_alter_table('operational_metrics', schema=None) as batch_op:
        batch_op.create_index(
            'ix_operational_metrics_org_key',
            ['organization_id', 'metric_key'], unique=False)

    op.create_table(
        'operational_incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('lane', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('occurred_on', sa.String(), nullable=True),
        sa.Column('shipment_ref', sa.String(), nullable=True),
        sa.Column('customer_impact', sa.Text(), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('corrective_action', sa.Text(), nullable=True),
        sa.Column('owner', sa.String(), nullable=True),
        sa.Column('action_item_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('resolved_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['action_item_id'], ['roadmap_items.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('operational_incidents', schema=None) as batch_op:
        batch_op.create_index(
            'ix_operational_incidents_org_status',
            ['organization_id', 'status'], unique=False)
        batch_op.create_index(
            'ix_operational_incidents_org_occurred',
            ['organization_id', 'occurred_on'], unique=False)

    op.create_table(
        'compliance_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('doc_type', sa.String(), nullable=True),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('owner', sa.String(), nullable=True),
        sa.Column('issued_on', sa.String(), nullable=True),
        sa.Column('expires_on', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('compliance_documents', schema=None) as batch_op:
        batch_op.create_index(
            'ix_compliance_documents_org_expiry',
            ['organization_id', 'expires_on'], unique=False)

    op.create_table(
        'data_imports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('imported_count', sa.Integer(), nullable=True),
        sa.Column('skipped_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('data_imports', schema=None) as batch_op:
        batch_op.create_index(
            'ix_data_imports_org_created',
            ['organization_id', 'created_at'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('data_imports', schema=None) as batch_op:
        batch_op.drop_index('ix_data_imports_org_created')
    op.drop_table('data_imports')

    with op.batch_alter_table('compliance_documents', schema=None) as batch_op:
        batch_op.drop_index('ix_compliance_documents_org_expiry')
    op.drop_table('compliance_documents')

    with op.batch_alter_table('operational_incidents', schema=None) as batch_op:
        batch_op.drop_index('ix_operational_incidents_org_occurred')
        batch_op.drop_index('ix_operational_incidents_org_status')
    op.drop_table('operational_incidents')

    with op.batch_alter_table('operational_metrics', schema=None) as batch_op:
        batch_op.drop_index('ix_operational_metrics_org_key')
    op.drop_table('operational_metrics')
