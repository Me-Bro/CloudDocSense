FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY worker ./worker

RUN uv pip install --system --no-cache -e .

# Pre-download the embedding model into the image so the Celery worker never
# fetches it at task time (avoids slow/stalled downloads inside forked children).
ARG EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${EMBEDDING_MODEL}')"

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
