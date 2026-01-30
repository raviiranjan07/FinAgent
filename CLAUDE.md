# FinAgent - AI Finance Content Intelligence System

> Context file for Claude and AI assistants working on this project.

---

## Vision

Build a trustworthy AI-driven finance media system that explains finance, markets, and policies clearly and calmly, with strict safety guardrails preventing harmful advice.

---

## What Is This Project?

FinAgent automatically:
1. **Ingests** financial news from 30+ RSS feeds (central banks, regulators, major news)
2. **Classifies** events by type and intent
3. **Generates** clear explanations using LLMs (Gemini/OpenRouter/Ollama)
4. **Validates** content safety (no advice, predictions, or hype)
5. **Reviews** risky content with HITL (Human In The Loop)
6. **Formats** for Twitter/X (single tweets or threads)
7. **Stores** in PostgreSQL with pgvector for semantic deduplication
8. **Displays** in React dashboard with real-time updates

---

## Content Safety Rules (CRITICAL)

### Strictly Prohibited
- ❌ Investment advice: "buy", "sell", "hold"
- ❌ Predictions or forecasts
- ❌ Guarantees or certainty
- ❌ Urgency or FOMO: "act now", "best time"
- ❌ Political opinions

### Forbidden Phrases (instant FAIL)
```
buy, sell, hold, invest now, best time, guaranteed returns,
you should, must act, risk-free, certain profit, recommended to, act now
```

### Safety Principle
> **"Silence is safer than speculation."**

---

## Current Phase: MVP

| Phase | Status |
|-------|--------|
| POC | ✅ COMPLETED |
| Pre-MVP | ✅ COMPLETED |
| **MVP** | 🔄 **IN PROGRESS** |

### MVP Features (Current)
- ✅ Content generation pipeline (RSS → LLM → Validation)
- ✅ HITL decision system (97.56% AI-human agreement)
- ✅ Content evaluation UI
- ✅ Twitter content generation (single tweets + threads)
- ✅ Content editing before publish
- ✅ Centralized evaluation queue (Content + Twitter)
- ✅ Scheduling system
- ✅ Twitter publishing integration (DRY RUN mode active)
- ✅ Architecture v2.0 refactoring (plugin namespace, versioning, validation)
- ✅ Automated RSS ingestion worker (runs every 4 hours)
- ✅ Automated Twitter publishing worker (runs every 60 seconds)
- ⏳ Analytics dashboard (pending)
- ⏳ Auto-approval system for high-confidence content (pending)

### Recent Updates (January 2026)

**Per-Source Backfill System** - Intelligent duplicate handling at fetch level:
- ✅ **Per-Source Deduplication:** Each RSS source independently fetches until quota is met with unique events
- ✅ **URL-Based Pre-Filtering:** Duplicate URLs filtered during fetch (before pipeline processing)
- ✅ **Newest Content Priority:** RSS entries sorted by published_at descending (most recent first)
- ✅ **Smart Quota Distribution:** Category quotas distributed evenly across sources
- ✅ **Database Integration:** Loads historical URLs from database (if enabled) or log file

**How It Works:**
1. Load all processed URLs from database/log file at startup
2. For each source, fetch events sorted by newest first
3. Check each URL against processed URLs
4. Keep fetching until source quota reached (or RSS feed exhausted)
5. Remaining semantic duplicates caught by DeduplicationAdapter in pipeline

**Example:** RBI_PRESS (quota: 2)
- RSS has 20 entries
- Fetch newest first
- Entry 1: New → Add (1/2)
- Entry 2: Duplicate URL → Skip
- Entry 3: New → Add (2/2)
- Quota reached, stop fetching

**Architecture v2.0 Refactoring** - Major improvements to scalability and data integrity:
- ✅ **Plugin Namespace:** ExecutionContext now uses `plugins` dict to prevent field bloat
- ✅ **Content Versioning:** Track which plugin/prompt/model generated each item
- ✅ **Pipeline Idempotency:** Unique constraints prevent duplicate processing
- ✅ **Smart Forbidden Words:** Boundary-aware detection (no false positives on "buyback", "sell-off")
- ✅ **JSON Schema Validation:** Pydantic schemas prevent malformed data
- ✅ **Qwen <think> Tag Fix:** v1.6-notoken prompts prevent reasoning token output
- 📄 See: `doc/ARCHITECTURE_REFACTORING_v2.0.md`, `doc/QWEN_THINK_TAG_FIX.md`

**Publishing Features:**
- ✅ **DRY RUN Mode:** Test publishing without real Twitter API calls
- ✅ **Mode Indicators:** Dashboard shows LIVE/DRY_RUN/DISABLED status
- ✅ **Delete Protection:** Can delete dry run items, protects live published content

---

## Architecture

### Content Pipeline
```
RSS Event → Adapters → Database → UI

Adapters (in order):
1. EmbeddingAdapter      - Vector embeddings (pgvector)
2. DeduplicationAdapter  - Semantic duplicate detection (cosine >0.85)
3. EventTypeAdapter      - Event classification
4. IntentAdapter         - Content intent
5. ContextAdapter        - LLM content generation
6. ClarityAdapter        - Safety validation
7. HITLDecisionAdapter   - Human review decision
8. DatabaseAdapter       - PostgreSQL + WebSocket notifications
9. LoggerAdapter         - JSONL logs
```

### Twitter Plugin Pipeline
```
Approved Output → Twitter Adapters → Content Queue → Publish

Twitter Adapters:
1. FormatDecisionAdapter - SINGLE vs THREAD
2. TwitterSingleAdapter  - Generate single tweet
3. TwitterThreadAdapter  - Generate thread (3 tweets)
4. TwitterClarityAdapter - Twitter-specific validation
5. TwitterHITLAdapter    - HITL decision for Twitter
```

---

## Project Structure

```
FinAgent/
├── adapters/              # Pipeline adapters
│   ├── event_type.py
│   ├── intent.py
│   ├── output.py
│   ├── clarity.py
│   ├── hitl.py
│   ├── embedding.py
│   ├── dedup.py
│   ├── database.py
│   └── plugins/twitter/  # Twitter generation pipeline
│
├── api/                   # FastAPI backend
│   ├── main.py           # App + WebSocket
│   ├── routes/           # REST API endpoints
│   └── websocket.py      # WebSocket manager
│
├── dashboard/             # React frontend (Vite + TypeScript + Tailwind)
│   ├── src/pages/        # Dashboard, Outputs, Evaluations, Stats
│   ├── src/components/   # UI components
│   └── src/hooks/        # useWebSocket
│
├── database/
│   ├── models.py         # SQLAlchemy ORM
│   ├── repository.py     # Data access layer
│   └── migrations/       # Schema migrations
│
├── services/
│   ├── llm_service.py    # Multi-provider LLM client
│   ├── hitl_service.py   # Centralized HITL logic
│   └── quota_manager.py  # API quota tracking
│
├── config/
│   ├── settings.py       # RSS sources, LLM config
│   └── prompts.py        # LLM prompts (validated)
│
├── run_pipeline.py       # Main pipeline entry point
└── run_twitter_plugin.py # Twitter content generation
```

---

## Running the System

### Prerequisites
- PostgreSQL running with `finagent` database
- Python virtual environment activated (`.venv`)
- LLM service configured (Gemini/Groq/Ollama)

### Start API Server
```bash
cd api
uvicorn main:app --reload --port 8001
```

### Start Dashboard
```bash
cd dashboard
npm run dev
```

### Run Content Pipeline (POC)
**Note:** There is NO `run_poc.py` file. The pipeline is run through the API or dashboard workflow:

1. **Via Dashboard:**
   - Navigate to http://localhost:5173
   - Outputs page shows processed events
   - Evaluate and approve content

2. **Via API:**
   - Events are fetched automatically from RSS sources
   - Use `/api/outputs` endpoint to see generated content
   - Use `/api/evaluations` endpoint to approve/reject

### Generate Twitter Content
```bash
# Generate Twitter content for a specific output
python run_twitter_plugin.py --output-id <output_id>

# Or use dashboard "Generate X Content" button on Approved Queue
```

### Access Points
- **Dashboard:** http://localhost:5173
- **API Docs:** http://localhost:8001/docs
- **Health Check:** http://localhost:8001/api/health
- **WebSocket:** ws://localhost:8001/ws

---

## Database Models

### Core Tables
- **events** - RSS feed events
- **outputs** - LLM-generated content
- **evaluations** - Human verdicts (PASS/FAIL)
- **content_queue** - Twitter content ready to publish
- **embeddings** - Vector embeddings for deduplication

---

## Critical Rules for AI Assistants

1. **NEVER add advice language** - "buy", "sell", "you should", etc.
2. **Root Cause Analysis First** - Always analyze bugs before proposing fixes
3. **Wait for Approval** - Get user approval before implementing fixes/features
4. **Adapter Contract** - Adapters process data, don't control flow
5. **Safety First** - When in doubt, err on the side of caution
6. **No POC references** - We are in MVP phase, not POC
7. **NEVER assume requirements** - If user request is ambiguous or unclear, ALWAYS ask for clarification first
8. **Confirm understanding before acting** - When user says "two tabs", ask if they mean separate pages or tabs within one page
9. **Only implement when explicitly asked** - Don't jump to implementation just because user asks "why" - they may only want explanation
10. **Listen carefully** - User's exact words matter - don't interpret or fill in gaps without confirming
11. **Qwen <think> Tags** - When using qwen models, prompts MUST include v1.6-notoken format to prevent reasoning token output (see `doc/QWEN_THINK_TAG_FIX.md`)

---

## Key Terminology

- **Content** - LLM-generated explanations from RSS events
- **Twitter/X** - Formatted tweets/threads from approved content
- **HITL** - Human-in-the-Loop (AI suggests, human decides)
- **Clarity** - Safety validation (no advice, predictions, etc.)
- **Evaluation** - Human review (PASS/FAIL verdict)

---

*Last updated: January 24, 2026 (MVP Phase - Architecture v2.0)*
