---
title: SoftMania Chat-Bot
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# SoftMania Chat-Bot 🚀

This repository implements the SoftMania multi-hop reasoning/chat agent. The README is split section-by-section to make the codebase, deployment, and Hugging Face Spaces requirements explicit and easy to follow.

**Quick links (section map)**

- **Overview & Architecture** — this section
- **Prerequisites & Environment** — `Environment` below
- **Run Locally / Docker** — `Running the App`
- **Hugging Face Spaces deployment** — `Hugging Face Deployment` (required frontmatter + secrets)
- **API Reference** — `API Reference`
- **Code Map (section-by-section)** — `Code Map`
- **Troubleshooting & Notes** — `Troubleshooting`

## Overview & Architecture

SoftMania is a hybrid retrieval and reasoning engine combining:
- A Neon PGVector vector store for semantic search.
- A Neo4j knowledge graph for entity linking and traversals.
- A LangGraph workflow orchestrating router → retriever → compressor → synthesizer nodes.

The service exposes a small FastAPI that powers an embeddable `static/widget.html` chat UI.

**System Data Flow:** For a comprehensive overview of the isolated ingestion and query pipelines, view the [Application Data Flow Diagram](docs/diagrams/10-application-data-flow.md).

## Prerequisites & Environment

- Python 3.11+ (virtualenv recommended)
- A Neon/Postgres instance with `pgvector` enabled (set `NEON_DATABASE_URL`)
- A Neo4j instance (set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`)
- A Mistral AI API key (set `MISTRAL_API_KEY`)

Create a `.env` in the project root (or set Spaces secrets):

```
MISTRAL_API_KEY=your_key
NEON_DATABASE_URL=postgresql://user:pass@host:port/dbname
NEO4J_URI=bolt://neo4j-host:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
SESSION_HMAC_SECRET=replace-this-with-a-secure-random-value
SESSION_EXPIRY_HOURS=72
SESSION_COOKIE_SECURE=1
LOCAL_EMBEDDING_MODEL=true
```

NOTE: For Hugging Face Spaces, set the same values as *Repository secrets* (in the Spaces settings) or add them to the container environment.

## Running the App

1. Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

2. Run locally:

```bash
python main.py
```

The service will be available at `http://localhost:7860` by default.

### Docker / Container

- This repo includes a `Dockerfile` and `docker-compose.yml` for containerized runs. The project frontmatter uses `sdk: docker` to support Hugging Face Spaces Docker deployments.

## Hugging Face Deployment (Spaces) — required mapping

Hugging Face Spaces uses the YAML frontmatter at the top of `README.md` to detect deployment settings when `sdk: docker` is used. The existing frontmatter is mandatory and must include at minimum:

- `sdk: docker` — instructs Spaces to build the provided `Dockerfile`.
- `app_port` — port the container listens on (7860 in this repo).

Recommended additional items (already present): `title`, `emoji`, `pinned`.

Spaces Secrets: ensure these environment variables are set in the Spaces UI:
- `MISTRAL_API_KEY`
- `NEON_DATABASE_URL`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- `SESSION_HMAC_SECRET`

Health check & startup: `src/api/server.py` runs `setup_pgvector_tables()` at startup to create necessary DB tables; ensure the DB user can create tables or run migrations separately.

## API Reference

- `POST /ingest` — Upload a document for ingestion (chunks → vector + graph). See [src/api/server.py](src/api/server.py#L1-L120).
- `POST /query` — Ask a question; session-aware HMAC authentication is used. See [src/api/server.py](src/api/server.py#L120-L260).
- `POST /history` — Get full session history for UI rendering. See [src/api/server.py](src/api/server.py#L260-L340).
- `POST /feedback` — Submit like/dislike for an assistant message. See [src/api/server.py](src/api/server.py#L340-L420).
- `DELETE /clear` — Purge vectors and graph. See [src/api/server.py](src/api/server.py#L420-L500).

## Code Map — section-by-section

- `main.py` — application entrypoint and optional Hugging Face token/tokenizer pre-download. See [main.py](main.py#L1-L40).
- `src/config.py` — central configuration and helpers for LLM/DB clients. See [src/config.py](src/config.py#L1-L140).
- `src/api/server.py` — FastAPI endpoints, session HMAC logic, and startup DB setup. See [src/api/server.py](src/api/server.py#L1-L200).
- `src/agent/` — LangGraph workflow and nodes:
  - `graph.py` — StateGraph definition and routing logic. See [src/agent/graph.py](src/agent/graph.py#L1-L120).
  - `nodes.py` — router, decomposer, compressor, synthesizer node implementations. See [src/agent/nodes.py](src/agent/nodes.py#L1-L140).
  - `retrievers.py` — hybrid retriever combining Neon + Neo4j traversals. See [src/agent/retrievers.py](src/agent/retrievers.py#L1-L120).
- `src/ingestion/` — ingestion pipeline:
  - `orchestrator.py` — orchestrates loading, chunking, embedding, and graph extraction. See [src/ingestion/orchestrator.py](src/ingestion/orchestrator.py#L1-L120).
  - `vector_db.py` — PGVector schema setup, batch inserts, and semantic search. See [src/ingestion/vector_db.py](src/ingestion/vector_db.py#L1-L140).
  - `graph_db.py` — Neo4j inserts and clear operations. See [src/ingestion/graph_db.py](src/ingestion/graph_db.py#L1-L80).
  - `chunker.py`, `extractor.py` — chunk creation and LLM-based extraction.
- `src/prompts.py` + `src/prompts.yaml` — centralized prompt templates and guardrails used by agent nodes. See [src/prompts.py](src/prompts.py#L1-L60) and [src/prompts.yaml](src/prompts.yaml).
- `static/widget.html` — embeddable chat widget and UX (fullscreen, theme toggle, feedback buttons). See [static/widget.html](static/widget.html#L1-L120).
- `tests/` — contains basic tests and benchmarks.

## Recent Security & Architecture Updates

1. **Config Centralization**: All environmental variables are centrally validated and managed within `src/config.py`, making typing and default resolution deterministic across the application.
2. **Secure Cookies**: Cross-Site Scripting (XSS) and interception protections are deeply integrated. When `SESSION_COOKIE_SECURE=1` is configured, session authentication defaults to `HTTP-Only Secure` cookies, replacing unencrypted JSON body exposure over non-HTTPS lines.
3. **Local Embedding Isolation**: Ingestion processes now exclusively enforce the usage of local `e5-mistral-7b-instruct` embeddings to mitigate massive rate limits on external endpoints. If `LOCAL_EMBEDDING_MODEL=false`, the system gracefully halts the `/ingest` route, leaving the Mistral API totally dedicated to semantic user query generation.

## Troubleshooting & Notes

- If DB table creation fails on startup, verify `NEON_DATABASE_URL` has DDL privileges or run `setup_pgvector_tables()` from a DB-admin session.
- Ensure `SESSION_HMAC_SECRET` is set to a strong random value in production; rotating this will invalidate existing session tokens.
- `Config.HISTORY_MAX_TURNS` controls whether the server fetches history for LLM context (0 disables history; see `src/api/server.py` change to skip history when 0).

## Contributing

Please open issues or PRs for feature requests, bug fixes, or documentation updates.

---
*This README was programmatically expanded to include a section-by-section map and explicit Hugging Face Spaces deployment notes.*

## Analysis Report

A consolidated, actionable analysis of implemented features, operational notes, verification steps, and recommended next actions has been created: [docs/analysis_report.md](docs/analysis_report.md)

