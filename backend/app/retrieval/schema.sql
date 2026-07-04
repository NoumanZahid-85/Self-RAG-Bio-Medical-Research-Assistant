-- =============================================================================
-- Self-RAG Phase 1: Retrieval Corpus Schema
-- =============================================================================
-- Why dense vector + tsvector in the same table: one query can do hybrid
-- search (cosine similarity + full-text) without a join across two stores.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    source_pmid TEXT,
    text TEXT NOT NULL,
    embedding vector(1024),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
);

-- HNSW index on the embedding column for fast approximate nearest-neighbor search.
-- Why HNSW over IVFFlat: better recall at equivalent speed for this corpus size (~211k rows).
-- Why loaded AFTER data (task 5.3): building the index against a populated table
-- is far faster than building incrementally during inserts.
-- Run this after ingestion completes:
--   CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

-- GIN index on the tsvector column for the full-text search side of hybrid retrieval.
-- Also built after loading for the same performance reason.
-- Run this after ingestion completes:
--   CREATE INDEX ON documents USING gin (tsv);
