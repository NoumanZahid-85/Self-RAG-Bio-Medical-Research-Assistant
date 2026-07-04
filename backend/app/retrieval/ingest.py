"""
Phase 1 Task 2: Ingestion Script
===============================
Downloads the PubMedQA corpus (pqa_artificial, ~211k rows), embeds each
abstract via Jina Embeddings API, and stores vectors + full-text in pgvector.

Run: python -m backend.app.retrieval.ingest
"""
import logging
import os
import sys
import time
from collections.abc import Iterator

from datasets import load_dataset
from dotenv import load_dotenv
from tqdm import tqdm

from .db import build_indexes, bulk_insert_documents, count_documents, run_schema
from .embeddings import JINA_EMBEDDING_DIM, JINA_MODEL, JinaEmbeddingClient

# Load .env from project root
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Batch sizes for API calls and DB inserts
EMBED_BATCH_SIZE = 256   # texts per API call
INSERT_BATCH_SIZE = 500  # rows per bulk INSERT

# Limit for initial testing (None = full dataset, 5000 = ~20 API calls)
MAX_DOCS = int(os.getenv("MAX_DOCS", "5000"))

# Rate limiting: seconds to wait between API calls (Jina free tier)
API_DELAY_SECONDS = float(os.getenv("API_DELAY_SECONDS", "2.0"))

# If True, embed the entire abstract as one chunk.
CHUNK_BY_ABSTRACT = True


# ---------------------------------------------------------------------------
# Chunking Strategy Decision
# ---------------------------------------------------------------------------
# WHY chunk_by_abstract = True:
# PubMed abstracts are short (150-300 words). For PubMedQA, the
# "final_decision" often depends on whole-abstract inference (e.g.
# comparing intervention vs. control across the full text). Splitting
# would lose cross-sentence reasoning. Whole-abstract chunks preserve
# the reasoning chain.
# ---------------------------------------------------------------------------

def load_pubmedqa_corpus() -> list[dict]:
    """
    Load the pqa_artificial split (~211k rows) — this is the RETRIEVAL CORPUS.
    The eval set (pqa_labeled, 500 rows) is loaded in Phase 3.
    """
    logger.info("Loading PubMedQA pqa_artificial from Hugging Face...")
    dataset = load_dataset("qiaojin/PubMedQA", "pqa_artificial", split="train", trust_remote_code=False)
    rows = list(dataset)
    logger.info("Loaded %d rows from pqa_artificial", len(rows))
    return rows


def chunk_document(row: dict) -> list[str]:
    """
    Chunk a PubMedQA row into text chunk(s).
    """
    contexts = row.get("context", {})

    if isinstance(contexts, dict):
        sentences = contexts.get("contexts", [])
    elif isinstance(contexts, list):
        sentences = contexts
    else:
        sentences = []

    if not sentences:
        return []

    abstract_text = " ".join(sentences).strip()
    if not abstract_text:
        return []

    if CHUNK_BY_ABSTRACT:
        return [abstract_text]

    # Sentence-level fallback: group into 3-5 sentence chunks
    chunks = []
    current_chunk = []
    for i, s in enumerate(sentences):
        current_chunk.append(s)
        if len(current_chunk) >= 4:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


def iter_chunks(rows: list[dict]) -> Iterator[tuple[str, str]]:
    """
    Yield (source_pmid, chunk_text) pairs.
    """
    for i, row in enumerate(rows):
        chunks = chunk_document(row)
        pmid = f"pubmedqa_artificial_{i}"
        for chunk_text in chunks:
            if chunk_text:
                yield (pmid, chunk_text)


def embed_and_store(rows: list[dict], client: JinaEmbeddingClient) -> None:
    """
    Embed all documents in batches via Jina API and bulk-insert into PostgreSQL.
    """
    buffer: list[tuple[str, str, list[float]]] = []

    total_inserted = 0
    api_calls = 0

    chunk_iter = iter_chunks(rows)
    total_rows = len(rows)

    # Progress bar over rows processed
    pbar = tqdm(total=total_rows, desc="Embedding & storing", unit="row")

    while True:
        batch = []
        try:
            while len(batch) < EMBED_BATCH_SIZE:
                batch.append(next(chunk_iter))
        except StopIteration:
            pass

        if not batch:
            break

        texts = [text for _, text in batch]
        metas = [(pmid, text) for pmid, text in batch]

        # Jina API call — fast because it runs on their GPU infra
        embeddings = client.encode(texts)
        api_calls += 1

        # Log progress every 5 API calls
        if api_calls % 5 == 0:
            logger.info("API calls: %d, Documents processed: %d", api_calls, pbar.n)

        # Rate limiting: wait between API calls
        if API_DELAY_SECONDS > 0:
            time.sleep(API_DELAY_SECONDS)

        for (pmid, text), emb in zip(metas, embeddings):
            buffer.append((pmid, text, emb))

        if len(buffer) >= INSERT_BATCH_SIZE:
            inserted = bulk_insert_documents(buffer)
            total_inserted += inserted
            buffer.clear()

        pbar.update(len(batch))

    # Flush remaining buffer
    if buffer:
        inserted = bulk_insert_documents(buffer)
        total_inserted += inserted

    pbar.close()

    logger.info("Ingestion complete. Total chunks inserted: %d", total_inserted)


def main():
    logger.info("=== Phase 1: PubMedQA Ingestion (Jina Embeddings) ===")

    # 1. Initialize Jina client
    client = JinaEmbeddingClient()
    logger.info("Jina Embeddings client initialized (model: %s, dim: %d)",
                JINA_MODEL, JINA_EMBEDDING_DIM)

    # 2. Apply schema (CREATE TABLE etc.)
    run_schema()

    # 3. Load dataset
    rows = load_pubmedqa_corpus()

    # Limit to sample for faster testing
    if MAX_DOCS and MAX_DOCS < len(rows):
        rows = rows[:MAX_DOCS]
        logger.info("Limited to sample of %d documents (MAX_DOCS=%d)", MAX_DOCS, MAX_DOCS)

    # 4. Embed and store
    embed_and_store(rows, client)

    # 5. Build indexes (HNSW + GIN) after data is loaded
    build_indexes()

    # 6. Verify
    count = count_documents()
    logger.info("Verification: %d documents in the table", count)
    if count == 0:
        logger.error("No documents were inserted — something went wrong.")
        sys.exit(1)

    client.close()
    logger.info("=== Phase 1 Complete ===")


if __name__ == "__main__":
    main()
