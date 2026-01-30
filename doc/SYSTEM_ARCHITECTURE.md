# FinAgent System Architecture

> Complete architecture documentation for the AI Finance Content Intelligence System.

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                       RSS FEEDS (30+ sources)                       │
│         Central Banks | Regulators | News | Crypto | Commodities    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ feedparser
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    run_pipeline.py                                  │
│                 Priority-based Event Selection                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     ADAPTER PIPELINE (9 stages)                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. EmbeddingAdapter     → 384-dim vector (sentence-transformers)│
│  │ 2. DeduplicationAdapter → URL + Semantic check (cosine ≥0.85)  │
│  │ 3. EventTypeAdapter     → 6 types (rule-based)                  │
│  │ 4. IntentAdapter        → 3 intents (rule-based)                │
│  │ 5. ContextAdapter       → LLM generation (Gemini→Groq→Ollama)   │
│  │ 6. ClarityAdapter       → Safety validation                     │
│  │ 7. HITLDecisionAdapter  → Human review decision                 │
│  │ 8. LoggerAdapter        → JSONL log                             │
│  │ 9. DatabaseAdapter      → PostgreSQL + WebSocket notify         │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────┬───────────────────────────┬────────────────────┘
                     │                           │
                     ↓                           ↓
        ┌────────────────────────┐    ┌─────────────────────────────┐
        │      PostgreSQL        │    │  HTTP POST /internal/notify │
        │  ┌──────────────────┐  │    └──────────────┬──────────────┘
        │  │ Event            │  │                   │
        │  │ Output           │  │                   ↓
        │  │ Evaluation       │  │    ┌─────────────────────────────┐
        │  │ ContentQueue     │  │    │    FastAPI (port 8001)      │
        │  └──────────────────┘  │    │    WebSocket Manager        │
        └────────────┬───────────┘    └──────────────┬──────────────┘
                     │                               │ broadcast
                     ↓                               ↓
        ┌────────────────────────────────────────────────────────────┐
        │              RepositoryManager (CRUD Layer)                │
        │   EventRepository | OutputRepository | EvaluationRepository │
        └────────────────────────────────────────────────────────────┘
                     ↑                               │
                     │ REST API                      │ WebSocket /ws
                     │                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  React Dashboard (port 5173)                        │
│   Dashboard | Outputs | Evaluations | ApprovedQueue | Scheduling    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ User Actions
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTENT CURATION FLOW                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │ Evaluate       │→ │ Approve        │→ │ Select for Publishing  │ │
│  │ (PASS/FAIL)    │  │ (to Queue)     │  │ (3-4 items)            │ │
│  └────────────────┘  └────────────────┘  └────────────────────────┘ │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   run_twitter_plugin.py                             │
│               TWITTER PLUGIN ADAPTER PIPELINE (5 stages)            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. FormatDecisionAdapter → SINGLE (280 char) or THREAD        │  │
│  │ 2. TwitterSingleAdapter / TwitterThreadAdapter                │  │
│  │ 3. TwitterClarityAdapter → Twitter-specific validation        │  │
│  │ 4. TwitterHITLAdapter    → Human review decision              │  │
│  │ 5. Save to ContentQueue (status=ready_to_schedule)            │  │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Scheduling Calendar (Dashboard)                 │
│                 POST /api/scheduling/schedule                       │
│                 Set scheduled_for timestamp                         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│              TwitterPublishingWorker (Background Daemon)            │
│         Poll ContentQueue → Find ready items → Publish to X         │
│                      [BLOCKER: API NOT CONNECTED]                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| Pipeline | `run_pipeline.py` | Main content processing orchestrator |
| Twitter Plugin | `run_twitter_plugin.py` | Process approved outputs for X |
| API Server | `api/main.py` | FastAPI backend (port 8001) |
| Publishing Worker | `workers/twitter_publishing_worker.py` | Background tweet publisher |
| Migrations | `run_migrations.py` | Database schema migrations |

---

## Adapter Pipeline (Main)

Sequential processing chain with early exit conditions:

```
Event → ExecutionContext → [Adapter Chain] → Database
```

| # | Adapter | Input | Output | Notes |
|---|---------|-------|--------|-------|
| 1 | EmbeddingAdapter | title, summary | event_embedding (384-dim) | sentence-transformers |
| 2 | DeduplicationAdapter | url, embedding | dedup (DedupResult) | Early exit if duplicate |
| 3 | EventTypeAdapter | title, summary | event_type | Early exit if SKIP |
| 4 | IntentAdapter | title, summary | intent | Rule-based |
| 5 | ContextAdapter | event, type, intent | llm_output | LLM with retry |
| 6 | ClarityAdapter | llm_output | clarity_issues[] | Safety validation |
| 7 | HITLDecisionAdapter | clarity_issues | hitl (HITLDecision) | Human review decision |
| 8 | LoggerAdapter | all context | log_record | JSONL file |
| 9 | DatabaseAdapter | all context | db_event_id, db_output_id | PostgreSQL + WebSocket |

---

## Twitter Plugin Pipeline

```
Approved Output → [Twitter Adapter Chain] → ContentQueue
```

| # | Adapter | Purpose |
|---|---------|---------|
| 1 | FormatDecisionAdapter | Decide SINGLE (280 char) or THREAD |
| 2 | TwitterSingleAdapter / TwitterThreadAdapter | Generate X content |
| 3 | TwitterClarityAdapter | X-specific safety validation |
| 4 | TwitterHITLAdapter | Human review decision (uses HITLService) |
| 5 | Save to ContentQueue | status + HITL metadata |

---

## Data Models

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Event     │────→│    Output    │────→│  Evaluation  │
│              │     │              │     │              │
│ event_id     │     │ event_id(FK) │     │ output_id(FK)│
│ title        │     │ llm_output   │     │ verdict      │
│ summary      │     │ event_type   │     │ evaluator    │
│ link         │     │ intent       │     │ created_at   │
│ source       │     │ clarity_issues│    └──────────────┘
│ embedding    │     │ hitl_required │
│ published_at │     │ embedding    │
└──────────────┘     └──────┬───────┘
                            │
                            ↓
                     ┌───────────────────────┐
                     │     ContentQueue      │
                     │                       │
                     │ output_id(FK)         │
                     │ format                │
                     │ content_text          │
                     │ scheduled_for         │
                     │ status                │
                     │ tweet_id              │
                     │ hitl_required         │
                     │ hitl_risk_level       │
                     │ suggested_verdict     │
                     │ suggested_verdict_reason│
                     └───────────────────────┘
```

---

## LLM Service

Multi-provider fallback chain with automatic failover:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Gemini    │ ──→ │    Groq     │ ──→ │   Ollama    │
│ (Primary)   │     │ (Fallback)  │     │  (Local)    │
│ 15 RPM      │     │ 4s delay    │     │ Unlimited   │
└─────────────┘     └─────────────┘     └─────────────┘
```

| Provider | Model | Rate Limit |
|----------|-------|------------|
| Gemini | gemini-2.5-flash-preview-09-2025 | 15 RPM, 100 RPD |
| Groq | llama-3.3-70b-versatile | 4s between calls |
| Ollama | gemma3:12b | Local, unlimited |

---

## API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/events` | GET | List RSS events |
| `/api/outputs` | GET | List LLM outputs with evaluations |
| `/api/evaluations/{id}` | POST | Submit PASS/FAIL verdict |
| `/api/stats` | GET | Dashboard statistics |
| `/api/content` | GET/POST | Approved content queue |
| `/api/selection/approve` | POST | Approve output for publishing |
| `/api/scheduling/schedule` | POST | Schedule content for publish time |
| `/api/twitter/generate` | POST | Generate X content from output |
| `/api/system/health` | GET | System health check |
| `/ws` | WebSocket | Real-time dashboard updates |
| `/internal/notify-output` | POST | Pipeline → WebSocket notification |

---

## WebSocket Events

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `NEW_OUTPUT` | Pipeline saves output | output_id, event_id, event_type |
| `NEW_EVENT` | Pipeline fetches event | event_id |
| `NEW_EVALUATION` | User submits verdict | output_id, verdict |
| `STATS_UPDATE` | Any data change | refresh signal |

---

## Event Classification

### Event Types (6)
| Type | Description |
|------|-------------|
| `FINANCE_POLICY` | Regulations, schemes, policies |
| `MARKET_INFRASTRUCTURE` | Bonds, auctions, exchanges |
| `MARKET_MOVEMENT` | Stock prices, market sentiment |
| `MACRO_ECONOMIC` | Inflation, GDP, interest rates |
| `GEO_FINANCIAL` | Tariffs, sanctions, trade wars |
| `NON_FINANCE` | Unrelated content |

### Content Intent (3)
| Intent | Output Style |
|--------|--------------|
| `EXPLANATORY` | Deep explanation of policies/mechanisms |
| `DESCRIPTIVE` | Brief factual summary |
| `MARKET_OPINION` | Summarize without advice |

---

## Deduplication Strategy

Two-layer check before processing:

```
Layer 1: URL Exact Match (fast)
    ↓ (if no match)
Layer 2: Semantic Similarity
    - Generate 384-dim embedding
    - Compare with historical embeddings
    - Threshold: cosine similarity ≥ 0.85
    - Uses pgvector for efficient search
```

---

## Directory Structure

```
FinAgent/
├── adapters/                 # Pipeline adapters
│   ├── embedding.py         # Vector embeddings
│   ├── dedup.py             # Semantic deduplication
│   ├── event_type.py        # Event classification
│   ├── intent.py            # Intent classification
│   ├── output.py            # LLM generation
│   ├── clarity.py           # Safety validation
│   ├── hitl.py              # HITL decision
│   ├── database.py          # PostgreSQL + WebSocket
│   └── plugins/twitter/     # X content adapters
│       ├── format_decision.py   # SINGLE vs THREAD
│       ├── twitter_single.py    # 280-char tweet
│       ├── twitter_thread.py    # 3-tweet thread
│       ├── twitter_clarity.py   # X-specific validation
│       └── twitter_hitl.py      # X HITL decision
│
├── api/                      # FastAPI backend
│   ├── main.py              # App entry + WebSocket
│   ├── routes/              # REST endpoints
│   ├── schemas/             # Pydantic models
│   └── validators/          # Request validation
│
├── dashboard/                # React frontend
│   └── src/
│       ├── pages/           # Dashboard, Outputs, Stats, etc.
│       ├── components/      # UI components
│       ├── contexts/        # React contexts
│       └── api/             # API client
│
├── database/
│   ├── models.py            # SQLAlchemy ORM
│   ├── repository.py        # Data access layer
│   ├── connection.py        # PostgreSQL connection
│   └── migrations/          # Schema migrations
│
├── services/
│   ├── llm_service.py       # Multi-provider LLM
│   ├── hitl_service.py      # Centralized HITL decision logic
│   ├── twitter_publishing_service.py  # X API publishing
│   ├── smart_scheduler.py   # Content scheduling logic
│   └── quota_manager.py     # API quota tracking
│
├── workers/
│   └── twitter_publishing_worker.py  # Background publisher
│
├── config/
│   ├── settings.py          # RSS sources, LLM config
│   └── prompts.py           # FROZEN LLM prompts
│
├── run_pipeline.py          # Main pipeline entry
├── run_twitter_plugin.py    # Twitter processing entry
└── run_migrations.py        # Database migrations
```

---

## Data Flow Sequence

```
1. RSS Ingestion
   └─ run_pipeline.py selects events by priority
   └─ feedparser fetches from 30+ RSS feeds

2. Pipeline Processing
   └─ 9 adapters process sequentially
   └─ Early exits: duplicate detection, SKIP classification

3. Database Persistence
   └─ Event + Output saved to PostgreSQL
   └─ Embeddings stored in pgvector

4. Real-time Notification
   └─ DatabaseAdapter → HTTP POST → FastAPI → WebSocket broadcast

5. Dashboard Display
   └─ React receives WebSocket message
   └─ UI updates without refresh

6. Human Evaluation
   └─ User reviews content, submits PASS/FAIL

7. Content Selection
   └─ Approved items added to publishing queue

8. Twitter Generation
   └─ Twitter plugin creates 280-char versions
   └─ TwitterHITLAdapter determines if human review needed
   └─ HITL metadata stored in ContentQueue

9. Scheduling
   └─ User sets publish time via calendar

10. Publishing (BLOCKER)
    └─ Background worker polls ContentQueue
    └─ Publishes when scheduled_for <= now
    └─ [X API integration pending]
```

---

## Access Points

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API Docs | http://localhost:8001/docs |
| Health Check | http://localhost:8001/api/health |
| WebSocket | ws://localhost:8001/ws |

---

*Last updated: January 2026*
