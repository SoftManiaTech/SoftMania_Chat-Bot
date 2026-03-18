# Feedback & Ops Flow

Flow for capturing user feedback and operational metrics.

```mermaid
flowchart LR
  UI[Widget like/dislike] --> API[/feedback]
  API --> Validate[validate_or_create_session]
  Validate --> SaveFB[save_feedback() → `query_logs.feedback`]
  SaveFB --> Ack[200 OK]
  SaveFB --> Metrics[Emit metric: feedback.count]
  Metrics --> Monitoring[Monitoring & Alerts]
  Monitoring --> Ops[On-call]
```

Notes:
- Emit metrics for feedback ratio (like/dislike) and trends.
- Use metrics to feed retriever/synthesizer tuning.