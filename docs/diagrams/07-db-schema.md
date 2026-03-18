# Storage Schema Overview

ER-like view of the main tables used by the system.

```mermaid
erDiagram
    DOCUMENT_CHUNKS {
        int id PK
        text TEXT
        doc_id TEXT
        chunk_id TEXT
        embedding VECTOR(1024)
        metadata JSONB
    }
    PORTAL_LINKS {
        int id PK
        page_url TEXT
        domain TEXT
        page_type TEXT
        summary TEXT
        created_at TIMESTAMP
    }
    CHAT_SESSIONS {
        text session_id PK
        text hmac_token
        text ip_address
        text device_signature
        created_at TIMESTAMP
        last_active TIMESTAMP
    }
    QUERY_LOGS {
        int id PK
        text session_id FK
        int turn_index
        text role
        text content
        int hop_count
        text feedback
        created_at TIMESTAMP
    }

    DOCUMENT_CHUNKS ||--o{ QUERY_LOGS : "referenced_by"
    CHAT_SESSIONS ||--o{ QUERY_LOGS : "owns"
    PORTAL_LINKS ||--o{ DOCUMENT_CHUNKS : "links_to"
```

Notes:
- `document_chunks.embedding` uses HNSW index for similarity searches.
- Use migrations for schema changes; avoid in-code TRUNCATE.