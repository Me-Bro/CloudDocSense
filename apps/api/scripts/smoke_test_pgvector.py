"""
M0 smoke test: embed 20 FAQ entries -> cosine query -> return best match.
Run: DATABASE_URL_SYNC=... OPENAI_API_KEY=... python -m scripts.smoke_test_pgvector
"""
import os
import sys

import psycopg2
from openai import OpenAI

FAQ = [
    ("What is DocSense?", "DocSense is an AI-powered document intelligence platform."),
    ("How do I upload a document?", "Use the Upload tab and drag-drop your file."),
    ("What file types are supported?", "PDF, DOCX, TXT, and scanned images via OCR."),
    ("How are answers grounded?", "Answers are generated only from retrieved document chunks."),
    ("What happens when no answer is found?", "DocSense returns a 'not found' response with no hallucination."),
    ("Is my data secure?", "Data is tenant-isolated by workspace_id; no cross-tenant access."),
    ("Can I query multiple documents?", "Yes, all documents in a workspace are searched together."),
    ("What embedding model is used?", "OpenAI text-embedding-3-small by default."),
    ("How is chunking done?", "LlamaIndex semantic chunking at ~500 tokens with overlap."),
    ("What is a citation?", "Each answer claim is linked to the source chunk and page number."),
    ("How do I add team members?", "Admins can invite members via the Workspace settings."),
    ("What are the user roles?", "admin, member, and viewer — each with different permissions."),
    ("Is there a cost dashboard?", "Yes, usage_events tracks per-query token and cost data."),
    ("Can DocSense handle scanned documents?", "Yes, vision models extract text from scanned/image docs."),
    ("What is the confidence threshold?", "Chunks below the threshold trigger a 'not found' response."),
    ("How long does ingestion take?", "Typically seconds for text; minutes for large scanned PDFs."),
    ("What is LangGraph used for?", "Complex multi-hop queries run through a capped LangGraph agent."),
    ("What is LlamaIndex used for?", "Retrieval: VectorStoreIndex over pgvector."),
    ("Is streaming supported?", "Yes, answers stream token-by-token via SSE."),
    ("Where is data stored?", "Vectors in pgvector (PostgreSQL), files in MinIO/S3."),
]

QUERY = "How does DocSense prevent hallucinations?"


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    db_url = os.environ.get(
        "DATABASE_URL_SYNC", "postgresql://docsense:docsense@localhost:5432/docsense"
    )

    if not api_key:
        print("OPENAI_API_KEY not set — skipping")
        sys.exit(0)

    client = OpenAI(api_key=api_key)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS smoke_faq (
            id SERIAL PRIMARY KEY,
            question TEXT,
            answer TEXT,
            embedding vector(1536)
        )
    """)
    cur.execute("TRUNCATE smoke_faq")
    conn.commit()

    print(f"Embedding {len(FAQ)} FAQ entries...")
    texts = [f"{q} {a}" for q, a in FAQ]
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    vectors = [e.embedding for e in resp.data]

    for (q, a), vec in zip(FAQ, vectors):
        cur.execute(
            "INSERT INTO smoke_faq (question, answer, embedding) VALUES (%s, %s, %s)",
            (q, a, vec),
        )
    conn.commit()

    print(f"\nQuerying: '{QUERY}'")
    q_resp = client.embeddings.create(model="text-embedding-3-small", input=[QUERY])
    q_vec = q_resp.data[0].embedding

    cur.execute(
        """
        SELECT question, answer, 1 - (embedding <=> %s::vector) AS similarity
        FROM smoke_faq
        ORDER BY embedding <=> %s::vector
        LIMIT 3
        """,
        (q_vec, q_vec),
    )

    rows = cur.fetchall()
    print("\nTop matches:")
    for q, a, sim in rows:
        print(f"  [{sim:.3f}] {q}")
        print(f"           {a}")

    cur.close()
    conn.close()
    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
