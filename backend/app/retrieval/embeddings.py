"""
Jina Embeddings API client.

Uses jina-embeddings-v3 (1024-dim) via the Jina AI API.
Why Jina over local PubMedBERT: GPU-backed API is 100-1000x faster
on CPU-constrained machines, and jina-embeddings-v3 benchmarks at
the top of the MTEB leaderboard for retrieval tasks.
"""
import logging
import os
import random
import time

import httpx

logger = logging.getLogger(__name__)

JINA_API_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v3"
JINA_EMBEDDING_DIM = 1024


class JinaEmbeddingClient:
    """
    Thin wrapper around Jina's embeddings API.

    Batches texts and returns dense vectors. Handles rate limits
    with exponential backoff + jitter.
    """

    def __init__(self, api_key: str | None = None, max_batch_size: int = 256):
        self.api_key = api_key or os.getenv("JINA_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "JINA_API_KEY not set. Get one at https://jina.ai/embeddings/"
            )
        self.max_batch_size = max_batch_size
        self._client = httpx.Client(timeout=300.0)
        # Track last request time for rate limiting
        self._last_request_time = 0.0
        # Minimum gap between requests to stay under rate limits
        self._min_request_gap = 3.0  # seconds

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Encode a list of texts into vectors.

        Returns list of embedding vectors in the same order as input texts.
        """
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i : i + self.max_batch_size]
            embeddings = self._call_api_with_backoff(batch)
            all_embeddings.extend(embeddings)

            processed = min(i + self.max_batch_size, len(texts))
            logger.debug("Encoded %d/%d texts", processed, len(texts))

        return all_embeddings

    def _call_api_with_backoff(self, texts: list[str], max_retries: int = 8) -> list[list[float]]:
        """
        Call the Jina API with exponential backoff + jitter for rate limits.

        Retries on 429 (rate limit) and 5xx errors with increasing delays.
        """
        for attempt in range(max_retries):
            # Enforce minimum gap between requests
            now = time.time()
            since_last = now - self._last_request_time
            if since_last < self._min_request_gap:
                time.sleep(self._min_request_gap - since_last)

            try:
                resp = self._client.post(
                    JINA_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": JINA_MODEL,
                        "input": texts,
                        "embedding_type": "float",
                    },
                )

                self._last_request_time = time.time()

                if resp.status_code == 429:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning("Rate limited (429). Waiting %.1fs (attempt %d/%d)...",
                                   wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

                # Jina returns: {"data": [{"object": "embedding", "index": 0, "embedding": [...]}, ...]}
                items = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in items]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning("Rate limited. Waiting %.1fs (attempt %d/%d)...",
                                   wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue
                raise
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning("Timeout. Waiting %.1fs (attempt %d/%d)...",
                                   wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"Failed after {max_retries} retries for batch of {len(texts)} texts")

    def close(self):
        self._client.close()
