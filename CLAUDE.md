# FinAgent - AI Finance Media & Intelligence System

> This file helps Claude (and other AI assistants) understand the project context.

---

## Vision

**To build a trustworthy, scalable, AI-driven finance media system that explains finance, markets, and policies clearly and calmly, while converting audience attention into sustainable revenue through ethical automation.**

---

## What Is This Project?

FinAgent is an automated finance content intelligence system that:

1. **Ingests** financial news from official RSS feeds (RBI, Bloomberg, etc.)
2. **Classifies** events by type (policy, market movement, macro, etc.) and intent
3. **Generates** clear, non-expert-friendly explanations using local LLM (Ollama)
4. **Validates** content for safety (no advice, no predictions, no hype)
5. **Flags** risky content for human review (HITL)
6. **Logs** everything for evaluation and continuous improvement

### The Problem We Solve

Finance news is often:
- Full of jargon non-experts don't understand
- Mixed with opinions, predictions, and clickbait
- Potentially harmful if misinterpreted as advice

### Our Solution

Create **calm, factual, educational explanations** that anyone can understand, with **strict guardrails** that prevent the AI from giving advice or making predictions.

---

## Content Philosophy

| Principle | Description |
|-----------|-------------|
| **Educational** | Teaches concepts, not just reports facts |
| **Lightly Opinionated** | Thoughtful perspective without strong bias |
| **Data-Backed** | Claims supported by data |
| **Curiosity-Driven** | Encourages learning and exploration |
| **Calm** | No hype, fear, or urgency |
| **Human-Like** | Natural, conversational tone |

### Strictly Prohibited

- ❌ Investment advice ("buy", "sell", "hold")
- ❌ Predictions or forecasts
- ❌ Guarantees or certainty
- ❌ Political opinions
- ❌ Sensationalism or clickbait

### Safety Principle

> **"Silence is safer than speculation."**

If the system is unsure whether something could be interpreted as advice, it must not say it.

---

## Current Phase: Pre-MVP

### Phase History

| Phase | Status | Result |
|-------|--------|--------|
| POC | ✅ COMPLETED | 0% failure rate - PASSED |
| Pre-MVP | 🔄 IN PROGRESS | - |

### Pre-MVP Objective

**To achieve HITL exit criteria (90% human-system agreement) and build the infrastructure for content approval workflow.**

### Pre-MVP Scope

**Completed:**
- ✅ PostgreSQL database with pgvector
- ✅ FastAPI backend with REST API
- ✅ React dashboard (Vite + TypeScript + Tailwind)
- ✅ WebSocket real-time updates
- ✅ Expanded RSS sources (32 sources)
- ✅ Content evaluation UI
- ✅ Deduplication system

**In Progress:**
- ⏳ Achieve 90% HITL agreement rate
- ⏳ Content approval workflow

**Out of Scope (for MVP):**
- Trading advice or recommendations
- Predictions or forecasts
- Personalization
- Monetization
- Auto-posting to social media

### Pre-MVP Exit Criteria

| Condition | Threshold | Status |
|-----------|-----------|--------|
| Human-System Agreement | ≥90% over 30 events | Pending |
| Rule Stability | No new rules for 7 days | Pending |
| False Positives | <10% | Pending |

---

## Architecture

### Full Stack (Pre-MVP)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React Dashboard                              │
│                    (Vite + TypeScript + Tailwind)                   │
└─────────────────────────────────────────────────────────────────────┘
                              │ WebSocket + REST
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                              │
│              (REST API + WebSocket Real-time Updates)               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                            │
│              (Events, Outputs, Evaluations, Embeddings)             │
└─────────────────────────────────────────────────────────────────────┘
```

### Content Pipeline

```
RSS Event → ExecutionContext → EventTypeAdapter → IntentAdapter → OutputAdapter → ClarityAdapter → HITLDecisionAdapter → LoggerAdapter
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `models/event.py` | Event data schema |
| `adapters/event_type.py` | Classify into 6 event types |
| `adapters/intent.py` | Classify intent (EXPLANATORY/DESCRIPTIVE/MARKET_OPINION) |
| `adapters/output.py` | Generate LLM explanation |
| `adapters/clarity.py` | Validate safety & clarity rules |
| `adapters/hitl.py` | Decide if human review needed |
| `adapters/logger.py` | Log to JSONL + Database |
| `config/prompts.py` | **FROZEN** system prompt (DO NOT MODIFY) |

### Event Types (6 categories)

1. `FINANCE_POLICY` - RBI, SEBI regulations, schemes
2. `MARKET_INFRASTRUCTURE` - Bonds, auctions, exchanges
3. `MARKET_MOVEMENT` - Stock prices, market sentiment
4. `MACRO_ECONOMIC` - Inflation, GDP, interest rates
5. `GEO_FINANCIAL` - Tariffs, sanctions, trade wars
6. `NON_FINANCE` - Unrelated content

### Content Intent Types (3 categories)

1. `EXPLANATORY` - Policies, rules, mechanisms → Explain in depth
2. `DESCRIPTIVE` - Factual reporting → Brief summary
3. `MARKET_OPINION` - Trades, sentiment → Summarize without advice

---

## Forbidden Language

These phrases trigger **instant FAIL** if detected in output:

```
buy, sell, hold, invest now, best time, guaranteed returns,
you should, must act, risk-free, certain profit, recommended to, act now
```

---

## Project Roadmap

### Phase 1: POC ✅ COMPLETED
- ✅ RSS ingestion
- ✅ LLM generation
- ✅ Classification (event type + intent)
- ✅ Clarity validation
- ✅ Adapter-based architecture
- ✅ HITL decision logic
- ✅ Run 14-20 test cases
- ✅ Achieved 0% failure rate (PASSED)

### Phase 2: Pre-MVP (Current)
- ✅ PostgreSQL + pgvector database
- ✅ FastAPI REST API
- ✅ React evaluation dashboard
- ✅ WebSocket real-time updates
- ✅ Add more RSS sources (32 total)
- ✅ Deduplication system
- ⏳ Achieve HITL exit criteria (90% agreement)
- ⏳ Content approval workflow

### Phase 3: MVP
- Multi-platform publishing (Twitter, LinkedIn, Newsletter)
- Scheduling system
- Public website
- Analytics integration
- Feedback loop

### Phase 4: Scale & Monetize
- Subscriptions
- B2B partnerships
- API/Data products
- Cloud deployment

---

## Key Files

### Core Pipeline
| File | Purpose |
|------|---------|
| `run_poc.py` | Main pipeline entry point |
| `config/prompts.py` | **FROZEN** system prompt |
| `config/settings.py` | RSS sources (32), LLM config |
| `adapters/*.py` | Pipeline adapters |
| `models/event.py` | Event schema |

### Pre-MVP Infrastructure
| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI application |
| `api/routes/*.py` | REST API endpoints |
| `api/websocket.py` | Real-time WebSocket manager |
| `database/models.py` | SQLAlchemy ORM models |
| `database/session.py` | Database connection |
| `dashboard/` | React frontend (Vite + TypeScript) |

### Documentation
| File | Purpose |
|------|---------|
| `doc/MASTER_POC_DOCUMENTATION_v1.0.md` | Full POC documentation (FROZEN) |
| `CLAUDE.md` | AI assistant context file |

---

## Running the System

### Prerequisites
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Ensure Ollama is running with llama3 model
ollama run llama3

# Ensure PostgreSQL is running with database 'finagent'
```

### Run Pipeline (fetch & process events)
```bash
python run_poc.py
```

### Run API Server
```bash
cd api
uvicorn main:app --reload --port 8000
```

### Run Dashboard
```bash
cd dashboard
npm install  # first time only
npm run dev
```

### Access Points
- **Dashboard:** http://localhost:5173
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws

---

## Important Reminders for AI Assistants

1. **NEVER modify `config/prompts.py`** without explicit approval - it's frozen for POC
2. **NEVER add advice-like language** to any output
3. **Always check forbidden phrases** when generating content
4. **Maintain adapter contract** - adapters don't control flow, only process data
5. **Log everything** - traceability is critical for evaluation
6. **Safety over features** - if unsure, err on the side of caution
7. **Bug/Error Analysis Protocol** - For any bugs or errors:
   - First perform **root cause analysis** and explain the issue
   - Present findings to the user
   - **Wait for user approval** before implementing any fix
   - Do NOT auto-fix bugs without explicit permission
8. **Plan Before Implementation** - For any new feature or change:
   - First create a **written plan** explaining the approach
   - Present the plan to the user
   - **Wait for user approval** before writing any code
   - Do NOT implement without explicit permission

---

## Documentation

Full POC documentation is in: `doc/MASTER_POC_DOCUMENTATION_v1.0.md`

This includes:
- Complete system prompt (Section 6)
- Test cases TC-01 to TC-07 (Section 9)
- Evaluation sheet (Section 10)
- HITL exit criteria (Section 11)

---

## RSS Sources (30 active)

| Category | Sources |
|----------|---------|
| **India - Regulators** | RBI, SEBI, NSE, BSE, PFRDA, IRDAI |
| **India - News** | ET Markets, ET Economy, Moneycontrol, Livemint, Business Standard |
| **Global - News** | Bloomberg, Reuters (Business & Markets), CNBC, MarketWatch, Yahoo Finance, Financial Times |
| **USA - Central Bank** | Federal Reserve (All & Monetary), Treasury (Announcements & Auctions) |
| **Europe & Others** | ECB, Bank of England, Bank of Japan |
| **Crypto** | CoinDesk, Cointelegraph, Bitcoin Magazine |
| **Commodities** | OilPrice *(KITCO_MINING disabled - XML parsing errors)* |

---

## Source Prioritization System

### Design Principles

- **Hierarchical Categories**: Sources are organized into types → categories → sources
- **One Source = One Category**: Each source belongs to exactly one category (no duplicates)
- **Config-Driven**: Priorities and quotas defined in config, not hardcoded
- **Scalable**: Easy to add new categories or sources without code changes

### Category Hierarchy

```
OFFICIAL (type)
├── CENTRAL_BANKS (priority: 1, quota: 5, region: GLOBAL)
│   └── RBI, FED_ALL, FED_MONETARY, ECB, BOE, BOJ
│
└── REGULATORS (priority: 1, quota: 3, region: INDIA)
    └── SEBI, NSE, BSE, PFRDA, IRDAI

NEWS (type)
├── GLOBAL_NEWS (priority: 2, quota: 4, region: GLOBAL)
│   └── BLOOMBERG, REUTERS_BUSINESS, REUTERS_MARKETS, FINANCIAL_TIMES
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
    └── OIL_PRICE (KITCO_MINING disabled due to XML parsing errors)
```

### Category Properties

| Property | Description |
|----------|-------------|
| `name` | Unique category identifier |
| `type` | Parent type (OFFICIAL, NEWS, GOVERNMENT, SPECIALTY) |
| `priority` | Processing order (1 = highest, 4 = lowest) |
| `quota` | Max events to select per run |
| `region` | Geographic focus (GLOBAL, INDIA, USA) |
| `enabled` | Boolean to enable/disable category |

### Priority Quotas Summary

| Priority | Type | Category | Quota | Sources |
|----------|------|----------|-------|---------|
| 1 | OFFICIAL | CENTRAL_BANKS | 5 | 6 sources |
| 1 | OFFICIAL | REGULATORS | 3 | 5 sources |
| 2 | NEWS | GLOBAL_NEWS | 4 | 4 sources |
| 2 | NEWS | INDIA_NEWS | 3 | 5 sources |
| 2 | GOVERNMENT | TREASURY | 2 | 2 sources |
| 3 | NEWS | US_NEWS | 2 | 4 sources |
| 4 | SPECIALTY | CRYPTO | 2 | 3 sources |
| 4 | SPECIALTY | COMMODITIES | 2 | 1 source |
| **Total** | | | **23** | **30 sources** |

### Selection Algorithm

The pipeline operates in **3 distinct stages**:

#### Stage 1: Fetch (Per Source)
```python
# For each enabled source, fetch up to MAX_EVENTS (default: 4)
fetch_events(source) → Returns up to 4 most recent events
```

#### Stage 2: Selection (Apply Quotas)
```python
# Group by category, select up to quota
For each category (sorted by priority):
  - Collect events from all sources in category
  - Sort by published_at (most recent first)
  - Select up to `quota` events
  - Add to processing queue
```

**Example:** TREASURY category (quota: 2)
- TREASURY_ANNOUNCEMENTS: Fetched 4 events
- TREASURY_AUCTIONS: Fetched 4 events
- Select 2 most recent across both sources → Added to queue

#### Stage 3: Processing (Pipeline with Deduplication)
```python
# Process each selected event through adapter pipeline
For each event in queue (20 total):
  1. EmbeddingAdapter → Generate embeddings
  2. DeduplicationAdapter → Check for duplicates
     - If duplicate: Skip (no backfill)
     - If unique: Continue pipeline
  3. EventTypeAdapter → Classify event
  4. ... (remaining adapters)
```

### Important: No Backfill on Duplicate Detection

**When deduplication skips an event, the pipeline does NOT:**
- ❌ Fetch more events from RSS to replace it
- ❌ Try to maintain the category quota
- ❌ Go back to earlier stages

**Instead, it:**
- ✅ Marks event as duplicate
- ✅ Continues with next event in queue
- ✅ Logs the skip

**Example from logs:**
```
[13/20] TREASURY_ANNOUNCEMENTS: Treasury announces 6-Week Bill...
    [DEDUP] URL match - skipping
[14/20] TREASURY_AUCTIONS: 6-Week Bill Treasury Auction Results...
    [DEDUP] URL match - skipping
```

Both events were **already selected** in Stage 2. When they hit deduplication in Stage 3, they're skipped, but:
- No new events are fetched
- TREASURY ends up with 0 new events (both deduplicated)
- Processing continues with remaining 6 events

### Why No Backfill?

1. **Semantic Deduplication** - If an event is duplicate, fetching more won't help (likely more duplicates)
2. **Quota Protection** - Prevents fetching 100+ events to find unique ones
3. **RSS Feed Behavior** - Same story often appears multiple times in feeds
4. **Performance** - Backfilling would slow down pipeline significantly

### Tuning for Better Results

If you're getting too many duplicates:

1. **Increase MAX_EVENTS** (config/settings.py)
   ```python
   MAX_EVENTS = 10  # Default: 4, fetch more per source
   ```

2. **Adjust Deduplication Threshold** (adapters/dedup.py)
   ```python
   SIMILARITY_THRESHOLD = 0.90  # Default: 0.85, higher = stricter
   ```

3. **Lower Category Quotas** - If sources have duplicates, expect less unique content

### Priority Rationale

| Priority | Rationale |
|----------|-----------|
| **1 - OFFICIAL** | Primary sources - Central banks and regulators produce authoritative content that directly impacts markets |
| **2 - NEWS/GOVT** | Secondary sources - Major news outlets and government announcements provide important context |
| **3 - US_NEWS** | Tertiary sources - US-focused news, lower priority for India-first focus |
| **4 - SPECIALTY** | Niche sources - Crypto and commodities are specialized verticals |

---

*Last updated: January 2026*
