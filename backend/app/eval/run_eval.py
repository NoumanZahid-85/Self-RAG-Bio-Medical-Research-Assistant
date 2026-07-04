"""
Phase 3: Evaluation Harness
===========================
Runs the Self-RAG pipeline against the PubMedQA labeled set and reports
metrics: faithfulness, answer relevancy, context precision, context recall.

Usage:
    python -m backend.app.eval.run_eval --sample 5
    python -m backend.app.eval.run_eval --sample 0  (full 500)
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

from datasets import load_dataset
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tqdm import tqdm

from ..llm.client import LLMClient
from ..rag.graph import run_selfrag

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval")

FAITHFULNESS_THRESHOLD = 0.85
ANSWER_RELEVANCY_THRESHOLD = 0.80
CONTEXT_PRECISION_THRESHOLD = 0.50
CONTEXT_RECALL_THRESHOLD = 0.50


class FaithfulnessScore(BaseModel):
    total_claims: int = Field(description="Total number of factual claims in the answer")
    supported_claims: int = Field(description="Number of claims supported by the source documents")
    reasoning: str = Field(description="Brief explanation")


class RelevancyScore(BaseModel):
    score: float = Field(description="Relevance score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation")


class RecallScore(BaseModel):
    score: float = Field(description="Recall score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation")


FAITHFULNESS_PROMPT = """You are a biomedical fact-checker. I will give you an ANSWER and the
SOURCE DOCUMENTS it was based on. Extract each factual claim from the answer and check whether
it is supported by the source documents."""

ANSWER_RELEVANCY_PROMPT = """You are a biomedical QA evaluator. Determine whether the ANSWER
actually addresses the QUESTION. Score from 0.0 (completely irrelevant) to 1.0 (perfectly relevant)."""

CONTEXT_RECALL_PROMPT = """You are a biomedical information retrieval evaluator. Given a GROUND
TRUTH ANSWER and the RETRIEVED DOCUMENTS, determine what fraction of the information needed to
answer is present in the retrieved documents. Score from 0.0 (nothing covered) to 1.0 (fully covered)."""


class ScoringLLMClient:
    """Wrapper that adds structured-output scoring methods to LLMClient."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def score_faithfulness(self, answer: str, context: str) -> FaithfulnessScore:
        if not answer or not context:
            return FaithfulnessScore(total_claims=0, supported_claims=0, reasoning="Empty answer or context")
        user = f"SOURCE DOCUMENTS:\n{context[:3000]}\n\nANSWER:\n{answer}"
        return self._llm.grade(FAITHFULNESS_PROMPT, user, FaithfulnessScore)

    def score_relevancy(self, question: str, answer: str) -> RelevancyScore:
        if not answer:
            return RelevancyScore(score=0.0, reasoning="Empty answer")
        user = f"QUESTION: {question}\n\nANSWER: {answer}"
        return self._llm.grade(ANSWER_RELEVANCY_PROMPT, user, RelevancyScore)

    def score_recall(self, ground_truth: str, context: str) -> RecallScore:
        if not ground_truth or not context:
            return RecallScore(score=0.0, reasoning="Empty ground truth or context")
        user = f"GROUND TRUTH ANSWER:\n{ground_truth[:2000]}\n\nRETRIEVED DOCUMENTS:\n{context[:3000]}"
        return self._llm.grade(CONTEXT_RECALL_PROMPT, user, RecallScore)


def load_gold_set(sample: int = 0):
    ds = load_dataset("qiaojin/PubMedQA", "pqa_labeled", split="train", trust_remote_code=False)
    if sample and sample < len(ds):
        ds = ds.select(range(sample))
    return ds


def extract_context_text(context):
    if isinstance(context, dict):
        return " ".join(context.get("contexts", []))
    return str(context)


def compute_context_precision(graded_docs: list, retrieved_docs: list) -> float:
    if not retrieved_docs:
        return 0.0
    return len(graded_docs) / len(retrieved_docs)


def run_eval(sample: int = 5, output_file: str = None):
    llm = LLMClient()
    scorer = ScoringLLMClient(llm)

    gold = load_gold_set(sample)
    total = len(gold)

    print(f"\n{'='*72}")
    print(f"Running Self-RAG evaluation on {total} questions")
    print(f"{'='*72}\n")

    results = []
    faith_scores = []
    relevancy_scores = []
    precision_scores = []
    recall_scores = []

    for i, row in enumerate(tqdm(gold, desc="Evaluating")):
        question = row["question"]
        ground_truth = str(row.get("long_answer", ""))

        start = time.time()
        try:
            rag_result = run_selfrag(question, llm=llm)
        except Exception as e:
            logger.error("Pipeline failed for q %d: %s", i, e)
            rag_result = {
                "generation": "", "documents": [],
                "graded_documents": [], "abstained": True, "graph_path": [],
            }
        elapsed = time.time() - start

        answer = rag_result.get("generation", "")
        retrieved_texts = [d.get("text", "") for d in rag_result.get("documents", [])]
        retrieved_context = "\n\n".join(retrieved_texts[:5])
        graded_docs = rag_result.get("graded_documents", [])

        fs = scorer.score_faithfulness(answer, retrieved_context)
        rs = scorer.score_relevancy(question, answer)
        precision = compute_context_precision(graded_docs, rag_result.get("documents", []))
        rcs = scorer.score_recall(ground_truth, retrieved_context)

        faith = fs.supported_claims / fs.total_claims if fs.total_claims > 0 else (1.0 if not answer else 0.0)
        faith_scores.append(faith)
        relevancy_scores.append(rs.score)
        precision_scores.append(precision)
        recall_scores.append(rcs.score)

        result = {
            "index": i,
            "question": question,
            "answer": answer[:300],
            "ground_truth": ground_truth[:300],
            "abstained": rag_result.get("abstained", False),
            "graph_path": rag_result.get("graph_path", []),
            "retrieved_count": len(rag_result.get("documents", [])),
            "graded_relevant": len(graded_docs),
            "faithfulness": round(faith, 4),
            "answer_relevancy": round(rs.score, 4),
            "context_precision": round(precision, 4),
            "context_recall": round(rcs.score, 4),
            "elapsed_seconds": round(elapsed, 1),
        }
        results.append(result)

        print(f"\n  [{i+1}/{total}] Faith={faith:.2f} Rel={rs.score:.2f} "
              f"Prec={precision:.2f} Rec={rcs.score:.2f} "
              f"Abstain={result['abstained']} Path={'->'.join(result['graph_path'])}")

    avg_faith = sum(faith_scores) / len(faith_scores) if faith_scores else 0
    avg_rel = sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0
    avg_prec = sum(precision_scores) / len(precision_scores) if precision_scores else 0
    avg_rec = sum(recall_scores) / len(recall_scores) if recall_scores else 0

    print(f"\n{'='*72}")
    print("EVALUATION REPORT")
    print(f"{'='*72}")
    print(f"  Questions evaluated: {total}")
    def _pass_fail(score: float, threshold: float) -> str:
        return "PASS" if score >= threshold else "FAIL"

    print(f"  Average faithfulness:     {avg_faith:.4f}  (threshold: {FAITHFULNESS_THRESHOLD})"
          f" {_pass_fail(avg_faith, FAITHFULNESS_THRESHOLD)}")
    print(f"  Average answer relevancy: {avg_rel:.4f}  (threshold: {ANSWER_RELEVANCY_THRESHOLD})"
          f" {_pass_fail(avg_rel, ANSWER_RELEVANCY_THRESHOLD)}")
    print(f"  Average context precision:{avg_prec:.4f}  (threshold: {CONTEXT_PRECISION_THRESHOLD})"
          f" {_pass_fail(avg_prec, CONTEXT_PRECISION_THRESHOLD)}")
    print(f"  Average context recall:   {avg_rec:.4f}  (threshold: {CONTEXT_RECALL_THRESHOLD})"
          f" {_pass_fail(avg_rec, CONTEXT_RECALL_THRESHOLD)}")
    print(f"  Abstain rate: {sum(1 for r in results if r['abstained']) / len(results) * 100:.1f}%")
    print(f"{'='*72}\n")

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "config": {"sample": sample, "total": total, "timestamp": datetime.now().isoformat()},
                "thresholds": {
                    "faithfulness": FAITHFULNESS_THRESHOLD,
                    "answer_relevancy": ANSWER_RELEVANCY_THRESHOLD,
                    "context_precision": CONTEXT_PRECISION_THRESHOLD,
                    "context_recall": CONTEXT_RECALL_THRESHOLD,
                },
                "aggregate": {
                    "avg_faithfulness": round(avg_faith, 4),
                    "avg_answer_relevancy": round(avg_rel, 4),
                    "avg_context_precision": round(avg_prec, 4),
                    "avg_context_recall": round(avg_rec, 4),
                    "abstain_rate": round(sum(1 for r in results if r['abstained']) / len(results), 4),
                },
                "results": results,
            }, f, indent=2)
        print(f"Results saved to: {output_file}")

    all_pass = avg_faith >= FAITHFULNESS_THRESHOLD and avg_rel >= ANSWER_RELEVANCY_THRESHOLD
    if not all_pass:
        print("EVALUATION FAILED: thresholds not met")
        sys.exit(1)
    else:
        print("EVALUATION PASSED: all thresholds met")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Self-RAG Evaluation Harness (Phase 3)")
    parser.add_argument("--sample", type=int, default=5, help="Number of questions to evaluate (0 = all)")
    parser.add_argument("--output", type=str, default=None, help="JSON output file")
    args = parser.parse_args()
    if args.sample == 0:
        args.sample = None
    if args.output is None:
        args.output = f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    run_eval(sample=args.sample, output_file=args.output)


if __name__ == "__main__":
    main()
