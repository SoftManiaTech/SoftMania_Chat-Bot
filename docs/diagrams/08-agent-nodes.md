# Agent Node Orchestration & Hop Loop

Shows Router → Decomposer → Retriever → Compressor → Synthesizer and hop control.

```mermaid
flowchart TD
  Start[Incoming query] --> Router
  Router -->|off_topic| EndOff[Return refusal]
  Router -->|simple| Retriever
  Router -->|complex| Decomposer
  Decomposer --> Retriever
  Retriever --> Compressor
  Compressor --> Synthesizer
  Synthesizer --> CheckSufficiency{is_sufficient?}
  CheckSufficiency -- yes --> End[Return final answer]
  CheckSufficiency -- no -->|hop_count < MAX_HOP_COUNT| Retriever
  CheckSufficiency -- no -->|hop_count >= MAX_HOP_COUNT| EndFail[Return best-effort answer]

  classDef node fill:#eef2ff,stroke:#777
  class Router,Decomposer,Retriever,Compressor,Synthesizer node
```

Recommendations:
- Enforce `Config.MAX_HOP_COUNT` and per-node timeouts.
- Log guardrail triggers and fallback events.