"""
Phase 1 Task 3: Hybrid Search with Reciprocal Rank Fusion (RRF)

Combines:
  1. Dense vector search (cosine similarity via Jina Embeddings API)
  2. Full-text keyword search (tsvector + ts_rank)

Fuses results using Reciprocal Rank Fusion (RRF).

Run: python -m backend.app.retrieval.hybrid_search --query "your question"
"""
import argparse
import logging
import sys

from .db import query_dense, query_keyword
from .embeddings import JinaEmbeddingClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RRF_K = 60


class HybridSearcher:
    """
    Performs hybrid (dense + keyword) search over the pgvector `documents` table.
    """

    def __init__(self):
        self._client: JinaEmbeddingClient | None = None

    def _get_client(self):
        if self._client is None:
            self._client = JinaEmbeddingClient()
        return self._client

    def reciprocal_rank_fusion(
        self,
        dense_results: list[dict],
        keyword_results: list[dict],
        k_final: int,
    ) -> list[dict]:
        """
        Fuse two ranked lists using Reciprocal Rank Fusion (RRF).
        RRF score(d) = sum_{r in ranks} 1 / (RRF_K + rank(d, r))
        """
        from collections import defaultdict
        rrf_scores: dict[int, float] = defaultdict(float)
        doc_map: dict[int, dict] = {}

        for doc in dense_results:
            doc_id = doc["id"]
            rrf_scores[doc_id] += 1.0 / (RRF_K + doc["rank"])
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        for doc in keyword_results:
            doc_id = doc["id"]
            rrf_scores[doc_id] += 1.0 / (RRF_K + doc["rank"])
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:k_final]

        results = []
        for doc_id, rrf in fused:
            doc = doc_map[doc_id]
            results.append({
                "id": doc_id,
                "source_pmid": doc["source_pmid"],
                "text": doc["text"],
                "rrf_score": round(rrf, 6),
                "dense_rank": next((d["rank"] for d in dense_results if d["id"] == doc_id), None),
                "keyword_rank": next((d["rank"] for d in keyword_results if d["id"] == doc_id), None),
            })
        return results

    def search(self, query: str, k: int = 10) -> list[dict]:
        """
        Main entry point: runs dense + keyword search, fuses with RRF,
        returns top-k results.
        """
        fetch_k = k * 3
        client = self._get_client()
        query_embedding = client.encode([query])[0]

        dense = query_dense(query_embedding, fetch_k)
        keyword = query_keyword(query, fetch_k)

        if not dense and not keyword:
            logger.warning("No results from either search method for query: %s", query)
            return []

        return self.reciprocal_rank_fusion(dense, keyword, k)


def hybrid_search(query: str, k: int = 10) -> list[dict]:
    """
    Convenience function for other modules to call without dealing with
    the class boilerplate. This is what Phase 2's retrieve_node calls.
    """
    searcher = HybridSearcher()
    return searcher.search(query, k)


def main():
    parser = argparse.ArgumentParser(description="Hybrid search over PubMedQA corpus")
    parser.add_argument("--query", type=str, required=True, help="Natural-language query")
    parser.add_argument("--k", type=int, default=10, help="Number of results (default: 10)")
    args = parser.parse_args()

    results = hybrid_search(args.query, k=args.k)

    if not results:
        print("No results found.")
        sys.exit(0)

    for i, r in enumerate(results, start=1):
        print(f"\n--- Result {i} (RRF: {r['rrf_score']}) ---")
        print(f"  Source: {r['source_pmid']}")
        print(f"  Dense rank: {r['dense_rank']}, Keyword rank: {r['keyword_rank']}")
        text = r["text"]
        if len(text) > 300:
            text = text[:300] + "..."
        print(f"  Text: {text}")


if __name__ == "__main__":
    main()
