"""Resize chunk embedding to 384 dims (local fastembed bge-small-en-v1.5)

Switches the default embedding from OpenAI text-embedding-3-small (1536) to the
free local model. The HNSW index is dropped and recreated because it is bound to
the column's vector dimension.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-21

"""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

NEW_DIM = 384
OLD_DIM = 1536
NEW_MODEL = "BAAI/bge-small-en-v1.5"
OLD_MODEL = "text-embedding-3-small"


def upgrade() -> None:
    # Index is tied to the vector dim — drop before altering the column type.
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    # No safe cast between differently-sized vectors; existing rows are dev data.
    op.execute("UPDATE chunks SET embedding = NULL")
    op.alter_column(
        "chunks",
        "embedding",
        type_=Vector(NEW_DIM),
        existing_nullable=True,
        postgresql_using="NULL",
    )
    op.alter_column("chunks", "embedding_model", server_default=NEW_MODEL)
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute("UPDATE chunks SET embedding = NULL")
    op.alter_column(
        "chunks",
        "embedding",
        type_=Vector(OLD_DIM),
        existing_nullable=True,
        postgresql_using="NULL",
    )
    op.alter_column("chunks", "embedding_model", server_default=OLD_MODEL)
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
