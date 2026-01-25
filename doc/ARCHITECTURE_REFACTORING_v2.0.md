# Architecture Refactoring v2.0

**Date:** January 24, 2026
**Status:** Phase 1 & 2 Complete
**Impact:** All Twitter plugin code

---

## Overview

This document describes the architectural improvements made to fix scalability and data integrity issues in the FinAgent codebase.

## Problems Addressed

### Critical Issues (Fixed)

1. **ExecutionContext Growing Unbounded** - Plugin fields polluting core context
2. **No Schema Validation for JSON Fields** - Malformed data causing runtime errors
3. **Forbidden Word Detection Too Naive** - False positives on technical terms
4. **Migration Drift** - Database schema and models out of sync
5. **No Content Version Tracking** - Can't trace which version generated content
6. **Pipeline Not Idempotent** - Duplicate processing possible

---

## Phase 1: Low-Risk Fixes (✅ Complete)

### Fix 1: Content Version Tracking

**Problem:** No way to trace which plugin version, prompt, or model generated each content item.

**Solution:** Added versioning fields to `content_queue` table.

**Migration:** `008_add_content_versioning.sql`
```sql
ALTER TABLE content_queue
ADD COLUMN plugin_version VARCHAR(50),
ADD COLUMN prompt_version VARCHAR(100),
ADD COLUMN model_used VARCHAR(100),
ADD COLUMN generation_timestamp TIMESTAMP,
ADD COLUMN generation_context JSONB DEFAULT '{}';
```

**Model Changes:** `database/models.py`
```python
class ContentQueue(Base):
    # ...existing fields...

    # Generation tracking
    plugin_version = Column(String(50))
    prompt_version = Column(String(100))
    model_used = Column(String(100))
    generation_timestamp = Column(DateTime)
    generation_context = Column(JSONB, default=dict)
```

**Usage Example:**
```python
content_queue = ContentQueue(
    # ...content fields...
    plugin_version="twitter-v1.6-notoken",
    prompt_version="TWITTER_GENERATION_THREAD_v1.6-notoken",
    model_used="qwen/qwen3-32b",
    generation_timestamp=datetime.utcnow(),
    generation_context={
        "twitter_mode": "groq",
        "model": "qwen/qwen3-32b",
        "generation_time_ms": 2440
    }
)
```

**Benefits:**
- Can compare output quality across prompt versions
- Debug issues by identifying which model generated problematic content
- A/B test different generation approaches
- Audit trail for compliance

---

### Fix 2: Pipeline Idempotency

**Problem:** Running Twitter plugin twice on same output creates duplicates. No retry logic for failures.

**Solution:** Added unique constraint + retry logic for failed items.

**Migration:** `009_add_output_id_unique_constraint.sql`
```sql
-- Delete existing duplicates (keep most recent)
WITH duplicates AS (
    SELECT id, output_id,
           ROW_NUMBER() OVER (PARTITION BY output_id ORDER BY created_at DESC) as rn
    FROM content_queue
)
DELETE FROM content_queue
WHERE id IN (SELECT id FROM duplicates WHERE rn > 1);

-- Add unique constraint
ALTER TABLE content_queue
ADD CONSTRAINT unique_content_queue_output_id UNIQUE (output_id);
```

**Code Changes:** `run_twitter_plugin.py`
```python
# Check if already processed
existing = db.query(ContentQueue).filter(ContentQueue.output_id == output_id).first()
if existing:
    # Allow retry for failed items
    if existing.status == 'failed':
        print(f"[Retry] Found failed attempt, deleting and retrying...")
        db.delete(existing)
        db.commit()
    else:
        return {
            "success": False,
            "error": f"Already processed with status: {existing.status}",
            "content_queue_id": str(existing.id)
        }

# ...later, handle race conditions...
try:
    db.commit()
except Exception as commit_error:
    if "unique_content_queue_output_id" in str(commit_error).lower():
        db.rollback()
        return {"error": "Already processed (race condition detected)"}
    else:
        raise
```

**Benefits:**
- Prevents duplicate content in queue
- Failed items can be retried automatically
- Race conditions handled gracefully
- Database enforces data integrity

---

### Fix 3: Forbidden Word Detection

**Problem:** Naive word matching causes false positives:
- "buyback" triggers "buy"
- "sell-off" triggers "sell"
- "you shouldn't panic" triggers "you should"

**Solution:** Boundary-aware regex + whitelist exceptions.

**Implementation:** `utils/forbidden_words.py`
```python
import re

# Word boundary patterns
FORBIDDEN_PATTERNS = {
    r'\bbuy\b': "buy",
    r'\bsell\b': "sell",
    r'\byou should\b': "you should",
    # ...more patterns...
}

# Whitelist for compound terms
WHITELIST_TERMS = {
    "buyback": "buy",
    "buydown": "buy",
    "sell-off": "sell",
    "shareholder": "hold",
    # ...more terms...
}

def detect_forbidden_phrases(text: str) -> List[Tuple[str, str]]:
    """Detect forbidden phrases with context awareness."""
    issues = []
    text_lower = text.lower()

    for pattern, description in FORBIDDEN_PATTERNS.items():
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)

        for match in matches:
            # Check if match is part of whitelisted compound
            if not is_whitelisted(text, match.start(), match.end(), description):
                context = extract_context(text, match.start(), match.end())
                issues.append((match.group(), context))

    return issues
```

**Test Results:**
```
✅ CLEAN: Company announces share buyback program
✅ CLEAN: Mortgage buydown reduces your interest rate
✅ CLEAN: Market sell-off continues
✅ CLEAN: Shareholders approve buyback
❌ DETECTED: You should buy this stock now → 'buy', 'you should'
❌ DETECTED: Investors sell holdings → 'sell'
```

**Updated Adapters:**
- `adapters/clarity.py` - POC content validation
- `adapters/plugins/twitter/twitter_clarity.py` - Twitter content validation

**Benefits:**
- Fewer false positives on technical terms
- Context-aware detection
- Easy to add new exceptions
- Better user experience

---

## Phase 2: Structural Changes (✅ Complete)

### Fix 1: ExecutionContext Plugin Namespace

**Problem:** Every plugin adds fields to core ExecutionContext, causing unbounded growth.

**Before:**
```python
class ExecutionContext(BaseModel):
    # Core fields
    event: Event
    event_type: Optional[str]
    intent: Optional[str]

    # Twitter fields (polluting core)
    twitter_format: Optional[dict]
    twitter_content: Optional[dict]
    twitter_clarity_issues: List[str]
    twitter_hitl: Optional[HITLDecision]

    # What happens when we add LinkedIn, Newsletter, YouTube?
    # linkedin_format: Optional[dict]
    # linkedin_content: Optional[dict]
    # newsletter_format: Optional[dict]
    # newsletter_content: Optional[dict]
    # ...50+ more fields?
```

**After:**
```python
class ExecutionContext(BaseModel):
    # Core fields
    event: Event
    event_type: Optional[str]
    intent: Optional[str]

    # Plugin namespace (NEW - v2.0)
    plugins: Dict[str, Any] = {}

    # Helper methods
    def get_plugin_data(self, plugin_name: str, default=None) -> Any:
        return self.plugins.get(plugin_name, default)

    def update_plugin_data(self, plugin_name: str, updates: Dict[str, Any]):
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
        self.plugins[plugin_name].update(updates)
```

**Usage Example:**
```python
# Twitter plugin stores data in its namespace
context.update_plugin_data("twitter", {
    "format": {"format": "THREAD", "thread_length": 3},
    "content": {"tweets": ["Tweet 1", "Tweet 2", "Tweet 3"]},
    "clarity_passed": True,
    "hitl": {"required": True, "risk_level": "MEDIUM"}
})

# LinkedIn plugin (future) stores in its namespace
context.update_plugin_data("linkedin", {
    "format": "ARTICLE",
    "content": {"title": "...", "body": "..."},
    "clarity_passed": True
})

# Access plugin data
twitter_data = context.get_plugin_data("twitter")
format_decision = twitter_data["format"]
```

**Backward Compatibility:**
```python
class ExecutionContext(BaseModel):
    # ...core fields...
    plugins: Dict[str, Any] = {}

    # DEPRECATED - kept for backward compatibility
    # TODO: Remove after migration complete
    twitter_format: Optional[dict] = None
    twitter_content: Optional[dict] = None
    twitter_clarity_issues: List[str] = []
```

**Migration Strategy:**
All Twitter adapters now write to BOTH locations:
```python
# NEW: Plugin namespace
context.update_plugin_data("twitter", {"format": decision})

# OLD: Legacy field (for backward compatibility)
context.twitter_format = decision
```

**Updated Adapters:**
- ✅ `FormatDecisionAdapter` - Writes format to plugin namespace
- ✅ `TwitterSingleAdapter` - Writes content to plugin namespace
- ✅ `TwitterThreadAdapter` - Writes content to plugin namespace
- ✅ `TwitterClarityAdapter` - Reads/writes clarity results
- ✅ `TwitterHITLAdapter` - Reads/writes HITL decision

**Benefits:**
- Scalable to unlimited plugins
- Clean separation of concerns
- Easy to add new platforms
- Backward compatible during migration

---

### Fix 2: JSON Field Validation

**Problem:** `content_text` field stores JSON but has no schema validation, leading to malformed data.

**Examples of Bad Data:**
```json
// Old format (malformed)
{"format": "THREAD", "tweet_count": 3, "tweets": {"tweet1": "...", "tweet2": "...", "tweet3": "..."}}

// New format (correct)
["Tweet 1", "Tweet 2", "Tweet 3"]
```

**Solution:** Pydantic schemas for all JSON fields.

**Implementation:** `database/schemas.py`

```python
from pydantic import BaseModel, Field, validator

class TwitterSingleContent(BaseModel):
    """Schema for SINGLE format content."""
    tweet: str = Field(..., min_length=1, max_length=280)

    def to_db_format(self) -> str:
        """Convert to database storage (plain string)."""
        return self.tweet

    @classmethod
    def from_db_format(cls, db_value: str):
        """Load from database."""
        return cls(tweet=db_value)


class TwitterThreadContent(BaseModel):
    """Schema for THREAD format content."""
    tweets: List[str] = Field(..., min_items=3, max_items=3)

    @validator('tweets')
    def validate_tweets(cls, tweets):
        if len(tweets) != 3:
            raise ValueError(f"Thread must have exactly 3 tweets, got {len(tweets)}")
        for i, tweet in enumerate(tweets, 1):
            if len(tweet) > 280:
                raise ValueError(f"Tweet {i} exceeds 280 chars")
        return [t.strip() for t in tweets]

    def to_db_format(self) -> str:
        """Convert to database storage (JSON array)."""
        return json.dumps(self.tweets)

    @classmethod
    def from_db_format(cls, db_value: str):
        """Load from database."""
        return cls(tweets=json.loads(db_value))


class TwitterContent(BaseModel):
    """Unified schema for Twitter content."""
    format: str = Field(..., pattern="^(SINGLE|THREAD)$")
    content: Any  # TwitterSingleContent or TwitterThreadContent

    def to_db_format(self) -> str:
        return self.content.to_db_format()

    @classmethod
    def from_db_format(cls, format_type: str, db_value: str):
        if format_type == 'SINGLE':
            content = TwitterSingleContent.from_db_format(db_value)
        else:
            content = TwitterThreadContent.from_db_format(db_value)
        return cls(format=format_type, content=content)
```

**Usage in Code:**

**Storing content:**
```python
# run_twitter_plugin.py
from database.schemas import TwitterThreadContent

# Validate before storing
schema = TwitterThreadContent(tweets=[
    twitter_content["tweets"]["tweet1"],
    twitter_content["tweets"]["tweet2"],
    twitter_content["tweets"]["tweet3"]
])

# Store validated content
content_text = schema.to_db_format()  # Returns: '["Tweet 1", "Tweet 2", "Tweet 3"]'
```

**Loading content:**
```python
# api/routes/twitter_content.py
from database.schemas import safe_load_twitter_content

# Safe loading with error handling
twitter_content = safe_load_twitter_content(item.format, item.content_text)

if twitter_content:
    # Successfully parsed
    tweets = twitter_content.content.tweets
else:
    # Malformed content - handle gracefully
    tweets = []
```

**Validation Tests:**
```
✅ Valid SINGLE: "RBI announces repo rate at 6.5%"
❌ Empty SINGLE: "" → Rejected (min 1 char)
❌ Long SINGLE: "x" * 300 → Rejected (max 280 chars)
✅ Valid THREAD: ["Tweet 1", "Tweet 2", "Tweet 3"]
❌ Short THREAD: ["Tweet 1", "Tweet 2"] → Rejected (must have 3)
❌ Long THREAD: ["Tweet 1", "Tweet 2", "Tweet 3", "Tweet 4"] → Rejected (max 3)
```

**Benefits:**
- Prevents malformed data from entering database
- Runtime errors caught at write-time, not read-time
- Clear error messages for debugging
- Type safety for JSON fields
- Easy to add validation rules

---

## Summary of Changes

### Database Migrations
```
008_add_content_versioning.sql        - Added version tracking fields
009_add_output_id_unique_constraint.sql - Prevented duplicate processing
```

### New Files
```
utils/forbidden_words.py     - Smart forbidden word detection
database/schemas.py          - Pydantic schemas for validation
```

### Modified Files
```
adapters/context.py                                - Added plugin namespace
adapters/clarity.py                                - Uses smart detection
adapters/plugins/twitter/format_decision.py        - Writes to plugin namespace
adapters/plugins/twitter/twitter_single.py         - Writes to plugin namespace
adapters/plugins/twitter/twitter_thread.py         - Writes to plugin namespace
adapters/plugins/twitter/twitter_clarity.py        - Uses smart detection + namespace
adapters/plugins/twitter/twitter_hitl.py           - Uses plugin namespace
database/models.py                                 - Added versioning fields
run_twitter_plugin.py                              - Schema validation + versioning
api/routes/twitter_content.py                      - Schema validation on read
```

### Test Results
```
✅ Content version tracking working
✅ Unique constraint preventing duplicates
✅ Retry logic for failed items
✅ Forbidden word whitelist working (buyback, sell-off, etc.)
✅ Plugin namespace isolating data
✅ Schema validation catching malformed content
✅ All existing tests passing (backward compatible)
```

---

## Migration Status

### Phase 1: Low-Risk Fixes ✅
- [x] Content version tracking
- [x] Pipeline idempotency
- [x] Forbidden word detection

### Phase 2: Structural Changes ✅
- [x] ExecutionContext plugin namespace
- [x] JSON field validation

### Phase 3: Tooling (Pending)
- [ ] Alembic setup for auto-migration generation
- [ ] Remove deprecated ExecutionContext fields
- [ ] Add LinkedIn plugin (test scalability)

---

## Rollback Plan

If issues arise, rollback is safe:

1. **Phase 1 fixes** - Additive only, can be ignored
2. **Phase 2 fixes** - Backward compatible, old code still works
3. **Database migrations** - Can rollback with:
   ```sql
   ALTER TABLE content_queue DROP COLUMN plugin_version;
   ALTER TABLE content_queue DROP CONSTRAINT unique_content_queue_output_id;
   ```

---

## Next Steps

1. **Monitor production** - Watch for schema validation errors
2. **Deprecation timeline** - Plan removal of legacy `twitter_*` fields
3. **Add new plugins** - Test scalability with LinkedIn plugin
4. **Documentation** - Update API docs with new schemas

---

## References

- Original architecture issues documented in: `doc/SYSTEM_ARCHITECTURE.md`
- Migration files: `database/migrations/008_*.sql`, `009_*.sql`
- Test coverage: All existing tests pass + new validation tests added
