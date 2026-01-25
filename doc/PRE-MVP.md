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
11. [Operational Safety Rails](#11-operational-safety-rails)
12. [Exit Criteria](#12-exit-criteria)
13. [Appendices](#13-appendices)

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
| Operational Safety Rails | Kill switch + Generation metadata | PENDING |
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
| **Operational Safety Rails** | **Kill switch for emergency control + Generation metadata for audit trails** |

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
5. **Operational Safety** - Kill switch and generation metadata implemented and tested

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

# 11. Operational Safety Rails

## 11.1 Overview

Before transitioning to MVP (publishing phase), two critical operational safeguards must be implemented to ensure system reliability, auditability, and emergency control.

These are not features—they are **architectural hygiene** and **operational safety mechanisms**.

---

## 11.2 Kill Switch / Emergency Stop

### Purpose

Ability to **immediately disable content generation or publishing without code deployment**.

### Why Critical

Once MVP publishing begins:
- A bad prompt could generate unsafe content
- An LLM API failure could cause cascading errors
- A regulatory concern might require immediate halt
- System abuse or security breach needs instant response

**Without a kill switch, the only option is emergency code deployment—too slow and risky.**

### Implementation

**1. Configuration Variables**

```python
# config/settings.py

CONTENT_GENERATION_ENABLED: bool = os.getenv(
    "CONTENT_GENERATION_ENABLED",
    "true"
).lower() == "true"

PUBLISHING_ENABLED: bool = os.getenv(
    "PUBLISHING_ENABLED",
    "false"  # Default OFF until MVP
).lower() == "true"
```

**2. System Status API**

```python
# api/routes/system.py

@router.get("/api/system/status")
def get_system_status():
    """Public endpoint - shows system operational status"""
    return {
        "status": "operational",
        "content_generation_enabled": settings.CONTENT_GENERATION_ENABLED,
        "publishing_enabled": settings.PUBLISHING_ENABLED,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/api/system/content-generation/disable")
def disable_content_generation(admin_token: str):
    """Admin only - disable content generation"""
    if not verify_admin_token(admin_token):
        raise HTTPException(401, "Unauthorized")

    # Write to .env or config file
    update_env_variable("CONTENT_GENERATION_ENABLED", "false")

    return {"message": "Content generation disabled", "requires_restart": True}

@router.post("/api/system/publishing/disable")
def disable_publishing(admin_token: str):
    """Admin only - emergency stop publishing"""
    if not verify_admin_token(admin_token):
        raise HTTPException(401, "Unauthorized")

    update_env_variable("PUBLISHING_ENABLED", "false")

    return {"message": "Publishing disabled immediately"}
```

**3. Pipeline Enforcement**

```python
# In run_poc.py (pipeline script)

if not settings.CONTENT_GENERATION_ENABLED:
    logger.warning("Content generation is DISABLED via kill switch")
    sys.exit(0)

# In publishing worker (MVP)
while True:
    if not settings.PUBLISHING_ENABLED:
        logger.warning("Publishing is DISABLED via kill switch - worker paused")
        time.sleep(60)  # Check again in 60 seconds
        continue

    # Normal publishing logic...
```

**4. Dashboard Indicator**

```tsx
// dashboard/src/components/SystemStatus.tsx

function SystemStatus() {
  const { data: status } = useQuery('/api/system/status');

  return (
    <div className="system-status">
      {!status?.content_generation_enabled && (
        <Alert variant="warning">
          ⚠️ Content generation is currently DISABLED
        </Alert>
      )}
      {!status?.publishing_enabled && (
        <Alert variant="info">
          🛑 Publishing is currently DISABLED
        </Alert>
      )}
    </div>
  );
}
```

### Usage

**To disable content generation (Pre-MVP):**
```bash
# Set environment variable
export CONTENT_GENERATION_ENABLED=false

# Or via API (with admin token)
curl -X POST http://localhost:8000/api/system/content-generation/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Restart pipeline
# No new content will be generated
```

**To disable publishing (MVP):**
```bash
# Emergency stop - no restart needed
export PUBLISHING_ENABLED=false

# Publishing worker will stop immediately
# Already-scheduled posts will NOT publish
```

### Exit Criteria

- ✅ Kill switch implemented for content generation
- ✅ Kill switch implemented for publishing (MVP)
- ✅ Admin API endpoints secured
- ✅ Dashboard shows system status
- ✅ Tested in staging environment

---

## 11.3 Generation Metadata (Immutable Snapshots)

### Purpose

**Store exact configuration used for every LLM generation** to enable reproducibility, debugging, and audit trails.

### Why Important

**The Problem:**
- LLM output today: "RBI keeps rates steady..."
- 3 months later, complaint received
- Question: "Which prompt version generated this?"
- Answer: **Unknown** (no metadata stored)

**The Solution:**
Capture and store the **exact state** of generation at the moment it happened.

### What to Capture

```python
generation_metadata = {
    # Model Information
    "model": "llama3",              # or "gpt-4o-mini"
    "model_version": "8B",          # Model size/variant
    "provider": "ollama",            # ollama / openrouter

    # Prompt Configuration
    "prompt_version": "1.0",        # Frozen prompt version
    "system_prompt_hash": "a3f2...", # SHA-256 of actual prompt text

    # Generation Parameters
    "temperature": 0.7,
    "max_tokens": 512,
    "top_p": 0.9,

    # Pipeline State
    "adapter_versions": {
        "event_type": "1.0",
        "intent": "1.0",
        "output": "1.0",
        "clarity": "1.0"
    },

    # Timestamps
    "generated_at": "2026-01-22T10:30:45Z",
    "generation_duration_ms": 2340,

    # Event Context
    "event_type": "FINANCE_POLICY",
    "intent": "EXPLANATORY",
    "source": "RBI_PRESS"
}
```

### Implementation

**1. Database Schema Update**

```python
# database/models.py - Add to Output model

class Output(Base):
    __tablename__ = "outputs"

    # ... existing columns ...

    generation_metadata = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Immutable snapshot of generation configuration"
    )
```

**Migration:**
```sql
-- database/migrations/add_generation_metadata.sql

ALTER TABLE outputs
ADD COLUMN generation_metadata JSONB DEFAULT '{}';

COMMENT ON COLUMN outputs.generation_metadata IS
'Immutable snapshot of LLM configuration, prompt version, and generation parameters';
```

**2. Capture in OutputAdapter**

```python
# adapters/output.py

class OutputAdapter(BaseAdapter):

    def run(self, event: Event, context: ExecutionContext):
        # Generate content
        llm_output = self.llm_service.generate(...)

        # Capture metadata
        context.generation_metadata = {
            "model": self.llm_service.model_name,
            "model_version": self.llm_service.model_version,
            "provider": self.llm_service.provider,
            "prompt_version": settings.PROMPT_VERSION,
            "system_prompt_hash": hashlib.sha256(
                settings.SYSTEM_PROMPT.encode()
            ).hexdigest(),
            "temperature": self.llm_service.temperature,
            "max_tokens": self.llm_service.max_tokens,
            "adapter_versions": {
                "event_type": "1.0",
                "intent": "1.0",
                "output": "1.0",
                "clarity": "1.0"
            },
            "generated_at": datetime.utcnow().isoformat(),
            "generation_duration_ms": duration_ms,
            "event_type": context.event_type,
            "intent": context.intent,
            "source": event.source
        }

        context.llm_output = llm_output
```

**3. Store in Database**

```python
# adapters/database.py

def save_output(context: ExecutionContext):
    output = Output(
        event_id=context.event.id,
        llm_output=context.llm_output,
        event_type=context.event_type,
        intent=context.intent,
        clarity_issues=context.clarity_issues,
        hitl_required=context.hitl.required,
        hitl_risk_level=context.hitl.risk_level,
        generation_metadata=context.generation_metadata  # ← NEW
    )
    db.add(output)
    db.commit()
```

**4. API Response**

```python
# api/routes/outputs.py

@router.get("/api/outputs/{output_id}")
def get_output_detail(output_id: str):
    output = db.query(Output).filter_by(id=output_id).first()

    return {
        "id": output.id,
        "llm_output": output.llm_output,
        "event_type": output.event_type,
        # ... other fields ...

        "generation_metadata": output.generation_metadata,  # ← Expose

        # Or hide by default, show on demand
        "metadata_available": bool(output.generation_metadata)
    }
```

**5. Dashboard View (Optional)**

```tsx
// dashboard/src/pages/OutputDetail.tsx

function OutputMetadata({ metadata }) {
  return (
    <Accordion title="🔍 Generation Metadata">
      <dl>
        <dt>Model:</dt>
        <dd>{metadata.model} ({metadata.model_version})</dd>

        <dt>Prompt Version:</dt>
        <dd>{metadata.prompt_version}</dd>

        <dt>Generated At:</dt>
        <dd>{new Date(metadata.generated_at).toLocaleString()}</dd>

        <dt>Temperature:</dt>
        <dd>{metadata.temperature}</dd>

        <dt>Duration:</dt>
        <dd>{metadata.generation_duration_ms}ms</dd>
      </dl>

      <details>
        <summary>Full Metadata (JSON)</summary>
        <pre>{JSON.stringify(metadata, null, 2)}</pre>
      </details>
    </Accordion>
  );
}
```

### Use Cases

**1. Debugging**
```
User complaint: "This explanation is confusing"
→ Check generation_metadata
→ See: prompt_version = "0.9" (old version)
→ Conclusion: User saw content from old prompt, since updated
```

**2. Audit Trail**
```
Regulator asks: "How was this content generated?"
→ Provide: Model, prompt version, parameters, timestamp
→ Demonstrates: Transparent, documented process
```

**3. Performance Analysis**
```
Query: "Which model version produces best content?"
→ GROUP BY generation_metadata->>'model'
→ JOIN with evaluations (PASS/FAIL)
→ Result: "llama3 8B" has 97% pass rate vs "gpt-4o-mini" 92%
```

**4. Reproducibility**
```
Need to regenerate content with exact same settings:
→ Read generation_metadata from original
→ Use same model, prompt version, temperature
→ Should produce similar (though not identical) output
```

### Exit Criteria

- ✅ `generation_metadata` column added to `outputs` table
- ✅ All new outputs store metadata
- ✅ API exposes metadata on request
- ✅ Dashboard can view metadata (optional)
- ✅ Tested: Metadata populated correctly for all generation types

---

## 11.4 Implementation Timeline

| Task | Effort | Priority | Phase |
|------|--------|----------|-------|
| **Kill Switch - Config Variables** | 30 min | 🔴 Critical | Pre-MVP |
| **Kill Switch - API Endpoints** | 1 hour | 🔴 Critical | Pre-MVP |
| **Kill Switch - Dashboard Indicator** | 30 min | 🟡 Medium | Pre-MVP |
| **Generation Metadata - DB Schema** | 30 min | 🔴 Critical | Pre-MVP |
| **Generation Metadata - Capture Logic** | 1 hour | 🔴 Critical | Pre-MVP |
| **Generation Metadata - API Exposure** | 30 min | 🟡 Medium | Pre-MVP |
| **Generation Metadata - Dashboard View** | 1 hour | 🟢 Low | MVP |
| **Testing & Validation** | 1 hour | 🔴 Critical | Pre-MVP |
| **Total** | **~6 hours** | | |

**Recommendation:** Complete both features **before** starting MVP publishing work.

---

## 11.5 Success Criteria

Before moving to MVP, verify:

**Kill Switch:**
- ✅ Can disable content generation via environment variable
- ✅ Can disable publishing via environment variable
- ✅ API endpoints return correct status
- ✅ Dashboard shows kill switch status
- ✅ Pipeline respects kill switch (stops gracefully)
- ✅ Admin authentication works

**Generation Metadata:**
- ✅ All new outputs have `generation_metadata` populated
- ✅ Metadata includes all required fields (model, prompt version, timestamp, etc.)
- ✅ Metadata is immutable (stored at generation time, never modified)
- ✅ API returns metadata when requested
- ✅ Can query database by metadata fields

**Integration:**
- ✅ Both features tested in staging environment
- ✅ No performance degradation
- ✅ Documentation updated
- ✅ Team trained on emergency procedures

---

# 12. Exit Criteria

## 12.1 Pre-MVP Exit Conditions

| # | Condition | Threshold | Status |
|---|-----------|-----------|--------|
| 1 | Human-System Agreement | ≥90% over 30 events | PENDING |
| 2 | Rule Stability | No new rules for 7 days | PENDING |
| 3 | False Positives | <10% | PENDING |
| 4 | High-Risk Sources Validated | RBI, Bloomberg fully tested | PENDING |
| 5 | **Kill Switch Operational** | **Config + API + Testing complete** | **PENDING** |
| 6 | **Generation Metadata** | **All outputs store metadata** | **PENDING** |

## 12.2 Agreement Rate Calculation

```
Agreement Rate = (PASS Count) / (PASS Count + FAIL Count) × 100
```

**Target:** ≥90%

## 12.3 Post Pre-MVP State

After exit criteria are met:

1. **HITL becomes optional** - System can auto-approve low-risk content
2. **Human review only for:**
   - New sources
   - New event types
   - High-risk classifications
   - Explicit regression
3. **Move to MVP phase** - Begin building publishing features

---

# 13. Appendices

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
