"""
Phase 1 Task 4: Retrieval Sanity-Check CLI
==========================================
Runs hybrid_search against a handful of known PubMedQA questions and prints
the results so you can manually verify retrieval quality before moving to Phase 2.

Run: python -m backend.app.retrieval.check_retrieval
"""
import sys

from .db import count_documents
from .hybrid_search import hybrid_search

SAMPLE_QUESTIONS = [
    "Do preoperative statins reduce atrial fibrillation after coronary artery bypass grafting?",
    "Does metformin reduce cardiovascular events in type 2 diabetes?",
    "Does aspirin reduce cardiovascular risk in diabetic patients?",
    "Are ACE inhibitors effective for hypertension in elderly patients?",
]


def main():
    count = count_documents()
    print(f"Documents in database: {count}")
    if count == 0:
        print("ERROR: No documents found. Run ingest.py first.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("RETRIEVAL SANITY CHECK")
    print("=" * 70)
    print("For each question, check that the top results are topically")
    print("relevant. If you see off-topic results, check:")
    print("  1. Embedding model loaded correctly (not zero-vectors)")
    print("  2. Full-text index (GIN) was built after ingestion")
    print("  3. HNSW index was built after ingestion")
    print("=" * 70)

    all_good = True
    for question in SAMPLE_QUESTIONS:
        print(f"\n{'─' * 70}")
        print(f"QUERY: {question}")
        print(f"{'─' * 70}")

        results = hybrid_search(question, k=5)

        if not results:
            print("  WARNING: No results returned!")
            all_good = False
            continue

        for i, r in enumerate(results, start=1):
            print(f"  {i}. [RRF={r['rrf_score']:.4f}] {r['source_pmid']}")
            print(f"     \"{r['text'][:150]}...\"")

    print(f"\n{'=' * 70}")
    if all_good:
        print("Sanity check passed. Retrieval is returning results for all queries.")
    else:
        print("WARNING: Some queries returned no results — investigate before Phase 2.")
    print("=" * 70)


if __name__ == "__main__":
    main()
