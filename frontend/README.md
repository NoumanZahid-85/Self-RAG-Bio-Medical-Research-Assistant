# Self-RAG Biomedical Research Assistant

[![CI](https://github.com/your-org/self-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/self-rag/actions/workflows/ci.yml)
[![Deploy](https://github.com/your-org/self-rag/actions/workflows/deploy.yml/badge.svg)](https://github.com/your-org/self-rag/actions/workflows/deploy.yml)

An agentic Self-RAG system that answers biomedical research-verification questions (yes/no/maybe, grounded in PubMed abstracts) using a LangGraph pipeline that retrieves, grades its own retrieval, generates, checks itself for hallucination, and abstains when evidence is weak.

## Frontend

Built with React + TypeScript + Vite + Tailwind.

```bash
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to point at the running FastAPI backend.

## Backend

See `backend/` — FastAPI + LangGraph + pgvector + Groq API.

```bash
docker compose up --build
```

## CI/CD

- **CI:** On every PR to `main` — lint (ruff), unit tests (pytest), and a RAGAS quality gate (conditional on API keys).
- **Deploy:** On merge to `main` — build Docker image and push to GitHub Container Registry.

## License

MIT — built as a portfolio project demonstrating production-grade RAG patterns.
