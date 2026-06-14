"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("settings", sa.JSON, nullable=True, server_default="{}"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("workspace_id", sa.String, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("mime_type", sa.String, nullable=True),
        sa.Column("status", sa.String, server_default="pending"),
        sa.Column("source", sa.String, nullable=True),
        sa.Column("owner_id", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("document_id", sa.String, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("workspace_id", sa.String, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("chunk_metadata", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("embedding_model", sa.String, server_default="text-embedding-3-small"),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )
    op.create_index("ix_chunks_workspace_id", "chunks", ["workspace_id"])
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("workspace_id", sa.String, nullable=False),
        sa.Column("user_id", sa.String, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("conversation_id", sa.String, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", sa.JSON, nullable=True, server_default="[]"),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.drop_index("ix_chunks_workspace_id", "chunks")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("workspaces")
