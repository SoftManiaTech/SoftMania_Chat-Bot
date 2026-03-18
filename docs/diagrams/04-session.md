# Session & History Flow

Short: session HMAC validation → optional history fetch (respecting `HISTORY_MAX_TURNS`) → inject chat_history into agent context → log turns and feedback.

```mermaid
flowchart TD
  subgraph SessionFlow
    Client[Widget] -->|send session_id/token| API[POST /query or /history]
    API --> Validate[validate_or_create_session]
    Validate --> DBRecord[`chat_sessions` row]
    API -->|if HISTORY_MAX_TURNS>0| GetHist[get_session_history(max_turns)]
    GetHist --> LangGraph
    LangGraph --> API
    API --> append_turn[append_turn() → `query_logs`]
    Client -->|submit feedback| API
    API --> save_feedback[save_feedback()]
  end

  classDef db fill:#f9f,stroke:#333;
  class DBRecord,append_turn,save_feedback db

```

Security notes:
- Move tokens to HttpOnly cookies for production.
- Set a secure `SESSION_HMAC_SECRET` in env; do not use default.