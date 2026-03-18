# Overall Architecture

Short: end-to-end system: Browser widget → FastAPI server → LangGraph agent → hybrid retrieval (Neon PGVector + Neo4j) → logs and feedback.

```mermaid
flowchart TD
  subgraph Client
    W["Widget / Browser"] -->|POST /query| API["API Server (`src/api/server.py`)"]
    W -->|POST /ingest| API
    W -->|POST /feedback| API
  end

  subgraph API_Server
    API --> Sess["Session Validation (HMAC) / `chat_sessions`"]
    API --> Links["Portal Links Injection (`portal_links`)"]
    API --> LangGraph["LangGraph Agent (`graph_app`)"]
    API --> DBBootstrap["Startup: setup_pgvector_tables()"]
  end

  subgraph LangGraph
    LangGraph --> Router["Router Node"]
    Router -->|simple| Retriever["Hybrid Retriever"]
    Router -->|complex| Decomposer["Decomposer"] --> Retriever
    Retriever --> Compressor["Compressor"]
    Compressor --> Synthesizer["Synthesizer"]
    Synthesizer -->|final_answer| API
  end

  subgraph Storage
    PG["Neon PGVector (`document_chunks` table)"] ---|vector search| Retriever
    Neo["Neo4j Graph DB"] ---|graph traversal| Retriever
    API ---|writes| QueryLogs["`query_logs` table"]
    API ---|session rows| ChatSessions["`chat_sessions` table"]
    API ---|portal| PortalLinks["`portal_links` table"]
  end

  classDef infra fill:#f3f4f6,stroke:#333;
  class API_Server,LangGraph,Storage infra

```