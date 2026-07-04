import logging
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import execute_values

# Load .env from project root so DATABASE_URL is always available
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
if os.path.isfile(_env_path):
    load_dotenv(_env_path)

logger = logging.getLogger(__name__)

# Connection pool singleton
_connection_pool: pool.ThreadedConnectionPool | None = None


def get_db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://selfrag:selfrag@localhost:5432/selfrag")


def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    global _connection_pool
    url = get_db_url()
    _connection_pool = pool.ThreadedConnectionPool(minconn, maxconn, url)
    logger.info("Database connection pool initialized (min=%d, max=%d)", minconn, maxconn)


@contextmanager
def _db_connection():
    """Private context manager to handle pool leases, pgvector registry, transactions, and cleanup."""
    global _connection_pool
    if _connection_pool is None:
        init_pool()
    conn = _connection_pool.getconn()
    try:
        try:
            import pgvector.psycopg2 as pgv
            pgv.register_vector(conn)
        except ImportError:
            pass  # pgvector not installed — vector queries will fail later
        
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if _connection_pool is not None:
            _connection_pool.putconn(conn)


# ---------------------------------------------------------------------------
# Public Domain Repository API
# ---------------------------------------------------------------------------

def query_dense(query_embedding: list[float], limit: int) -> list[dict]:
    """Execute vector cosine distance search over documents."""
    results = []
    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source_pmid, text,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM documents
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, limit),
            )
            for rank, row in enumerate(cur.fetchall(), start=1):
                results.append({
                    "id": row[0],
                    "source_pmid": row[1],
                    "text": row[2],
                    "score": float(row[3]),
                    "rank": rank,
                    "method": "dense",
                })
    return results


def query_keyword(query: str, limit: int) -> list[dict]:
    """Execute full-text keyword search using tsvector/tsquery."""
    results = []
    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source_pmid, text,
                       ts_rank(tsv, plainto_tsquery('english', %s)) AS rank_score
                FROM documents
                WHERE tsv @@ plainto_tsquery('english', %s)
                ORDER BY rank_score DESC
                LIMIT %s
                """,
                (query, query, limit),
            )
            for rank, row in enumerate(cur.fetchall(), start=1):
                results.append({
                    "id": row[0],
                    "source_pmid": row[1],
                    "text": row[2],
                    "score": float(row[3]),
                    "rank": rank,
                    "method": "keyword",
                })
    return results


def bulk_insert_documents(rows: list[tuple[str, str, list[float]]]) -> int:
    """Insert multiple documents and their embeddings efficiently."""
    sql = """
        INSERT INTO documents (source_pmid, text, embedding)
        VALUES %s
    """
    with _db_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows, template="(%s, %s, %s::vector)", page_size=1000)
        logger.info("Bulk inserted %d rows", len(rows))
        return len(rows)


def run_schema() -> None:
    """Read and apply database tables schema."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        sql = f.read()

    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("Schema applied successfully")


def count_documents() -> int:
    """Count the total number of documents present in the corpus."""
    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM documents")
            count = cur.fetchone()[0]
    return count


def build_indexes() -> None:
    """Create HNSW cosine distance and GIN lexical indexes on the documents table."""
    with _db_connection() as conn:
        logger.info("Building HNSW index on embedding column (this may take several minutes)...")
        with conn.cursor() as cur:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_embedding "
                "ON documents USING hnsw (embedding vector_cosine_ops)"
            )
        logger.info("HNSW index built.")

        logger.info("Building GIN index on tsv column...")
        with conn.cursor() as cur:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_tsv "
                "ON documents USING gin (tsv)"
            )
        logger.info("GIN index built.")
