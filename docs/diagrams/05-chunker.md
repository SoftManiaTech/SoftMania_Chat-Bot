# Chunker Flow

Detailed flow for chunking and chunk metadata generation.

```mermaid
flowchart TD
  A[Raw document text] --> B[RecursiveCharacterTextSplitter]
  B -->|chunk_size=Config.CHUNK_SIZE| C[Chunk pieces]
  C -->|assign metadata| D[Document objects with {doc_id, chunk_id, chunk_index}]
  D --> E[Per-chunk processing (ingestor loop)]
  E --> F[Store chunk text + metadata into `document_chunks`]

  classDef cfg fill:#f3f4f6,stroke:#999
  class B cfg

  subgraph tuning
    note1[Tune CHUNK_SIZE & CHUNK_OVERLAP]
    note2[Test token usage with extraction LLM]
  end

  C --> note1
  C --> note2
```

Notes:
- Keep chunk overlap to preserve sentence boundaries.
- Test different chunk sizes against LLM context limits.