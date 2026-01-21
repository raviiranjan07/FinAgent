# FinAgent: AI Finance Media & Intelligence System
## Master Pre-MVP Documentation v1.0

**Status:** FROZEN
**Version:** 1.0
**Last Updated:** January 2026
**Prerequisite:** POC Phase Completed (0% failure rate)

---

# Table of Contents

1. [Phase Overview](#1-phase-overview)
2. [POC Summary & Learnings](#2-poc-summary--learnings)
3. [Pre-MVP Objectives & Scope](#3-pre-mvp-objectives--scope)
4. [System Architecture](#4-system-architecture)
5. [Source Prioritization System](#5-source-prioritization-system)
6. [Database Schema](#6-database-schema)
7. [API Specification](#7-api-specification)
8. [WebSocket Events](#8-websocket-events)
9. [Dashboard Application](#9-dashboard-application)
10. [HITL Workflow](#10-hitl-workflow)
11. [Exit Criteria](#11-exit-criteria)
12. [Appendices](#12-appendices)

---

# 1. Phase Overview

## 1.1 Project Roadmap

| Phase | Status | Objective |
|-------|--------|-----------|
| POC | COMPLETED | Validate AI can explain finance events safely |
| **Pre-MVP** | **IN PROGRESS** | Achieve HITL exit criteria, build evaluation infrastructure |
| MVP | PLANNED | Multi-platform publishing, scheduling, public website |
| Scale | PLANNED | Subscriptions, B2B, API products |

## 1.2 Pre-MVP Purpose

The Pre-MVP phase bridges the gap between the successful POC and a production-ready MVP by:

1. **Validating HITL Exit** - Achieving 90% human-system agreement to enable automation
2. **Building Infrastructure** - Database, API, and dashboard for content evaluation
3. **Scaling Sources** - Expanding from 2 RSS sources to 31+ sources
4. **Establishing Workflow** - Creating repeatable content evaluation and approval processes

## 1.3 Key Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| Database Setup | PostgreSQL + pgvector | COMPLETED |
| API Development | FastAPI REST endpoints | COMPLETED |
| Dashboard | React evaluation UI | COMPLETED |
| Real-time Updates | WebSocket integration | COMPLETED |
| Source Expansion | 31 RSS sources configured | COMPLETED |
| Deduplication | Embedding-based similarity | COMPLETED |
| Source Prioritization | Category-based quotas | IN PROGRESS |
| HITL Exit | 90% agreement rate | PENDING |

---

# 2. POC Summary & Learnings

## 2.1 POC Results

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Failure Rate | ≤15% | **0%** | PASSED |
| Test Cases | 14-20 runs | Completed | PASSED |
| Critical Violations | 0 | 0 | PASSED |

## 2.2 What POC Validated

1. **LLM Capability** - Llama 3 (via Ollama) can generate safe, educational finance explanations
2. **Guardrails Work** - Forbidden language detection prevents advice/predictions
3. **Adapter Architecture** - Modular pipeline enables clean separation of concerns
4. **Classification Accuracy** - Event type and intent classification is reliable

## 2.3 POC Limitations Addressed in Pre-MVP

| POC Limitation | Pre-MVP Solution |
|----------------|------------------|
| Manual evaluation (terminal) | Dashboard with HITL UI |
| JSONL logging only | PostgreSQL database |
| 2 RSS sources | 31 RSS sources |
| No real-time feedback | WebSocket live updates |
| No duplicate detection | Embedding-based deduplication |

## 2.4 Carried Forward from POC

The following remain **unchanged** from POC:

- **System Prompt** - Frozen, no modifications
- **Forbidden Language** - Same phrases trigger instant FAIL
- **Event Types** - Same 6 categories
- **Content Intents** - Same 3 categories
- **Safety Principles** - "Silence is safer than speculation"

---

# 3. Pre-MVP Objectives & Scope

## 3.1 Primary Objective

**To achieve HITL exit criteria (90% human-system agreement) and build the infrastructure for scalable content evaluation.**

## 3.2 In-Scope

| Feature | Description |
|---------|-------------|
| PostgreSQL Database | Persistent storage with pgvector for embeddings |
| FastAPI Backend | REST API for all CRUD operations |
| React Dashboard | Content evaluation and statistics UI |
| WebSocket Updates | Real-time notifications |
| Source Expansion | 31 RSS sources across 8 categories |
| Deduplication | Embedding similarity to prevent duplicates |
| Source Prioritization | Category-based quotas and priority ordering |
| HITL Workflow | Human evaluation with PASS/FAIL verdicts |
| Statistics & Analytics | Pass rates, failure reasons, progress tracking |

## 3.3 Out-of-Scope

| Feature | Phase |
|---------|-------|
| Multi-platform publishing | MVP |
| Content scheduling | MVP |
| Public website | MVP |
| Auto-posting to social media | MVP |
| Subscriptions/monetization | Scale |
| B2B partnerships | Scale |
| API products | Scale |

## 3.4 Success Definition

Pre-MVP succeeds when:

1. **90% Agreement Rate** - Human evaluators agree with system clarity checks 90%+ of the time
2. **Rule Stability** - No new rule types discovered for 7 consecutive days
3. **False Positive Rate** - Less than 10% false HITL flags
4. **Infrastructure Complete** - All Pre-MVP features operational

---

# 4. System Architecture

## 4.1 Full Stack Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React Dashboard                              │
│                    (Vite + TypeScript + Tailwind)                   │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │Dashboard │  │ Outputs  │  │Evaluations│  │  Stats   │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (REST) + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                              │
│              (REST API + WebSocket Real-time Updates)               │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │ /events  │  │ /outputs │  │/evaluations│ │  /stats  │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ SQLAlchemy ORM
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │  Events  │  │ Outputs  │  │Evaluations│ │ContentQueue│          │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

## 4.2 Content Pipeline (Unchanged from POC)

```
RSS Event → ExecutionContext → EventTypeAdapter → IntentAdapter → OutputAdapter → ClarityAdapter → HITLDecisionAdapter → LoggerAdapter
```

## 4.3 Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | React | 18.x |
| | Vite | 5.x |
| | TypeScript | 5.x |
| | Tailwind CSS | 3.x |
| | TanStack Query | 5.x |
| **Backend** | FastAPI | 0.100+ |
| | Pydantic | 2.x |
| | SQLAlchemy | 2.x |
| | Uvicorn | 0.24+ |
| **Database** | PostgreSQL | 15+ |
| | pgvector | 0.5+ |
| **LLM** | Ollama | Latest |
| | Llama 3 | 8B |
| **Embeddings** | sentence-transformers | Latest |
| | all-MiniLM-L6-v2 | 384 dims |

## 4.4 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| React Dashboard | Human evaluation interface, statistics display |
| FastAPI Backend | REST API, WebSocket broadcasts, business logic |
| PostgreSQL | Persistent storage, vector similarity search |
| Ollama/Llama 3 | LLM content generation |
| sentence-transformers | Embedding generation for deduplication |

---

# 5. Source Prioritization System

## 5.1 Design Principles

- **Hierarchical Categories** - Sources organized into types → categories → sources
- **One Source = One Category** - Each source belongs to exactly one category
- **Config-Driven** - Priorities and quotas defined in config, not hardcoded
- **Scalable** - Easy to add new categories or sources without code changes

## 5.2 Category Hierarchy

```
OFFICIAL (type)
├── CENTRAL_BANKS (priority: 1, quota: 5, region: GLOBAL)
│   └── RBI_PRESS, FED_ALL, FED_MONETARY, ECB_PRESS, BOE_NEWS, BOJ_NEWS
│
└── REGULATORS (priority: 1, quota: 3, region: INDIA)
    └── SEBI, NSE_INDIA, BSE_INDIA, PFRDA, IRDAI

NEWS (type)
├── GLOBAL_NEWS (priority: 2, quota: 4, region: GLOBAL)
│   └── BLOOMBERG_MARKETS, REUTERS_BUSINESS, REUTERS_MARKETS, FINANCIAL_TIMES
│
├── INDIA_NEWS (priority: 2, quota: 3, region: INDIA)
│   └── ET_MARKETS, ET_ECONOMY, MONEYCONTROL, LIVEMINT, BUSINESS_STANDARD
│
└── US_NEWS (priority: 3, quota: 2, region: USA)
    └── CNBC_TOP, CNBC_WORLD, MARKETWATCH, YAHOO_FINANCE

GOVERNMENT (type)
└── TREASURY (priority: 2, quota: 2, region: USA)
    └── TREASURY_ANNOUNCEMENTS, TREASURY_AUCTIONS

SPECIALTY (type)
├── CRYPTO (priority: 4, quota: 2, region: GLOBAL)
│   └── COINDESK, COINTELEGRAPH, BITCOIN_MAGAZINE
│
└── COMMODITIES (priority: 4, quota: 2, region: GLOBAL)
    └── KITCO_GOLD, OIL_PRICE
```

## 5.3 Category Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Unique category identifier |
| `type` | string | Parent type (OFFICIAL, NEWS, GOVERNMENT, SPECIALTY) |
| `priority` | int | Processing order (1 = highest, 4 = lowest) |
| `quota` | int | Max events to select per run |
| `region` | string | Geographic focus (GLOBAL, INDIA, USA) |
| `enabled` | bool | Enable/disable category |

## 5.4 Priority Quotas Summary

| Priority | Type | Category | Quota | Sources |
|----------|------|----------|-------|---------|
| 1 | OFFICIAL | CENTRAL_BANKS | 5 | 6 |
| 1 | OFFICIAL | REGULATORS | 3 | 5 |
| 2 | NEWS | GLOBAL_NEWS | 4 | 4 |
| 2 | NEWS | INDIA_NEWS | 3 | 5 |
| 2 | GOVERNMENT | TREASURY | 2 | 2 |
| 3 | NEWS | US_NEWS | 2 | 4 |
| 4 | SPECIALTY | CRYPTO | 2 | 3 |
| 4 | SPECIALTY | COMMODITIES | 2 | 2 |
| **Total** | | | **23** | **31** |

## 5.5 Selection Algorithm

```
1. Fetch events from all enabled sources
2. Remove duplicates (via embedding similarity, threshold: 0.85)
3. Group events by category
4. For each category (sorted by priority ascending):
   a. Sort events by published_at descending (most recent first)
   b. Select up to `quota` events
5. Process selected events through content pipeline
```

## 5.6 Priority Rationale

| Priority | Rationale |
|----------|-----------|
| **1 - OFFICIAL** | Primary sources - Central banks and regulators produce authoritative content that directly impacts markets |
| **2 - NEWS/GOVT** | Secondary sources - Major news outlets and government announcements provide important context |
| **3 - US_NEWS** | Tertiary sources - US-focused news, lower priority for India-first focus |
| **4 - SPECIALTY** | Niche sources - Crypto and commodities are specialized verticals |

---

# 6. Database Schema

## 6.1 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Events    │       │   Outputs   │       │ Evaluations │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──────<│ event_id(FK)│──────<│ event_id(FK)│
│ event_id    │       │ id (PK)     │       │ output_id(FK)│
│ title       │       │ llm_output  │       │ id (PK)     │
│ summary     │       │ event_type  │       │ verdict     │
│ link        │       │ intent      │       │ failure_reason│
│ source      │       │ clarity_issues│     │ comment     │
│ published_at│       │ hitl_required│      │ evaluator   │
│ embedding   │       │ hitl_risk_level│    │ evaluated_at│
│ created_at  │       │ created_at  │       └─────────────┘
└─────────────┘       └─────────────┘
       │                     │
       │                     │
       ▼                     ▼
┌─────────────────────────────┐
│       ContentQueue          │
├─────────────────────────────┤
│ id (PK)                     │
│ event_id (FK)               │
│ output_id (FK)              │
│ status                      │
│ edited_content              │
│ scheduled_for               │
│ published_at                │
│ platform                    │
│ platform_post_id            │
└─────────────────────────────┘
```

## 6.2 Events Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Internal ID |
| `event_id` | VARCHAR(255) | UNIQUE, NOT NULL | External RSS item ID |
| `title` | TEXT | NOT NULL | Event title |
| `summary` | TEXT | NOT NULL | Event content/summary |
| `link` | TEXT | | Original source URL |
| `source` | VARCHAR(100) | NOT NULL | RSS source key |
| `published_at` | TIMESTAMP | | Original publication time |
| `fetched_at` | TIMESTAMP | DEFAULT NOW() | When fetched |
| `embedding` | VECTOR(384) | | all-MiniLM embedding |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation |

**Indexes:** `idx_events_source`, `idx_events_published_at`, `idx_events_created_at`

## 6.3 Outputs Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Output ID |
| `event_id` | UUID | FK → Events.id | Parent event |
| `llm_output` | TEXT | NOT NULL | Generated explanation |
| `event_type` | VARCHAR(50) | NOT NULL | Classification |
| `intent` | VARCHAR(50) | NOT NULL | Content intent |
| `clarity_issues` | JSONB | DEFAULT '[]' | Validation issues |
| `hitl_required` | BOOLEAN | DEFAULT false | Needs human review |
| `hitl_risk_level` | VARCHAR(20) | | LOW, MEDIUM, HIGH |
| `output_embedding` | VECTOR(384) | | Output embedding |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time |

**Indexes:** `idx_outputs_event_id`, `idx_outputs_event_type`

## 6.4 Evaluations Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Evaluation ID |
| `event_id` | UUID | FK → Events.id | Related event |
| `output_id` | UUID | FK → Outputs.id | Evaluated output |
| `verdict` | VARCHAR(10) | CHECK IN ('PASS','FAIL') | Human verdict |
| `failure_reason` | TEXT | | Why content failed |
| `comment` | TEXT | | Optional comment |
| `evaluator` | VARCHAR(100) | DEFAULT 'default' | Evaluator ID |
| `evaluated_at` | TIMESTAMP | DEFAULT NOW() | Evaluation time |

**Indexes:** `idx_evaluations_verdict`

## 6.5 ContentQueue Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Queue item ID |
| `event_id` | UUID | FK → Events.id | Related event |
| `output_id` | UUID | FK → Outputs.id | Related output |
| `status` | VARCHAR(20) | CHECK IN (...) | Workflow status |
| `edited_content` | TEXT | | Human-edited version |
| `scheduled_for` | TIMESTAMP | | Scheduled publish time |
| `published_at` | TIMESTAMP | | Actual publish time |
| `platform` | VARCHAR(50) | | Target platform |
| `platform_post_id` | VARCHAR(255) | | External post ID |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMP | | Last update time |

**Status Values:** `pending`, `approved`, `rejected`, `scheduled`, `published`

---

# 7. API Specification

## 7.1 Base Configuration

| Setting | Value |
|---------|-------|
| Base URL | `/api` |
| Content-Type | `application/json` |
| CORS Origins | `localhost:5173`, `localhost:3000` |

## 7.2 Health Endpoints

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/` | `{"status": "ok", "message": "FinAgent API is running"}` |
| GET | `/api/health` | `{"status": "healthy", "database": "connected"}` |

## 7.3 Events API

### List Events
```
GET /api/events?page=1&page_size=20&source=RBI_PRESS
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "event_id": "string",
      "title": "string",
      "summary": "string",
      "link": "url",
      "source": "string",
      "published_at": "datetime",
      "created_at": "datetime",
      "has_output": true,
      "has_evaluation": false
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

### Get Event
```
GET /api/events/{event_id}
```

### List Sources
```
GET /api/events/sources/list
```

**Response:**
```json
{
  "sources": {
    "RBI_PRESS": 15,
    "BLOOMBERG_MARKETS": 42
  }
}
```

## 7.4 Outputs API

### List Outputs
```
GET /api/outputs?page=1&page_size=20&event_type=FINANCE_POLICY&pending_only=true&hitl_only=false
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "llm_output": "string",
      "event_type": "FINANCE_POLICY",
      "intent": "EXPLANATORY",
      "clarity_issues": ["string"],
      "hitl_required": true,
      "hitl_risk_level": "MEDIUM",
      "created_at": "datetime",
      "event_title": "string",
      "event_source": "string",
      "has_evaluation": false,
      "evaluation_verdict": null
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

### Get Output Detail
```
GET /api/outputs/{output_id}
```

### List Event Types
```
GET /api/outputs/event-types/list
```

## 7.5 Evaluations API

### Create Evaluation
```
POST /api/evaluations
Content-Type: application/json

{
  "output_id": "uuid",
  "verdict": "PASS|FAIL",
  "failure_reason": "string (required if FAIL)",
  "comment": "string (optional)",
  "evaluator": "string (optional)"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "output_id": "uuid",
  "verdict": "PASS",
  "failure_reason": null,
  "comment": "string",
  "evaluator": "default",
  "evaluated_at": "datetime"
}
```

### List Evaluations
```
GET /api/evaluations?page=1&page_size=20&verdict=FAIL
```

### Update Evaluation
```
PUT /api/evaluations/{evaluation_id}
```

### Delete Evaluation
```
DELETE /api/evaluations/{evaluation_id}
```

## 7.6 Statistics API

### Dashboard Stats
```
GET /api/stats/dashboard
```

**Response:**
```json
{
  "evaluation": {
    "total": 100,
    "pass_count": 85,
    "fail_count": 15,
    "pass_rate": 85.0,
    "fail_rate": 15.0,
    "pending_count": 20
  },
  "event_types": [
    {"event_type": "FINANCE_POLICY", "count": 30, "percentage": 30.0}
  ],
  "sources": [
    {"source": "RBI_PRESS", "count": 25, "percentage": 25.0}
  ],
  "failure_reasons": [
    {"reason": "JARGON_NOT_EXPLAINED", "count": 5, "percentage": 33.3}
  ],
  "recent_activity": {
    "daily_outputs": {"2026-01-21": 10},
    "total_last_7_days": 70
  }
}
```

### HITL Progress
```
GET /api/stats/hitl-progress
```

**Response:**
```json
{
  "total_evaluated": 100,
  "pass_count": 85,
  "fail_count": 15,
  "pass_rate": 85.0,
  "target_rate": 90.0,
  "progress": 94.4,
  "status": "needs_improvement",
  "remaining_to_target": 5.0
}
```

---

# 8. WebSocket Events

## 8.1 Connection

| Setting | Value |
|---------|-------|
| Endpoint | `ws://localhost:8000/ws` |
| Heartbeat | 30 seconds (ping/pong) |
| Auto-reconnect | 3 second delay |

## 8.2 Event Types

| Event | Payload | Trigger |
|-------|---------|---------|
| `NEW_EVENT` | `{event_id, title, source}` | New RSS event ingested |
| `NEW_OUTPUT` | `{output_id, event_id, event_type}` | New LLM output generated |
| `NEW_EVALUATION` | `{evaluation_id, output_id, verdict}` | Human evaluation submitted |
| `STATS_UPDATE` | `{}` | Generic stats refresh |

## 8.3 Message Format

```json
{
  "type": "NEW_EVALUATION",
  "data": {
    "evaluation_id": "uuid",
    "output_id": "uuid",
    "verdict": "PASS"
  }
}
```

---

# 9. Dashboard Application

## 9.1 Pages Overview

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | Overview, stats, progress |
| Outputs | `/outputs` | Content evaluation workflow |
| Evaluations | `/evaluations` | Evaluation history |
| Stats | `/stats` | Detailed analytics |

## 9.2 Dashboard Page

**Features:**
- Live connection status indicator (WebSocket)
- 4 stat cards: Total Outputs, Pass Rate, Passed, Failed
- HITL Exit Progress bar (target: 90%)
- Event Types distribution
- Failure Reasons breakdown
- RSS Sources grid

## 9.3 Outputs Page (HITL Workflow)

**Features:**
- Filter: Pending Only / All Outputs
- Output cards with:
  - Event title, source, type
  - HITL warning badge
  - Status badge (Pending/PASS/FAIL)
  - LLM output preview
  - Clarity issues tags
- Click-to-evaluate modal:
  - Full output display
  - Event metadata
  - Failure reason dropdown
  - Comment field
  - Pass/Fail buttons

**Failure Reason Options:**
1. ADVICE_DETECTED
2. PREDICTION_MADE
3. JARGON_NOT_EXPLAINED
4. FACTUAL_ERROR
5. INCOMPLETE_EXPLANATION
6. SENSATIONALISM
7. OTHER

## 9.4 Evaluations Page

**Features:**
- Filter: All / Passed / Failed
- Evaluation cards with:
  - Verdict badge
  - Failure reason (if applicable)
  - Evaluator comment
  - Timestamp
- Pagination (20 per page)

## 9.5 Stats Page

**Features:**
- HITL Exit Criteria progress card
  - Large progress bar
  - Pass/Fail counts
  - Status badge (On Track / Needs Improvement)
- Event Type distribution (bar chart)
- Failure Analysis (bar chart)
- Source Distribution (grid)
- 7-day activity count

---

# 10. HITL Workflow

## 10.1 Workflow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RSS Event  │────▶│  Pipeline   │────▶│   Output    │
│   Fetched   │     │  Processing │     │  Generated  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                    ┌─────────────────────────────────────────┐
                    │           HITL Decision                  │
                    │  ┌─────────────┐  ┌─────────────┐       │
                    │  │hitl_required│  │hitl_required│       │
                    │  │   = true    │  │   = false   │       │
                    │  └──────┬──────┘  └──────┬──────┘       │
                    └─────────┼────────────────┼──────────────┘
                              │                │
                              ▼                ▼
                    ┌─────────────┐    ┌─────────────┐
                    │   Human     │    │    Auto     │
                    │   Review    │    │   Approved  │
                    │  Required   │    │  (Future)   │
                    └──────┬──────┘    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
    ┌─────────────┐           ┌─────────────┐
    │    PASS     │           │    FAIL     │
    │  verdict    │           │  verdict    │
    └──────┬──────┘           └──────┬──────┘
           │                         │
           ▼                         ▼
    ┌─────────────┐           ┌─────────────┐
    │  Content    │           │  Logged for │
    │   Queue     │           │  Analysis   │
    └─────────────┘           └─────────────┘
```

## 10.2 HITL Trigger Conditions

| Condition | hitl_required |
|-----------|---------------|
| Clarity issues detected | `true` |
| High-risk event type | `true` |
| New/unknown source | `true` |
| Ambiguous classification | `true` |
| No issues, known pattern | `false` |

## 10.3 Evaluation Process

1. **Evaluator** opens Outputs page (filtered to Pending)
2. **Clicks** on output card to open evaluation modal
3. **Reviews** LLM output, event metadata, clarity issues
4. **Decides** PASS or FAIL
5. **If FAIL** - selects failure reason from dropdown
6. **Optionally** adds comment
7. **Submits** evaluation
8. **Dashboard** auto-refreshes via WebSocket

## 10.4 Evaluation Guidelines

### PASS Criteria
- Facts align with source RSS items
- No hallucinated or altered information
- Acknowledges unknowns appropriately
- No investment advice or calls to action
- Calm, neutral, professional tone
- Consistent reasoning and structure

### FAIL Criteria
- Advice detected (buy/sell/hold language)
- Predictions made with certainty
- Jargon not explained for non-experts
- Factual errors present
- Incomplete or confusing explanation
- Sensational or emotional tone

---

# 11. Exit Criteria

## 11.1 Pre-MVP Exit Conditions

| # | Condition | Threshold | Status |
|---|-----------|-----------|--------|
| 1 | Human-System Agreement | ≥90% over 30 events | PENDING |
| 2 | Rule Stability | No new rules for 7 days | PENDING |
| 3 | False Positives | <10% | PENDING |
| 4 | High-Risk Sources Validated | RBI, Bloomberg fully tested | PENDING |

## 11.2 Agreement Rate Calculation

```
Agreement Rate = (PASS Count) / (PASS Count + FAIL Count) × 100
```

**Target:** ≥90%

## 11.3 Post Pre-MVP State

After exit criteria are met:

1. **HITL becomes optional** - System can auto-approve low-risk content
2. **Human review only for:**
   - New sources
   - New event types
   - High-risk classifications
   - Explicit regression
3. **Move to MVP phase** - Begin building publishing features

---

# 12. Appendices

## Appendix A: Event Types Reference

| Type | Description | Examples |
|------|-------------|----------|
| `FINANCE_POLICY` | Regulations, rules, schemes | RBI rate decision, SEBI circular |
| `MARKET_INFRASTRUCTURE` | Exchanges, bonds, auctions | Treasury auction, NSE announcement |
| `MARKET_MOVEMENT` | Stock prices, market sentiment | Index movement, market selloff |
| `MACRO_ECONOMIC` | Inflation, GDP, interest rates | CPI release, GDP growth |
| `GEO_FINANCIAL` | Tariffs, sanctions, trade | Tariff announcement, sanctions |
| `NON_FINANCE` | Unrelated content | Sports, entertainment |

## Appendix B: Content Intents Reference

| Intent | Description | Output Guidance |
|--------|-------------|-----------------|
| `EXPLANATORY` | Policies, rules, mechanisms | Explain in depth, who/what/when |
| `DESCRIPTIVE` | Factual reporting | Brief summary, max 180 words |
| `MARKET_OPINION` | Trades, sentiment | Summarize without advice |

## Appendix C: Forbidden Language (Instant FAIL)

| Category | Forbidden Phrases |
|----------|-------------------|
| Direct Advice | buy, sell, hold, invest, exit, enter |
| Urgency | best time, invest now, must act, act now |
| Guarantees | guaranteed returns, risk-free, certain profit |
| Directives | you should, you must, recommended to |

## Appendix D: RSS Sources List

### OFFICIAL - Central Banks (6 sources)
| Key | URL |
|-----|-----|
| RBI_PRESS | https://rbi.org.in/pressreleases_rss.xml |
| FED_ALL | https://www.federalreserve.gov/feeds/press_all.xml |
| FED_MONETARY | https://www.federalreserve.gov/feeds/press_monetary.xml |
| ECB_PRESS | https://www.ecb.europa.eu/rss/press.html |
| BOE_NEWS | https://www.bankofengland.co.uk/rss/news |
| BOJ_NEWS | https://www.boj.or.jp/en/rss/whatsnew.xml |

### OFFICIAL - Regulators (5 sources)
| Key | URL |
|-----|-----|
| SEBI | https://www.sebi.gov.in/sebirss.xml |
| NSE_INDIA | https://www.nseindia.com/rss/all-corporate-announcements.xml |
| BSE_INDIA | https://www.bseindia.com/xml-data/corpfiling/rss/all.xml |
| PFRDA | https://www.pfrda.org.in/rss.aspx |
| IRDAI | https://irdai.gov.in/rss-feeds |

### NEWS - Global (4 sources)
| Key | URL |
|-----|-----|
| BLOOMBERG_MARKETS | https://feeds.bloomberg.com/markets/news.rss |
| REUTERS_BUSINESS | https://feeds.reuters.com/reuters/businessNews |
| REUTERS_MARKETS | https://feeds.reuters.com/reuters/marketsNews |
| FINANCIAL_TIMES | https://www.ft.com/rss/home |

### NEWS - India (5 sources)
| Key | URL |
|-----|-----|
| ET_MARKETS | https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms |
| ET_ECONOMY | https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms |
| MONEYCONTROL | https://www.moneycontrol.com/rss/latestnews.xml |
| LIVEMINT | https://www.livemint.com/rss/markets |
| BUSINESS_STANDARD | https://www.business-standard.com/rss/markets-106.rss |

### NEWS - US (4 sources)
| Key | URL |
|-----|-----|
| CNBC_TOP | https://www.cnbc.com/id/100003114/device/rss/rss.html |
| CNBC_WORLD | https://www.cnbc.com/id/100727362/device/rss/rss.html |
| MARKETWATCH | https://feeds.marketwatch.com/marketwatch/topstories |
| YAHOO_FINANCE | https://finance.yahoo.com/news/rssindex |

### GOVERNMENT - Treasury (2 sources)
| Key | URL |
|-----|-----|
| TREASURY_ANNOUNCEMENTS | https://treasurydirect.gov/TA_WS/securities/announced/rss |
| TREASURY_AUCTIONS | https://treasurydirect.gov/TA_WS/securities/auctioned/rss |

### SPECIALTY - Crypto (3 sources)
| Key | URL |
|-----|-----|
| COINDESK | https://www.coindesk.com/arc/outboundfeeds/rss/ |
| COINTELEGRAPH | https://cointelegraph.com/rss |
| BITCOIN_MAGAZINE | https://bitcoinmagazine.com/feed |

### SPECIALTY - Commodities (2 sources)
| Key | URL |
|-----|-----|
| KITCO_GOLD | https://www.kitco.com/rss/gold.rss |
| OIL_PRICE | https://oilprice.com/rss/main |

## Appendix E: Configuration Reference

### Deduplication Settings
| Setting | Value | Description |
|---------|-------|-------------|
| SIMILARITY_MODEL | all-MiniLM-L6-v2 | 80MB, fast, good quality |
| SIMILARITY_THRESHOLD | 0.85 | Cosine similarity for duplicates |
| DEDUP_LOOKBACK_HOURS | 72 | Compare with last 72 hours |

### LLM Settings
| Setting | Value | Description |
|---------|-------|-------------|
| OLLAMA_URL | http://localhost:11434/api/generate | Local Ollama endpoint |
| MODEL_NAME | llama3 | LLM model |
| LLM_TIMEOUT | 300 | 5 minute timeout |
| LLM_MAX_RETRIES | 3 | Retry attempts |
| LLM_RETRY_DELAY | 2 | Base delay (exponential) |

## Appendix F: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial Pre-MVP documentation |

---

# Document Control

| Field | Value |
|-------|-------|
| **Document Status** | FROZEN |
| **Applies To** | Pre-MVP Phase Only |
| **Prerequisite** | POC Phase Completed |
| **Change Authority** | Requires version bump + re-evaluation |
| **Related Documents** | MASTER_POC_DOCUMENTATION_v1.0.md, CLAUDE.md |

---

*This document consolidates all Pre-MVP documentation into a single authoritative reference.*
