# Ingestion Flow (per document)

Short: load → chunk → embed → store vectors → extract KG → store graph.

```mermaid
sequenceDiagram
  participant Scraper as Scraper/Seed
  participant Orch as Orchestrator
  participant Loader as File Loader
  participant Chunker as Chunker
  participant Emb as Embeddings (Mistral)
  participant VectorDB as PGVector
  participant Extract as Extractor (LLM)
  participant GraphDB as Neo4j

  Scraper->>Orch: enqueue(local file path)
  Orch->>Loader: load file bytes
  Loader->>Orch: return full_text
  Orch->>Chunker: create_chunks(full_text)
  Chunker->>Orch: list chunks

  loop per chunk
    Orch->>Emb: aembed_query(chunk.text)
    Emb-->>Orch: embedding vector
    Orch->>VectorDB: batch_insert_chunks(doc_id, chunk, embedding)
    Orch->>Extract: parse_with_llm(chunk)
    Extract-->>Orch: structured KG extraction
    Orch->>GraphDB: batch_insert_graph(doc_id, chunk_id, extraction)
  end

  Note right of GraphDB: After loop both PGVector and Neo4j
  Note left of Orch: returns ingestion summary (chunks, nodes, rels)

```

Notes / actions:
- Ensure idempotent upserts (avoid duplicates).
- Add retry/backoff around LLM & DB writes.
- Avoid destructive migration (no TRUNCATE in production).