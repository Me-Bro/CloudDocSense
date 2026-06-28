"""Add users, search_history; wire owner_id FKs

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28

"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("display_name", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # workspaces.owner_id -> users.id
    op.add_column(
        "workspaces",
        sa.Column("owner_id", sa.String, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # documents.owner_id already exists as plain String — add FK constraint + index
    op.create_foreign_key(
        "fk_documents_owner_id_users", "documents", "users", ["owner_id"], ["id"]
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])

    op.create_table(
        "search_history",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String, nullable=False),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("result_count", sa.Integer, server_default="0"),
        sa.Column("doc_ids", sa.JSON, nullable=True, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_search_history_user_id", "search_history", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_search_history_user_id", "search_history")
    op.drop_table("search_history")

    op.drop_index("ix_documents_owner_id", "documents")
    op.drop_constraint("fk_documents_owner_id_users", "documents", type_="foreignkey")

    op.drop_index("ix_workspaces_owner_id", "workspaces")
    op.drop_column("workspaces", "owner_id")

    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
