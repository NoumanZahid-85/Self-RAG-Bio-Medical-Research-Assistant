"""
Phase 2: CLI runner for the Self-RAG pipeline.
Usage: python -m backend.app.rag.cli --question "Your biomedical question?"
"""
import argparse
import logging

from ..rag.graph import run_selfrag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Self-RAG Biomedical Research Assistant")
    parser.add_argument(
        "--question", type=str, required=True,
        help="Biomedical question to answer",
    )
    args = parser.parse_args()

    result = run_selfrag(args.question)

    print("\n" + "=" * 72)
    print("SELF-RAG RESULT")
    print("=" * 72)
    print(f"Question: {args.question}")
    print(f"Graph path: {' -> '.join(result.get('graph_path', []))}")
    print(f"Abstained: {result.get('abstained', False)}")
    print(f"Documents retrieved: {len(result.get('documents', []))}")
    print(f"Relevant documents: {len(result.get('graded_documents', []))}")
    print("-" * 72)
    print("Answer:")
    print(result.get("generation", "No answer generated."))
    print("=" * 72)


if __name__ == "__main__":
    main()
