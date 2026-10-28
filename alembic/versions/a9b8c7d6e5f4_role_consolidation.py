"""Consolidate legacy user role into is_admin and user_type.

Revision ID: a9b8c7d6e5f4
Revises: 4d8a1c7f9b20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a9b8c7d6e5f4"
down_revision = "4d8a1c7f9b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    users = sa.table(
        "users",
        sa.column("role", sa.String),
        sa.column("user_type", sa.String),
        sa.column("is_admin", sa.Boolean),
    )

    bind.execute(
        users.update()
        .where(sa.func.lower(users.c.role).in_(("admin", "super_admin")))
        .values(is_admin=True)
    )
    bind.execute(
        users.update()
        .where(sa.and_(users.c.user_type.is_(None), users.c.is_admin.is_(True)))
        .values(user_type="admin")
    )
    bind.execute(
        users.update()
        .where(sa.and_(users.c.user_type.is_(None), sa.func.lower(users.c.role) == "bidder"))
        .values(user_type="bidder")
    )
    bind.execute(
        users.update().where(users.c.user_type.is_(None)).values(user_type="client")
    )
    bind.execute(
        users.update().where(users.c.role.is_(None)).values(role=users.c.user_type)
    )


def downgrade() -> None:
    # Data consolidation is intentional and safe to keep. The legacy column is
    # retained, so no schema rollback is required.
    pass
