"""Add guest user fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-28

"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_guest", sa.Boolean, server_default="false", nullable=False))
    op.add_column("users", sa.Column("guest_expires_at", sa.DateTime, nullable=True))
    op.create_index("ix_users_is_guest", "users", ["is_guest"])


def downgrade() -> None:
    op.drop_index("ix_users_is_guest", "users")
    op.drop_column("users", "guest_expires_at")
    op.drop_column("users", "is_guest")
