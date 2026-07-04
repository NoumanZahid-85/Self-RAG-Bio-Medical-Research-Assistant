"""
Phase 4: FastAPI Backend Service
=================================
Exposes POST /ask, POST /ask/stream, and GET /health endpoints with rate limiting.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..llm.client import LLMClient
from ..observability.tracing import make_run_config, update_answer_metadata
from ..rag.graph import run_selfrag_streaming
from ..retrieval.db import count_documents
from .queue import GlobalGroqQueue, PerIPRateLimiter

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_llm: LLMClient | None = None
_rate_limiter: PerIPRateLimiter | None = None
_queue: GlobalGroqQueue | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _llm, _rate_limiter, _queue
    logger.info("Starting Self-RAG API...")
    _llm = LLMClient()
    _rate_limiter = PerIPRateLimiter(rpm=int(os.getenv("RATE_LIMIT_PER_IP_RPM", "5")))
    _queue = GlobalGroqQueue(
        max_concurrent=int(os.getenv("GROQ_MAX_CONCURRENT", "5")),
        rpm_budget=int(os.getenv("GROQ_RPM_BUDGET", "25")),
    )
    yield
    logger.info("Shutting down Self-RAG API.")


app = FastAPI(
    title="Self-RAG Biomedical Assistant API",
    description="Retrieval-Augmented Generation pipeline for biomedical literature.",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="Biomedical question")


class AskResponse(BaseModel):
    answer: str = Field(description="Grounded answer or abstention message")
    citations: list[str] = Field(description="Source PMIDs cited in the answer")
    abstained: bool = Field(description="True if pipeline abstained due to insufficient evidence")
    graph_path: list[str] = Field(description="Sequence of graph nodes that fired")


class HealthResponse(BaseModel):
    status: str = Field(description="Overall health status")
    documents_count: int = Field(description="Number of documents in the retrieval corpus")
    groq_available: bool = Field(description="Whether the Groq API client initialized")


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"

    if _rate_limiter and not _rate_limiter.allow(client_ip):
        retry_after = _rate_limiter.retry_after(client_ip)
        logger.warning("Rate limited IP=%s retry_after=%.1fs", client_ip, retry_after)
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)},
        )

    logger.info("Processing question from IP=%s: %s", client_ip, request.question[:80])

    trace_config = make_run_config(
        question=request.question,
        session_id=client_ip,
        tags=["api", client_ip],
    )
    run_id = trace_config.get("run_id", "")

    try:
        async def run():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, run_selfrag_streaming, request.question, _llm, trace_config, None,
            )

        result = await _queue.submit(run())

        citations = []
        for doc in result.get("graded_documents", []):
            pmid = doc.get("source_pmid", "")
            if pmid:
                citations.append(pmid)

        if run_id:
            update_answer_metadata(
                run_id=run_id,
                answer=result.get("generation", ""),
                abstained=result.get("abstained", False),
                graph_path=result.get("graph_path", []),
                citations=citations,
            )

        return AskResponse(
            answer=result.get("generation", ""),
            citations=citations,
            abstained=result.get("abstained", False),
            graph_path=result.get("graph_path", []),
        )
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask/stream")
async def ask_stream(request: AskRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"

    if _rate_limiter and not _rate_limiter.allow(client_ip):
        retry_after = _rate_limiter.retry_after(client_ip)
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)},
        )

    logger.info("Streaming question from IP=%s: %s", client_ip, request.question[:80])

    trace_config = make_run_config(
        question=request.question,
        session_id=client_ip,
        tags=["api", "stream", client_ip],
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        progress_queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def progress_callback(step: str, detail: str = ""):
            try:
                asyncio.get_running_loop().call_soon_threadsafe(
                    progress_queue.put_nowait, {"step": step, "detail": detail}
                )
            except RuntimeError:
                pass

        yield f"data: {__import__('json').dumps({'step': 'started', 'detail': request.question})}\n\n"

        async def run_pipeline():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, run_selfrag_streaming, request.question, _llm, trace_config, progress_callback,
            )

        pipeline_task = asyncio.create_task(_queue.submit(run_pipeline()))

        while True:
            try:
                progress = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                if progress:
                    yield f"data: {__import__('json').dumps(progress)}\n\n"
            except asyncio.TimeoutError:
                pass

            if pipeline_task.done():
                break

        result = pipeline_task.result()

        citations = []
        for doc in result.get("graded_documents", []):
            pmid = doc.get("source_pmid", "")
            if pmid:
                citations.append(pmid)

        yield f"data: {__import__('json').dumps({'step': 'complete', 'answer': result.get('generation', ''), 'citations': citations, 'abstained': result.get('abstained', False), 'graph_path': result.get('graph_path', [])})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    doc_count = 0
    groq_ok = True
    try:
        doc_count = count_documents()
    except Exception as e:
        logger.warning("Health check DB failed: %s", e)
        groq_ok = _llm is not None

    return HealthResponse(
        status="healthy" if doc_count > 0 and groq_ok else "degraded",
        documents_count=doc_count,
        groq_available=groq_ok,
    )
