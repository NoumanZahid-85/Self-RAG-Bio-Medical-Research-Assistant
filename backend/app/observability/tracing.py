"""
LangSmith tracing configuration and helpers.

LangChain auto-traces all LLM + chain invocations when the environment
variables are set. This module provides:
  - A global LangSmith Client for dataset / project interactions.
  - Helpers to build per-request trace metadata so traces are organised
    by question, answer quality, and graph path in the LangSmith UI.
"""
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global client (lazy-init)
# ---------------------------------------------------------------------------
_client: Optional["Client"] = None  # noqa: F821 — imported on demand


def get_client():
    """Return the global langsmith.Client, creating it if necessary.

    The client is intentionally kept as a module-level singleton so that
    all parts of the application share the same API connection pool.
    """
    global _client
    if _client is not None:
        return _client

    try:
        from langsmith import Client as LangSmithClient

        api_key = os.getenv("LANGSMITH_API_KEY")
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        if api_key:
            _client = LangSmithClient(api_url=endpoint, api_key=api_key)
            logger.info("LangSmith client initialised (endpoint=%s)", endpoint)
        else:
            _client = LangSmithClient()  # will be a no-op without env
            logger.info("LangSmith client created (tracing may be disabled — no API key)")
    except Exception:
        logger.warning("Failed to initialise LangSmith client", exc_info=True)
        _client = None

    return _client


# ---------------------------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------------------------

def make_run_config(
    question: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Build a LangGraph invocation config dict that groups traces nicely.

    Each call to ``graph.invoke(initial_state, config=make_run_config(...))``
    will appear as a top-level **Run** in the LangSmith UI.

    Parameters
    ----------
    question:
        The user's question (truncated to 120 chars for metadata).
    session_id:
        Optional grouping key — when set, all runs with the same session_id
        appear under one project "Session" in the LangSmith UI.
    tags:
        Extra tags to attach to the run (e.g. ``["abstained"]``).

    Returns
    -------
    dict
        A config dictionary compatible with ``langgraph.graph.CompiledGraph.invoke``.
    """
    run_id = str(uuid.uuid4())
    metadata = {
        "question": question[:120],
        "question_length": len(question),
        "session_id": session_id or run_id,
    }

    config = {
        "run_name": "Self-RAG Pipeline",
        "run_id": run_id,
        "tags": list(tags or []),
        "metadata": metadata,
    }

    # Enable LangSmith tracing for this run if the environment allows it.
    # When LANGSMITH_TRACING=true this is automatic; setting it here makes
    # the behaviour explicit even when the env var is unset.
    if os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes"):
        config["callbacks"] = None  # let LangChain use its global tracer

    return config


def update_answer_metadata(
    run_id: str,
    answer: str,
    abstained: bool,
    graph_path: list[str],
    citations: list[str],
) -> None:
    """Post-hoc attach answer-level metadata to a finished trace.

    Call *after* the pipeline completes so the trace is enriched with the
    outcome (abstracted / not, path taken, citation count).

    This uses the LangSmith ``Client.update_run`` API.
    """
    client = get_client()
    if client is None:
        return

    try:
        client.update_run(
            run_id=run_id,
            tags=["abstained"] if abstained else ["answered"],
            metadata={
                "answer_length": len(answer),
                "abstained": abstained,
                "graph_path": graph_path,
                "citation_count": len(citations),
                "has_citations": len(citations) > 0,
            },
        )
    except Exception:
        logger.debug("Failed to update run metadata", exc_info=True)


def get_tracer() -> object | None:
    """Return the global LangSmith tracing handler, if available.

    This can be passed as the ``callbacks`` argument to LangChain calls
    when you want to nest them under the current run context.
    """
    try:
        from langchain_core.tracers import LangChainTracer

        client = get_client()
        if client is None:
            return None

        return LangChainTracer(
            project_name=os.getenv("LANGSMITH_PROJECT", "self-rag-pipeline"),
            client=client,
        )
    except Exception:
        return None
