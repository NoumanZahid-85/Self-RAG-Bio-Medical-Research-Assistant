"""
Phase 2: Core Self-RAG LangGraph Pipeline
=========================================
The heart of the project — a state machine that retrieves, grades, generates,
self-checks, and retries or abstains.
"""
import logging
from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, StateGraph

from ..llm.client import GradeResult, LLMClient
from ..retrieval.hybrid_search import hybrid_search

logger = logging.getLogger(__name__)

MAX_RETRIEVAL_RETRIES = 2
MAX_GENERATION_RETRIES = 2


class SelfRAGState(TypedDict):
    question: str
    documents: list[dict]
    graded_documents: list[dict]
    generation: str
    retrieval_retries: int
    generation_retries: int
    abstained: bool
    graph_path: list[str]
    hallucination_passed: bool
    answer_useful: bool


GRADE_RELEVANCE_SYSTEM = """You are a biomedical relevance judge. Determine whether the provided
document is RELEVANT to answering the question. Consider: does this document discuss the
specific medical intervention, condition, or comparison asked about?

Respond with a structured result:
- score: true if relevant, false if not relevant
- reasoning: brief justification"""

GRADE_HALLUCINATION_SYSTEM = """You are a biomedical fact-checker. Determine whether the ANSWER
is fully SUPPORTED by the provided DOCUMENTS. Check each factual claim in the answer against
the source documents. If any claim cannot be verified from the documents, mark as not supported.

Respond with a structured result:
- score: true if fully grounded/supported, false if any part is not supported
- reasoning: which claims are or aren't supported"""

GRADE_ANSWER_SYSTEM = """You are a biomedical QA evaluator. Determine whether the ANSWER
actually addresses the QUESTION. The answer may be well-written and true, but if it doesn't
answer what was asked, it's not useful.

Respond with a structured result:
- score: true if the answer directly addresses the question, false if it doesn't
- reasoning: brief justification"""

REWRITE_SYSTEM = """You are a biomedical query reformulation assistant. Given a question
that did NOT yield relevant results, rewrite it to improve retrieval. Consider:
1. Add relevant biomedical terminology
2. Be more specific about the intervention and outcome
3. Use language that would appear in a PubMed abstract

Return ONLY the rewritten query text, nothing else."""

GENERATE_SYSTEM = """You are a biomedical research assistant. Answer the question using ONLY
the provided documents. For each key claim, cite the source PMID in brackets like [PMID:12345].

If the documents don't contain enough information to answer confidently, say so.
Do NOT make up information or use knowledge outside the provided documents."""


def _add_path(state: SelfRAGState, node: str) -> None:
    state["graph_path"].append(node)


def retrieve_node(state: SelfRAGState, llm: LLMClient, on_progress: "Callable | None" = None) -> dict:
    _add_path(state, "retrieve")
    if on_progress:
        on_progress("retrieve", "Retrieving relevant biomedical literature")
    logger.info("Retrieving documents for: %s", state["question"])
    docs = hybrid_search(state["question"], k=5)
    if not docs:
        logger.warning("No documents retrieved")
    return {"documents": docs}


def grade_documents_node(state: SelfRAGState, llm: LLMClient, on_progress: "Callable | None" = None) -> dict:
    _add_path(state, "grade_documents")
    if on_progress:
        on_progress("grade_documents", "Grading retrieved evidence for relevance")
    graded = []
    for doc in state["documents"]:
        user_prompt = (
            f"Question: {state['question']}\n\n"
            f"Document: {doc['text'][:2000]}\n\n"
            f"Is this document relevant to answering the question?"
        )
        try:
            result: GradeResult = llm.grade(GRADE_RELEVANCE_SYSTEM, user_prompt)
            if result.score:
                graded.append(doc)
        except Exception as e:
            logger.warning("Grade failed for doc %s: %s", doc.get("source_pmid"), e)

    logger.info("Graded docs: %d relevant out of %d", len(graded), len(state["documents"]))
    return {"graded_documents": graded}


def generate_node(state: SelfRAGState, llm: LLMClient, on_progress: "Callable | None" = None) -> dict:
    _add_path(state, "generate")
    if on_progress:
        on_progress("generate", "Generating grounded answer with citations")
    if not state["graded_documents"]:
        logger.warning("No relevant documents to generate from")
        return {"generation": ""}

    context_parts = []
    for doc in state["graded_documents"]:
        pmid = doc.get("source_pmid", "unknown")
        context_parts.append(f"[PMID:{pmid}] {doc['text']}")

    context = "\n\n".join(context_parts)
    user_prompt = (
        f"Question: {state['question']}\n\n"
        f"Relevant Documents:\n{context}\n\n"
        f"Provide a concise, evidence-based answer with citations."
    )

    try:
        answer = llm.generate(GENERATE_SYSTEM, user_prompt)
        return {"generation": answer}
    except Exception as e:
        logger.error("Generation failed: %s", e)
        return {"generation": ""}


def check_hallucination_node(state: SelfRAGState, llm: LLMClient, on_progress: "Callable | None" = None) -> dict:
    _add_path(state, "check_hallucination")
    if on_progress:
        on_progress("check_hallucination", "Checking for hallucinations against sources")
    if not state["generation"]:
        return {"hallucination_passed": False}

    context_parts = []
    for doc in state.get("graded_documents", state.get("documents", [])):
        context_parts.append(doc["text"][:1500])
    context = "\n\n".join(context_parts)

    user_prompt = (
        f"Documents:\n{context}\n\n"
        f"Answer: {state['generation']}\n\n"
        f"Is the answer fully supported by the documents?"
    )

    try:
        result: GradeResult = llm.grade(GRADE_HALLUCINATION_SYSTEM, user_prompt)
        passed = result.score
        logger.info("Hallucination check: %s (reasoning: %s)", passed, result.reasoning[:100])
    except Exception as e:
        logger.warning("Hallucination check failed: %s", e)
        passed = False

    return {"hallucination_passed": passed}


def grade_answer_node(state: SelfRAGState, llm: LLMClient, on_progress: "Callable | None" = None) -> dict:
    _add_path(state, "grade_answer")
    if on_progress:
        on_progress("grade_answer", "Verifying answer addresses the question")
    if not state["generation"]:
        return {"answer_useful": False}

    user_prompt = (
        f"Question: {state['question']}\n\n"
        f"Answer: {state['generation']}\n\n"
        f"Does this answer actually address the question?"
    )

    try:
        result: GradeResult = llm.grade(GRADE_ANSWER_SYSTEM, user_prompt)
        useful = result.score
        logger.info("Answer grade: %s (reasoning: %s)", useful, result.reasoning[:100])
    except Exception as e:
        logger.warning("Answer grading failed: %s", e)
        useful = False

    return {"answer_useful": useful}


def inc_retrieval_retry(state: SelfRAGState) -> dict:
    """Increment the retrieval retry counter."""
    return {"retrieval_retries": state.get("retrieval_retries", 0) + 1}


def inc_generation_retry(state: SelfRAGState) -> dict:
    """Increment the generation retry counter."""
    return {"generation_retries": state.get("generation_retries", 0) + 1}


def rewrite_query_node(state: SelfRAGState, llm: LLMClient, on_progress: "Callable | None" = None) -> dict:
    _add_path(state, "rewrite_query")
    if on_progress:
        on_progress("rewrite_query", "Rewriting query for better results")
    user_prompt = (
        f"Original question that did NOT yield relevant results: {state['question']}\n\n"
        f"Rewrite this question to find better biomedical evidence."
    )

    try:
        new_query = llm.generate(REWRITE_SYSTEM, user_prompt)
        new_query = new_query.strip().strip('"').strip("'")
        logger.info("Rewritten query: '%s' -> '%s'", state["question"], new_query)
        return {"question": new_query}
    except Exception as e:
        logger.warning("Query rewrite failed: %s", e)
        return {}


def abstain_node(state: SelfRAGState) -> dict:
    _add_path(state, "abstain")
    msg = "Insufficient evidence in the retrieved literature to answer this question confidently."
    logger.info("Abstaining: %s", msg)
    return {
        "generation": msg,
        "abstained": True,
        "hallucination_passed": False,
        "answer_useful": False,
    }


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------

def route_after_grade(state: SelfRAGState) -> str:
    if state.get("graded_documents"):
        return "generate"
    return "no_relevant_docs"


def route_after_hallucination(state: SelfRAGState) -> str:
    if state.get("hallucination_passed"):
        return "grounded"
    retries = state.get("generation_retries", 0)
    if retries < MAX_GENERATION_RETRIES:
        return "retry_generate"
    return "abstain"


def route_after_answer_grade(state: SelfRAGState) -> str:
    if state.get("answer_useful"):
        return "useful"
    retries = state.get("retrieval_retries", 0)
    if retries < MAX_RETRIEVAL_RETRIES:
        return "retry_retrieval"
    return "abstain"


def route_after_rewrite(state: SelfRAGState) -> str:
    if state.get("retrieval_retries", 0) < MAX_RETRIEVAL_RETRIES:
        return "retry_retrieve"
    return "abstain"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(llm: LLMClient, on_progress: "Callable | None" = None) -> StateGraph:
    workflow = StateGraph(SelfRAGState)

    def wrap(fn: Callable):
        def wrapper(state: SelfRAGState) -> dict:
            return fn(state, llm, on_progress)
        return wrapper

    workflow.add_node("retrieve", wrap(retrieve_node))
    workflow.add_node("grade_documents", wrap(grade_documents_node))
    workflow.add_node("generate", wrap(generate_node))
    workflow.add_node("check_hallucination", wrap(check_hallucination_node))
    workflow.add_node("grade_answer", wrap(grade_answer_node))
    workflow.add_node("rewrite_query", wrap(rewrite_query_node))
    workflow.add_node("inc_retrieval_retry", inc_retrieval_retry)
    workflow.add_node("inc_generation_retry", inc_generation_retry)
    workflow.add_node("abstain", abstain_node)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        route_after_grade,
        {
            "generate": "generate",
            "no_relevant_docs": "inc_retrieval_retry",
        },
    )

    workflow.add_edge("inc_retrieval_retry", "rewrite_query")
    workflow.add_edge("generate", "check_hallucination")

    workflow.add_conditional_edges(
        "check_hallucination",
        route_after_hallucination,
        {
            "grounded": "grade_answer",
            "retry_generate": "inc_generation_retry",
            "abstain": "abstain",
        },
    )

    workflow.add_edge("inc_generation_retry", "generate")

    workflow.add_conditional_edges(
        "grade_answer",
        route_after_answer_grade,
        {
            "useful": END,
            "retry_retrieval": "inc_retrieval_retry",
            "abstain": "abstain",
        },
    )

    workflow.add_conditional_edges(
        "rewrite_query",
        route_after_rewrite,
        {
            "retry_retrieve": "retrieve",
            "abstain": "abstain",
        },
    )

    workflow.add_edge("abstain", END)

    return workflow.compile()


def run_selfrag(question: str, llm: LLMClient | None = None, config: dict | None = None) -> dict:
    return run_selfrag_streaming(question, llm, config, None)


def run_selfrag_streaming(question: str, llm: LLMClient | None = None, config: dict | None = None, on_progress: "Callable | None" = None) -> dict:
    if llm is None:
        llm = LLMClient()

    graph = build_graph(llm, on_progress)

    initial_state: SelfRAGState = {
        "question": question,
        "documents": [],
        "graded_documents": [],
        "generation": "",
        "retrieval_retries": 0,
        "generation_retries": 0,
        "abstained": False,
        "graph_path": [],
        "hallucination_passed": False,
        "answer_useful": False,
    }

    logger.info("=== Self-RAG pipeline start ===")
    result = graph.invoke(initial_state, config=config)
    path = result.get("graph_path", [])
    logger.info("=== Self-RAG pipeline complete (path: %s) ===", path)
    return result
