FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

RUN uv pip install --system --no-cache -e .

# Pre-download the local embedding model so it's cached in the image (offline/fast).
ARG EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${EMBEDDING_MODEL}')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
