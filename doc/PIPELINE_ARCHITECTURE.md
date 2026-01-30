# FinAgent Pipeline Architecture - Complete Analysis

> **Generated:** January 24, 2026
> **System Status:** MVP Phase - Live Publishing Active

---

## 🔍 Executive Summary

**Total Pipelines Created: 4 Main Pipelines + 2 Supporting Services**

This document provides a complete analysis of all pipelines, adapters, and workflows implemented in the FinAgent system.

---

## 📊 Pipeline Overview

| Pipeline | Purpose | Entry Point | Status |
|----------|---------|-------------|--------|
| **1. Content Generation Pipeline** | RSS → LLM Explanation | `run_pipeline.py` | ✅ Production |
| **2. Twitter Formatting Pipeline** | Approved Content → Twitter Posts | `run_twitter_plugin.py` | ✅ Production |
| **3. Publishing Pipeline** | Twitter Posts → Live X | API + TwitterPublishingService | ✅ Live |
| **4. Evaluation Pipeline** | Human Review Workflow | Dashboard UI + API | ✅ Production |
| **5. Analytics Pipeline** | Usage Metrics & Tracking | Stats API + Dashboard | ✅ Production |
| **6. Quota Management Service** | LLM API Rate Limiting | QuotaManager | ✅ Production |

---

## 1️⃣ Content Generation Pipeline (POC/Pre-MVP)

### Purpose
Transform raw RSS financial news into safe, educational explanations.

### Entry Point
```bash
python run_pipeline.py
```

### Adapter Chain (9 Adapters)

```
┌─────────────────────────────────────────────────────────────────┐
│                 CONTENT GENERATION PIPELINE                      │
└─────────────────────────────────────────────────────────────────┘

RSS Feed
   │
   ▼
[1] EmbeddingAdapter ──────────► Generate vector embeddings (384-dim)
   │
   ▼
[2] DeduplicationAdapter ──────► Semantic similarity check (cosine > 0.85)
   │                              → If duplicate: SKIP remaining adapters
   ▼
[3] EventTypeAdapter ──────────► Classify into 6 event types
   │                              (FINANCE_POLICY, MARKET_MOVEMENT, etc.)
   ▼
[4] IntentAdapter ─────────────► Classify intent (EXPLANATORY/DESCRIPTIVE/MARKET_OPINION)
   │
   ▼
[5] ContextAdapter ────────────► Generate LLM explanation (200-400 words)
   │                              Uses: Groq/Gemini/Ollama with fallbacks
   ▼
[6] ClarityAdapter ────────────► Validate safety rules
   │                              - No advice (buy/sell/hold)
   │                              - No predictions
   │                              - No forbidden phrases
   ▼
[7] HITLDecisionAdapter ───────► Decide if human review needed
   │                              Risk levels: LOW/MEDIUM/HIGH
   ▼
[8] LoggerAdapter ─────────────► Log to JSONL file
   │
   ▼
[9] DatabaseAdapter ───────────► Save to PostgreSQL
   │
   ▼
Output Record (ready for evaluation)
```

### Configuration
- **Source Selection:** Priority-based category system (32 RSS sources)
- **Per-Source Quota:** Dynamic backfill (fetch until quota met)
- **Deduplication:** URL + Semantic (embedding similarity)
- **LLM Fallback Chain:** Groq → Gemini → Ollama
- **Safety:** Frozen prompts (v1.2) + CRITICAL OUTPUT FORMAT

### Key Features
- **Per-Source Backfill:** Each source independently fetches until quota reached
- **Early Deduplication:** Skips expensive LLM calls for duplicates
- **Multi-Model Support:** Automatic fallback on quota exhaustion
- **Quota Tracking:** JSON-based quota status with auto-reset

### Output Schema
```python
Output {
    id: UUID
    event_id: UUID (foreign key)
    event_type: str (6 categories)
    intent: str (3 categories)
    llm_output: str (200-400 words)
    clarity_passed: bool
    clarity_issues: list
    hitl_required: bool
    generation_metadata: dict  # model, tokens, timing
}
```

---

## 2️⃣ Twitter Formatting Pipeline

### Purpose
Convert approved 200-400 word explanations into Twitter-optimized content (≤280 chars).

### Entry Point
```bash
python run_twitter_plugin.py [--output-id <UUID>]
```

### Adapter Chain (5 Adapters)

```
┌─────────────────────────────────────────────────────────────────┐
│                 TWITTER FORMATTING PIPELINE                      │
└─────────────────────────────────────────────────────────────────┘

Approved Output (from Pipeline 1)
   │
   ▼
[1] FormatDecisionAdapter ─────► Decide SINGLE vs THREAD
   │                              Rules:
   │                              - FINANCE_POLICY → THREAD
   │                              - MACRO_ECONOMIC → THREAD
   │                              - EXPLANATORY intent → THREAD
   │                              - Default → SINGLE
   ▼
[2] TwitterSingleAdapter ──────► Generate single tweet (250-260 chars)
   │                              Uses: TWITTER_GENERATION_SINGLE prompt
   │                              ChatGPT-style skepticism framing
   ▼
[3] TwitterThreadAdapter ──────► Generate 3-tweet thread
   │                              Uses: TWITTER_GENERATION_THREAD prompt
   │                              Tweet1: 🧵 + question
   │                              Tweet2: Mechanism/data
   │                              Tweet3: #hashtags
   ▼
[4] TwitterClarityAdapter ─────► Validate Twitter content
   │                              - Character count (≤280)
   │                              - Forbidden phrases (stricter than POC)
   │                              - No compound word false positives
   ▼
[5] TwitterHITLAdapter ────────► HITL decision (uses centralized service)
   │
   ▼
ContentQueue Record (ready_to_schedule)
```

### Prompt Engineering (v1.6-notoken)
- **CRITICAL OUTPUT FORMAT Section:** Prevents metadata/reasoning tokens
- **FORBIDDEN ADDITIONS List:** 6 categories of banned output
- **Defense-in-Depth:** Prompt + Model-level cleaning

### Twitter Content Strategies
```python
TWITTER_CONTENT_STRATEGIES = {
    "MARKET_MOVEMENT": "Question VAGUE narratives, state CLEAR triggers plainly",
    "FINANCE_POLICY": "State policy + question OFFICIAL NARRATIVE if vague",
    "MACRO_ECONOMIC": "State indicator + question EXPLANATION if unsupported",
    "EXPLANATORY": "State concept + challenge COMMON MISCONCEPTIONS"
}
```

### Output Schema
```python
ContentQueue {
    id: UUID
    output_id: UUID (foreign key)
    format: "SINGLE" | "THREAD"
    thread_length: int (1 or 3)
    content_text: str (JSON-encoded tweets)
    edited_content: str | null
    status: "ready_to_schedule" | "failed" | "published"
    plugin_version: "twitter-v1.6-notoken"
    prompt_version: str
    model_used: str
}
```

---

## 3️⃣ Publishing Pipeline

### Purpose
Post approved Twitter content to X (formerly Twitter).

### Entry Point
```
API: POST /twitter/publish/{content_queue_id}
Dashboard: "Publish to X" button
```

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     PUBLISHING PIPELINE                          │
└─────────────────────────────────────────────────────────────────┘

ContentQueue (ready_to_schedule)
   │
   ▼
[API Route] /twitter/publish/{id}
   │
   ▼
[Publishing Mode Check]
   ├──► DISABLED → Error: Publishing disabled
   ├──► DRY_RUN → Simulate (fake tweet_id: "dry_run_{uuid}")
   └──► LIVE → Continue to real API
         │
         ▼
[TwitterPublishingService]
         │
         ▼
[Format Handler]
   ├──► SINGLE → TwitterAPIClient.post_tweet(text)
   └──► THREAD → TwitterAPIClient.post_thread([tweet1, tweet2, tweet3])
         │
         ▼
[Twitter API v2]
         │
         ▼
[Update ContentQueue]
   - status = "published"
   - twitter_post_id = actual_tweet_id
   - twitter_url = "https://x.com/..."
   - published_at = now()
         │
         ▼
✅ Published to X
```

### Publishing Modes
| Mode | Behavior | Use Case | Indicator |
|------|----------|----------|-----------|
| **DISABLED** | Reject all publish requests | Maintenance | ⏸️ |
| **DRY_RUN** | Simulate (no real API call) | Testing | 🧪 |
| **LIVE** | Post to real X account | Production | 🔴 |

### Configuration (.env)
```bash
TWITTER_PUBLISHING_ENABLED=true
TWITTER_DRY_RUN=false  # false = LIVE mode
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
```

### Safety Features
- **Mode Banners:** UI shows current mode prominently
- **Live Post Protection:** Cannot delete items with LIVE twitter_post_id
- **Dry Run Badges:** Clear visual distinction (🧪 DRY RUN vs ✓ LIVE)
- **Pre-Publish Validation:** Character count, safety checks

---

## 4️⃣ Evaluation Pipeline (HITL Workflow)

### Purpose
Human-in-the-loop review and approval workflow for content quality assurance.

### Entry Point
```
Dashboard: /evaluations page
API: GET /outputs, POST /evaluations
```

### Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVALUATION PIPELINE                          │
└─────────────────────────────────────────────────────────────────┘

Output (from Pipeline 1)
   │
   ▼
[Dashboard UI] /evaluations
   │
   ▼
[Human Reviewer]
   ├──► Read event + LLM output
   ├──► Check clarity issues
   ├──► Review HITL suggestion
   └──► Make decision
         │
         ▼
[Verdict Selection]
   ├──► PASS → Approve for Twitter formatting
   └──► FAIL → Select reason + add notes
         │
         ▼
[API] POST /evaluations
   │
   ▼
[Save Evaluation Record]
   - verdict: PASS/FAIL
   - failure_reason: str | null
   - evaluator_notes: str
   - suggested_verdict: str (AI prediction)
   - agreement: bool (AI == Human)
         │
         ▼
[PASS outputs] ──► Available for Pipeline 2
[FAIL outputs] ──► Logged for analysis
```

### HITL Exit Criteria Tracking
- **Target:** 90% AI-Human agreement rate
- **Current Metrics:**
  - Overall agreement rate
  - False positive rate (AI says PASS, human says FAIL)
  - Confusion matrix (PP, PF, FP, FF)
  - Recent trend (last 30 evaluations)
  - Disagreement examples for pattern analysis

### Evaluation Schema
```python
Evaluation {
    id: UUID
    output_id: UUID (foreign key)
    verdict: "PASS" | "FAIL"
    failure_reason: str | null
    evaluator_notes: str
    suggested_verdict: str (from HITLDecisionAdapter)
    suggested_verdict_reason: str
    evaluator: str (default: "human")
}
```

---

## 5️⃣ Analytics Pipeline

### Purpose
Track publishing performance, HITL metrics, and content distribution.

### Entry Point
```
Dashboard: /stats page
API: GET /stats/dashboard, /stats/publishing-analytics
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYTICS PIPELINE                           │
└─────────────────────────────────────────────────────────────────┘

[Data Sources]
   ├──► Events (RSS ingestion)
   ├──► Outputs (LLM generation)
   ├──► Evaluations (human review)
   └──► ContentQueue (Twitter publishing)
         │
         ▼
[Repository Queries]
   ├──► count_by_event_type()
   ├──► count_by_source()
   ├──► get_failure_reasons()
   ├──► get_agreement_metrics()
   └──► get_publishing_analytics(days)
         │
         ▼
[Stats API Routes]
   ├──► /stats/dashboard ──────► Overview metrics
   ├──► /stats/hitl-metrics ───► AI-Human agreement
   └──► /stats/publishing-analytics ─► Daily publishing stats
         │
         ▼
[Dashboard UI Components]
   ├──► Publishing Analytics Chart (Bar chart)
   ├──► HITL Progress Bar
   ├──► Event Type Distribution
   ├──► Failure Analysis
   └──► Source Distribution
```

### Key Metrics Tracked

#### Publishing Analytics
- **Total Published:** Count of LIVE tweets (excludes dry runs)
- **By Format:** SINGLE vs THREAD breakdown
- **Daily Trend:** Last 7/15/30 days
- **Chart:** Stacked bar chart (date → single_count + thread_count)

#### HITL Metrics
- **Agreement Rate:** % of AI-Human agreement
- **False Positive Rate:** AI says PASS, human says FAIL
- **Confusion Matrix:** PP, PF, FP, FF
- **Recent Trend:** Last 30 evaluations
- **Disagreement Examples:** Top 5 mismatches

#### Content Distribution
- **Event Types:** 6 categories with percentages
- **Sources:** 32 RSS sources with counts
- **Failure Reasons:** Top causes of clarity failures

---

## 6️⃣ Quota Management Service

### Purpose
Track and enforce LLM API rate limits across providers.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  QUOTA MANAGEMENT SERVICE                        │
└─────────────────────────────────────────────────────────────────┘

[QuotaManager]
   │
   ├──► .quota_status.json (persistent state)
   │     {
   │       "gemini": {
   │         "exhausted": true,
   │         "reset_at": "2026-01-25T08:00:00",
   │         "last_429_at": "2026-01-24T09:00:11"
   │       },
   │       "openrouter": {...}
   │     }
   │
   ├──► check_quota(provider) ─────► Returns: available | exhausted
   ├──► record_429(provider) ───────► Marks exhausted + sets reset time
   └──► reset_if_time_passed() ────► Auto-reset after cooldown
         │
         ▼
[LLMService Integration]
   │
   ├──► Primary: Groq (free tier, high quota)
   │     └──► On 429: record_429("groq") → fallback to Gemini
   │
   ├──► Secondary: Gemini (500 RPD)
   │     └──► On 429: record_429("gemini") → fallback to Ollama
   │
   └──► Tertiary: Ollama (local, unlimited)
         └──► No quota tracking needed
```

### Provider Quotas
| Provider | Free Tier | Reset Period | Status File Key |
|----------|-----------|--------------|-----------------|
| **Groq** | High (unspecified) | 60 seconds | `groq` |
| **Gemini** | 500 RPD, 15 RPM | 8 AM UTC daily | `gemini` |
| **Ollama** | Unlimited (local) | N/A | N/A |

### Auto-Reset Logic
- **Minute-level quotas:** Reset after 60 seconds
- **Daily quotas:** Reset at 8 AM UTC (midnight Pacific)
- **Persistent state:** Survives process restarts

---

## 🔧 Supporting Services

### 1. LLMService
- **Multi-provider support:** Groq, Gemini, Ollama
- **Fallback chain:** Primary → Secondary → Tertiary
- **Model-level cleaning:** Strips `<think>` tags, metadata, character counts
- **Retry logic:** Exponential backoff with 3 attempts

### 2. TwitterAPIClient
- **Twitter API v2 wrapper**
- **OAuth 1.0a authentication**
- **Methods:**
  - `post_tweet(text)` → Single tweet
  - `post_thread(tweets)` → Thread with reply chaining

### 3. HITLService (Centralized)
- **Risk assessment:** Analyzes clarity issues
- **Verdict suggestion:** PASS/FAIL recommendation
- **Shared logic:** Used by both POC and Twitter pipelines

### 4. SmartScheduler
- **Future:** Optimal posting times
- **Current:** Not yet implemented

### 5. DataRetentionService
- **Future:** Archive old events
- **Current:** Not yet implemented

---

## 📂 File Structure

```
FinAgent/
├── run_pipeline.py           # PIPELINE 1: Content Generation
├── run_twitter_plugin.py     # PIPELINE 2: Twitter Formatting
│
├── adapters/                 # Core pipeline adapters
│   ├── embedding.py          # [P1] Vector embeddings
│   ├── dedup.py              # [P1] Semantic deduplication
│   ├── event_type.py         # [P1] Event classification
│   ├── intent.py             # [P1] Intent classification
│   ├── output.py             # [P1] LLM generation
│   ├── clarity.py            # [P1] Safety validation
│   ├── hitl.py               # [P1] HITL decision
│   ├── logger.py             # [P1] JSONL logging
│   ├── database.py           # [P1] PostgreSQL persistence
│   │
│   └── plugins/twitter/      # Twitter plugin adapters
│       ├── format_decision.py  # [P2] SINGLE vs THREAD
│       ├── twitter_single.py   # [P2] Generate single tweet
│       ├── twitter_thread.py   # [P2] Generate thread
│       ├── twitter_clarity.py  # [P2] Validate Twitter content
│       └── twitter_hitl.py     # [P2] HITL for Twitter
│
├── services/                 # Supporting services
│   ├── llm_service.py        # Multi-provider LLM with fallback
│   ├── quota_manager.py      # API rate limit tracking
│   ├── hitl_service.py       # Centralized HITL logic
│   ├── twitter_api_client.py # Twitter API v2 wrapper
│   └── twitter_publishing_service.py  # [P3] Publishing orchestrator
│
├── api/                      # FastAPI backend
│   ├── main.py               # API entry point
│   └── routes/
│       ├── twitter_content.py  # Twitter generation + publishing
│       ├── stats.py            # [P5] Analytics API
│       ├── evaluations.py      # [P4] HITL workflow
│       ├── outputs.py          # Output management
│       └── events.py           # Event management
│
├── dashboard/                # React frontend
│   └── src/
│       └── pages/
│           ├── GeneratedContent.tsx  # [P3] Publishing UI
│           ├── Stats.tsx             # [P5] Analytics UI
│           ├── Evaluations.tsx       # [P4] HITL UI
│           └── ApprovedQueue.tsx     # [P4] Approved outputs
│
├── config/
│   ├── prompts.py            # Frozen prompts (v1.2 POC, v1.6 Twitter)
│   └── settings.py           # RSS sources, categories, quotas
│
└── database/
    ├── models.py             # SQLAlchemy ORM
    └── repository.py         # Data access layer
```

---

## 🔄 Complete Data Flow (End-to-End)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE SYSTEM FLOW                               │
└──────────────────────────────────────────────────────────────────────────┘

[1] RSS INGESTION (Pipeline 1: Content Generation)
    32 RSS Sources → Priority Selection → Dedup → Classification → LLM Generation → Validation
    ↓
    Output Record (200-400 words, safety validated)

[2] HUMAN EVALUATION (Pipeline 4: Evaluation Workflow)
    Dashboard → Human Review → PASS/FAIL Verdict → Evaluation Record
    ↓
    Approved Outputs (PASS verdict only)

[3] TWITTER FORMATTING (Pipeline 2: Twitter Formatting)
    Approved Output → Format Decision → Tweet Generation → Twitter Validation
    ↓
    ContentQueue Record (≤280 chars, ready to publish)

[4] PUBLISHING (Pipeline 3: Publishing Pipeline)
    Dashboard → Publish Button → Publishing Mode Check → Twitter API → Live Tweet
    ↓
    Published Content (twitter_post_id, twitter_url)

[5] ANALYTICS (Pipeline 5: Analytics Pipeline)
    Published Content → Daily Aggregation → Stats API → Dashboard Charts
    ↓
    Publishing Metrics (total published, daily trend, format breakdown)
```

---

## 📊 Pipeline Statistics

| Metric | Count |
|--------|-------|
| **Total Pipelines** | 4 main + 2 supporting |
| **Total Adapters** | 14 adapters (9 POC + 5 Twitter) |
| **Total API Routes** | 10 route files |
| **Total Services** | 8 service classes |
| **Dashboard Pages** | 7 pages |
| **RSS Sources** | 32 sources |
| **Source Categories** | 8 categories (prioritized) |
| **LLM Providers** | 3 (Groq, Gemini, Ollama) |
| **Safety Rules** | 2 levels (POC + Twitter stricter) |
| **Publishing Modes** | 3 (DISABLED, DRY_RUN, LIVE) |

---

## 🎯 Current System Status

### ✅ Production-Ready Features
1. **Content Generation Pipeline** - Fully operational
2. **Twitter Formatting Pipeline** - Fully operational
3. **Live Publishing** - Active (LIVE mode enabled)
4. **Human Evaluation** - Active workflow
5. **Analytics Dashboard** - Real-time metrics
6. **Quota Management** - Multi-provider fallback
7. **Defense-in-Depth Safety** - Prompt + model-level

### 🚧 In Progress
1. **HITL Exit Criteria** - Targeting 90% agreement rate
2. **Smart Scheduling** - Optimal posting times (planned)
3. **Data Retention** - Archive old events (planned)

### 🔮 Future Enhancements
1. **Multi-platform Publishing** - LinkedIn, Newsletter
2. **A/B Testing** - Test different tweet styles
3. **Engagement Analytics** - Track likes, retweets, replies
4. **Automated Reposting** - High-performing content
5. **Content Personalization** - Audience segmentation

---

## 🔐 Safety Architecture (Multi-Layer)

```
Layer 1: Prompt Level (Prevention)
   ├──► CRITICAL OUTPUT FORMAT section
   ├──► FORBIDDEN ADDITIONS list
   ├──► INCORRECT/CORRECT examples
   └──► Explicit safety rules

Layer 2: Model Level (Enforcement)
   ├──► _clean_model_output() regex patterns
   ├──► Strip <think> tags
   ├──► Remove metadata annotations
   └──► Remove character counts

Layer 3: Validation Level (Detection)
   ├──► ClarityAdapter (POC content)
   ├──► TwitterClarityAdapter (Twitter content)
   ├──► Forbidden phrase checks
   └──► Character count validation

Layer 4: Human Level (Verification)
   ├──► Evaluation workflow
   ├──► HITL decision review
   └──► Pre-publish approval
```

---

## 📈 Scalability Considerations

### Current Architecture Strengths
✅ **Modular Adapter Design** - Easy to add new adapters
✅ **Multi-Provider Fallback** - Resilient to quota limits
✅ **Database Persistence** - Supports horizontal scaling
✅ **API-First Architecture** - Decoupled frontend/backend
✅ **Per-Source Backfill** - Independent source processing

### Potential Bottlenecks
⚠️ **LLM API Quotas** - Limited by free tier rates
⚠️ **Semantic Deduplication** - Embedding generation cost
⚠️ **Twitter API Limits** - Rate limits on posting

### Scaling Strategy
1. **Upgrade to paid LLM tiers** - Higher quotas
2. **Implement request batching** - Reduce API calls
3. **Add caching layer** - Redis for embeddings
4. **Deploy to cloud** - AWS/GCP for auto-scaling
5. **Queue-based processing** - RabbitMQ/Celery for async jobs

---

## 🎓 Key Learnings & Decisions

### 1. **Defense-in-Depth for Prompt Compliance**
- **Problem:** Qwen models ignored prompt instructions, outputting metadata
- **Solution:** Two-layer approach (prompt + model-level cleaning)
- **Result:** 100% compliance with output format

### 2. **Per-Source Backfill Architecture**
- **Problem:** Category quotas left unfilled when sources had duplicates
- **Solution:** Each source fetches independently until quota met
- **Result:** Predictable quotas, better source diversity

### 3. **Publishing Mode Indicators**
- **Problem:** Risk of accidental live posts during testing
- **Solution:** Prominent mode banners (DRY_RUN vs LIVE)
- **Result:** Clear visibility, safer operations

### 4. **Centralized HITL Service**
- **Problem:** HITL logic duplicated across POC and Twitter pipelines
- **Solution:** Shared HITLService with consistent risk assessment
- **Result:** Unified HITL logic, easier maintenance

### 5. **Quota Management with JSON State**
- **Problem:** Quota exhaustion caused cascading failures
- **Solution:** Persistent quota tracking with auto-reset
- **Result:** Graceful degradation, automatic recovery

---

## 📚 Related Documentation

- **POC Documentation:** `doc/POC.md` (frozen, historical)
- **Pre-MVP Documentation:** `doc/PRE-MVP.md` (frozen, historical)
- **MVP Documentation:** `doc/MVP.md` (current phase)
- **Twitter Plugin Plan:** `doc/TWITTER_DUAL_FORMAT_PLAN.md`
- **Migration Guide:** `MIGRATION_GUIDE.md`
- **Quota Management:** `QUOTA_MANAGEMENT_GUIDE.md`
- **Project Instructions:** `CLAUDE.md` (AI assistant context)

---

**Last Updated:** January 24, 2026
**System Version:** MVP Phase
**First Live Tweet:** ✅ Published
**Status:** Production (LIVE mode active)
