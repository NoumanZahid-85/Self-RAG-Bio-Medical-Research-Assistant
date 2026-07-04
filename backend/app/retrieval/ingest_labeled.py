"""
Ingest pqa_labeled dataset (~1000 rows) into PostgreSQL.
This ensures all evaluation questions have their respective source documents in the DB.

Run: python -m backend.app.retrieval.ingest_labeled
"""
import logging
import os
import sys
import time
from dotenv import load_dotenv
from datasets import load_dataset
from tqdm import tqdm

from .db import bulk_insert_documents, count_documents
from .embeddings import JINA_EMBEDDING_DIM, JINA_MODEL, JinaEmbeddingClient

# Load .env from project root
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 256
API_DELAY_SECONDS = 2.0

def load_labeled_corpus() -> list[dict]:
    logger.info("Loading PubMedQA pqa_labeled split from Hugging Face...")
    dataset = load_dataset("qiaojin/PubMedQA", "pqa_labeled", split="train", trust_remote_code=False)
    rows = list(dataset)
    logger.info("Loaded %d rows from pqa_labeled", len(rows))
    return rows

def extract_abstract(row: dict) -> str:
    contexts = row.get("context", {})
    if isinstance(contexts, dict):
        sentences = contexts.get("contexts", [])
    elif isinstance(contexts, list):
        sentences = contexts
    else:
        sentences = []
    return " ".join(sentences).strip()

def main():
    logger.info("=== Ingesting pqa_labeled split ===")
    
    # Check current doc count
    initial_count = count_documents()
    logger.info("Initial document count: %d", initial_count)
    
    client = JinaEmbeddingClient()
    rows = load_labeled_corpus()
    
    buffer = []
    total_inserted = 0
    
    # Process in batches
    for i in tqdm(range(0, len(rows), EMBED_BATCH_SIZE), desc="Embedding batches"):
        batch_rows = rows[i : i + EMBED_BATCH_SIZE]
        
        texts = []
        metadata = []
        for row in batch_rows:
            abstract = extract_abstract(row)
            if abstract:
                texts.append(abstract)
                metadata.append(row["pubid"])
                
        if not texts:
            continue
            
        # Encode
        logger.info("Sending %d texts to Jina API...", len(texts))
        embeddings = client.encode(texts)
        
        # Append to buffer
        for pmid, text, emb in zip(metadata, texts, embeddings):
            buffer.append((str(pmid), text, emb))
            
        # Bulk insert
        inserted = bulk_insert_documents(buffer)
        total_inserted += inserted
        buffer.clear()
        
        if API_DELAY_SECONDS > 0:
            time.sleep(API_DELAY_SECONDS)
            
    final_count = count_documents()
    logger.info("Ingestion complete. Total new documents inserted: %d", total_inserted)
    logger.info("Total documents in database: %d", final_count)
    
    client.close()

if __name__ == "__main__":
    main()
