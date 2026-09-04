# 🛡️SentinelPay: AI-Driven Revenue Recovery Layer
> Built for the Razorpay AI Buildathon — **Track 3: AI Revenue Recovery**

SentinelPay is an enterprise-grade payment failure recovery engine. It intercepts payment failure webhooks, bounds an LLM (Gemini 1.5) to diagnose the root cause with strict type safety, and uses database-level idempotency locks to eliminate the risk of duplicate customer charges.

---

##  System Architecture

```mermaid
flowchart TD
    A[Razorpay Payment Gateway] -->|Webhook: payment.failed| B[FastAPI Webhook Ingestion]
    B -->|Immediate 200 OK| A
    B -->|Async Background Task| C[Supabase PostgreSQL]
    C -->|Idempotency Check: webhook_event_id UNIQUE| D{Is Event Duplicate?}
    D -- Yes --> E[Drop Event / Log Conflict]
    D -- No --> F[Bounded AI Diagnostic Layer: Gemini 1.5]
    F -->|Structured JSON Enum| G[Deterministic Policy Engine]
    G -->|Composite Lock: tx_id + action UNIQUE| H{Action Lock Acquired?}
    H -- No --> I[Abort Double Action]
    H -- Yes --> J[Execute Recovery Action]
    J -->|SMART_RETRY| K[Trigger Gateway Retry]
    J -->|SEND_PAYMENT_LINK| L[Dispatch Alternate Invoice Link]
    J -->|MANUAL_REVIEW| M[Escalate to Operator Console]
    C -.->|Real-Time Stream| N[React Operator Dashboard]