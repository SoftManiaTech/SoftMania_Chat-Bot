# SoftMania — Consolidated Feature Analysis

This document summarizes implemented features, operational notes, verification steps, and recommended next actions for each major part of the repository.

## 1. main.py — Entrypoint & model pre-download
- Features: sets `HF_HOME`, pre-downloads tokenizer artifacts via `snapshot_download`, starts Uvicorn server.
- Notes: pre-download is optional (fails safely); `reload=True` is enabled (dev only).
- Verify: run `python main.py` and confirm `.cache/huggingface` populated and server starts.
- Next: make `reload` conditional; make `model_id` configurable via env.

## 2. src/config.py — Central configuration
- Features: LLM/embedding factories, `get_pg_pool`, `get_neo4j_graph`, runtime hyperparameters (chunk size, TOP_K, hop limits, history retention, rate limits).
- Notes: `NEON_DATABASE_URL` required; `SESSION_HMAC_SECRET` default is insecure; embedding dim and pool sizes are tuned for Neon.
- Verify: call `await Config.get_pg_pool()` and `Config.get_neo4j_graph()` in a test environment.
- Next: add retries/backoff and expose model names via env.

## 3. src/api — FastAPI server, sessions, endpoints
- Features: `/ingest`, `/query`, `/history`, `/feedback`, `/clear`, landing page, session HMAC lifecycle, startup DB table creation.
- Notes: history fetch skipped when `HISTORY_MAX_TURNS=0`; CORS wide-open; no server-side rate limiter yet.
- Verify: exercise `/query` flows, session creation, history toggling, and `append_turn` consequences.
- Next: add per-session rate-limiting middleware; restrict CORS for production; add upload size limits.

## 4. src/agent — Graph workflow and nodes
- Features: LangGraph StateGraph with nodes `router`, `decomposer`, `retriever`, `compressor`, `synthesizer`; hybrid retriever combining PGVector + Neo4j traversals; structured outputs and guardrails; multi-hop looping with hop limit.
- Notes: `_GRAPH_CACHE` is in-memory; Neo4j calls run in threadpool; synthesizer returns `is_sufficient` to control loops.
- Verify: unit test router classification, integration test multi-hop flows, confirm `retrieved_context` accumulation.
- Next: add cache TTL, monitor Neo4j threading, add metrics for hop counts and latency.

## 5. src/ingestion — Orchestrator, vector_db, graph_db, chunker, extractor
- Features: multi-format loaders, chunking via RecursiveCharacterTextSplitter, Mistral embeddings + PGVector storage, LLM-driven KG extraction, Neo4j insertions, schema setup and index creation.
- Notes: migration strategy currently truncates table on embedding-dim mismatch (dangerous); extractor uses synchronous `.invoke()`; ingestion assumes DDL permissions at startup.
- Verify: ingest sample docs and check `document_chunks` and Neo4j nodes/relations.
- Next: implement safe migrations, async extraction or batching, and retries/backoff for external calls.

## 6. src/prompts.py + src/prompts.yaml — Prompts & guardrails
- Features: YAML-driven prompts and guardrails, ChatPromptTemplates for nodes, synthesizer link injection rules and strict guardrails to reduce hallucination.
- Notes: editing YAML updates runtime behavior; keep prompt changes reviewable and versioned.
- Verify: run nodes with adversarial prompts in staging to confirm guardrail behavior.
- Next: add prompt versioning and CI checks for prompt syntax.

## 7. static/widget.html — Frontend chat widget
- Features: embeddable floating widget, fullscreen, theme toggle, session persistence, history loading, message rendering with basic markdown conversion, like/dislike feedback.
- Notes: client stores tokens in `localStorage` (not HttpOnly); markdown sanitizer is minimal — potential XSS risk.
- Verify: embed widget and validate session flows, feedback persistence, and history rendering.
- Next: integrate DOMPurify or safe renderer, support cookie-based sessions, surface rate-limit and session-expiry UI.

## 8. tests — Benchmarks & test coverage
- Features: benchmarking scripts (`benchmark_mistral.py`, `benchmark_ragas.py`) and an empty test placeholder.
- Notes: functional and unit test coverage is minimal; benchmarks assume large local resources.
- Verify: run benchmark scripts in a prepared environment.
- Next: add pytest unit tests for critical logic (sessions, append_turn, semantic_search, router_node). Integrate with CI.

## Overall recommendations
- Add server-side rate-limiting and stricter CORS for production.
- Harden migration and ingestion safety (avoid destructive TRUNCATE on dim mismatch).
- Move sensitive session tokens to HttpOnly cookies or use secure storage.
- Add observability: metrics for request rates, hop counts, retrieval latencies, and cache hit rates.
- Expand automated tests and add a staging job that runs ingestion + sample queries.

---
Generated automatically by repository analysis. For implementation work, pick items from the "Next" lists and I can create focused PRs or code changes.
