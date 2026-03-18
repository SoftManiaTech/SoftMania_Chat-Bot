# Retriever Detail (Hybrid Vector + Graph)

Short: per-sub-query semantic vector search → collect chunk_ids → 1-hop graph traversal → merge results → return retrieved context.

```mermaid
flowchart LR
  subgraph Retriever
    Q[Sub-query(s)] --> Emb[Mistral Embeddings]
    Emb --> VSearch[PGVector Semantic Search]
    VSearch --> ResultsV[Top-K Chunks]
    ResultsV --> Merge[Merge & Rank]
    ResultsV --> GTraverse[Neo4j Traversal (1-hop)]
    GTraverse --> ResultsG[Graph-linked entities]
    ResultsG --> Merge
    Merge --> Context[Build Retrieved Context]
    Context --> Agent[Compressor / Synthesizer]
  end

  style Retriever fill:#fff7ed,stroke:#bbb

```

Tuning / checks:
- Cache graph traversals with TTL.
- Tune `TOP_K_RESULTS` and HNSW params (`m`, `ef_construction`).
- Add fallback broadened search when no results.