# FinAgent MVP Plan
**AI Finance Media & Intelligence System**

---

## Executive Summary

**Current Phase:** MVP Phase 2 ✅ COMPLETED - Phases 1-2 Done, Phase 3 In Progress

**Timeline:** 2-3 weeks remaining

**Primary Goal:** Transform FinAgent from an evaluation system into a production-ready content publishing platform that can automatically post finance content to Twitter with human approval workflow.

---

## Current Status (Updated: January 23, 2026)

### ✅ Completed
- **Pre-MVP:** 97.56% HITL agreement achieved, all gaps closed
- **Phase 1:** Content Selection & Twitter Generation - COMPLETE
- **Phase 2:** Scheduling System - COMPLETE

### 🚧 In Progress
- **Phase 3:** Twitter Publishing API Integration - NOT STARTED

### ⏭️ Deferred
- **Phase 4:** Public Website - NOT APPLICABLE (using plugin architecture)
- **Phase 5:** Analytics - TODO after Phase 3

---

## MVP Vision

**"From Evaluation to Publication via Platform Plugins"**

The MVP enables:
1. Human editors to evaluate quality (PASS/FAIL) and select which approved content to publish
2. **Platform plugins** transform raw content into platform-specific formats (Twitter: 280 chars, LinkedIn: 700 chars, etc.)
3. Scheduled publishing to **Twitter** (LinkedIn & Newsletter plugins in future)
4. Analytics tracking for Twitter performance
5. Feedback loop for continuous improvement

**Key Architecture:** Each platform gets **standalone content** (no external links). Content is self-contained and optimized per platform.

**Key Workflow:** Quality approval ≠ Publishing decision. Users can PASS 10 items for quality, then select only 3-4 to actually publish.

---

## Selective Publishing Workflow (NEW)

**The Problem User Identified:**

> "There might be scenario that 10 events are there from which I like to post just 3-4, but all are PASS in quality check. Then what?"

**The Solution:**

We're implementing a **two-step workflow** that separates **quality approval** from **publishing decision**:

```
Step 1: Quality Check (PASS/FAIL)
   ↓
Step 2: User Selection (Choose which PASS items to publish)
   ↓
Step 3: Platform Content Generation (Only for selected items)
   ↓
Step 4: Scheduling & Publishing
```

### Status Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     EVALUATION PHASE                          │
│                                                               │
│  AI generates raw output → Human evaluates → PASS or FAIL    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                  APPROVED QUEUE (Status: "approved")          │
│                                                               │
│  All PASS items wait here for user selection                 │
│  User sees list with checkboxes                              │
└──────────────────────────────────────────────────────────────┘
                              ↓
                   User selects 3-4 out of 10
                              ↓
┌──────────────────────────────────────────────────────────────┐
│            SELECTED FOR PUBLISHING                            │
│         (Status: "selected_for_publishing")                   │
│                                                               │
│  Only these 3-4 items proceed to content generation          │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              PLATFORM CONTENT GENERATION                      │
│              (Status: "generating")                           │
│                                                               │
│  System creates Twitter version (280 chars + hashtags)       │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│            READY TO SCHEDULE                                  │
│         (Status: "ready_to_schedule")                         │
│                                                               │
│  User can now schedule these 3-4 for publishing              │
└──────────────────────────────────────────────────────────────┘
                              ↓
                    User schedules tweets
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                SCHEDULED → PUBLISHED                          │
│                                                               │
│  Worker publishes at scheduled time                          │
└──────────────────────────────────────────────────────────────┘
```

### What Happens to the Other 6-7 Items?

The items that **PASSED quality but were NOT selected** remain in "Approved Queue" with `status = "approved"`. You can:

1. **Select them later** - They stay in Approved Queue indefinitely
2. **Skip them permanently** - Mark as `status = "skipped"` to remove from queue
3. **Archive them** - Keep for reference but don't publish

This gives you **full control** over what gets published, separate from quality approval.

---

## MVP Objectives

### Primary Objectives

1. **Content Approval Workflow** - Enable human-in-the-loop content review, editing, and approval
2. **Platform Plugin System** - Transform raw content into platform-specific formats (Twitter: 280 chars, LinkedIn: 700 chars)
3. **Twitter Publishing** - Automated posting to Twitter with scheduling
4. **Scheduling System** - Queue and schedule content for optimal timing
5. **Analytics Integration** - Track Twitter engagement and performance metrics

### Plugin Architecture (Not Website-Based)

**Key Design:** Each platform receives **standalone, self-contained content**. No external links or website needed.

```
Raw LLM Output (400 words)
         ↓
    [Platform Plugins]
         ↓
    ┌────┴────┬─────────┬──────────┐
    ↓         ↓         ↓          ↓
Twitter   LinkedIn  Newsletter  Instagram
(280)     (700)     (full)      (visual)
```

**Example Twitter Output:**
```
🏦 RBI keeps repo rate steady at 6.5% for 5th time

The central bank's focus remains on controlling inflation,
which has cooled to 5.5%. This means borrowing costs stay
the same for now.

💡 What it means: Your loan EMIs won't change yet.

#RBI #MonetaryPolicy #Finance
```

No link to external website - content is complete and self-contained.

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Content Selection Time | <10 minutes | Time from PASS to Twitter generation completion |
| Twitter Publishing Success Rate | ≥95% | Successful tweets / scheduled tweets |
| Tweet Generation Quality | 100% | All generated tweets ≤280 chars with hashtags |
| Publishing Worker Reliability | ≥99% | Worker uptime over 30 days |
| Analytics Sync Accuracy | 100% | All published tweets have accurate metrics |
| User Control | 100% | Can select any subset of approved content to publish |

---

## MVP Scope

### In Scope (Must Have)

**Phase 1: Content Selection & Platform Generation** ✅ **COMPLETE**
- ✅ Two-step workflow: Quality approval (PASS/FAIL) → Selection for publishing (user chooses which to publish)
- ✅ "Approved Queue" interface showing all PASS items with checkboxes
- ✅ Platform content generation: Convert raw LLM output → Twitter format (280 chars, hashtags)
- ✅ Bulk selection actions (select multiple, generate for selected)
- ✅ Status tracking: approved → selected_for_publishing → generating → ready_to_schedule
- ✅ Content preview: See Twitter version before scheduling
- **Files:** [ApprovedQueue.tsx](dashboard/src/pages/ApprovedQueue.tsx), [GeneratedContent.tsx](dashboard/src/pages/GeneratedContent.tsx), [selection.py](api/routes/selection.py), [content_generator.py](services/content_generator.py)

**Phase 2: Scheduling System** ✅ **COMPLETE**
- ✅ Calendar-based scheduling interface
- ✅ Optimal timing suggestions based on platform best practices
- ✅ Timezone-aware scheduling (IST primary, platform-specific)
- ✅ Content queue management (reorder, reschedule, cancel)
- ✅ Smart scheduler service
- ✅ Error handling and retry logic
- **Files:** [SchedulingCalendar.tsx](dashboard/src/components/SchedulingCalendar.tsx), [scheduling.py](api/routes/scheduling.py), [smart_scheduler.py](services/smart_scheduler.py)

**Phase 3: Twitter Publishing** ❌ **NOT STARTED - NEXT PRIORITY**
- ⏳ Twitter API v2 integration
- ⏳ OAuth 2.0 authentication flow
- ⏳ Tweet posting (280 character limit)
- ⏳ Hashtag optimization based on event type
- ⏳ Publishing worker (checks every minute, posts scheduled tweets)
- ⏳ Error handling and retry logic
- ⏳ Store tweet IDs and URLs for analytics
- **Status:** Can schedule tweets but cannot actually post to Twitter yet
- **Blockers:** Need Twitter API credentials, TwitterPublishingService, PublishedContent table, publishing worker
- 🔜 LinkedIn & Newsletter plugins in future phases

**Phase 4: Public Website** ❌ **NOT APPLICABLE**
- ❌ Removed from MVP scope
- **Reason:** Using plugin architecture with self-contained content per platform
- **No external website needed** - each post is complete and standalone
- May be added in future if needed for SEO/brand presence

**Phase 5: Twitter Analytics Integration** ⏳ **TODO AFTER PHASE 3**
- ⏳ Track Twitter engagement metrics (likes, retweets, replies, impressions) for EVERY published tweet
- ⏳ Dashboard showing which tweets are most liked/preferred
- ⏳ Twitter API v2 analytics integration
- ⏳ Performance comparison: identify best/worst performing tweets
- ⏳ Analyze trends: what event type gets most engagement on Twitter
- ⏳ Export analytics reports for decision-making
- ⏳ Weekly summary emails with top performing tweets
- **Dependency:** Requires Phase 3 to be complete (need published tweets to analyze)
- 🔜 LinkedIn & Newsletter analytics in future phases

**Why Analytics Critical:** Without analytics, we can't understand what content resonates with the audience. This data drives all future content decisions and optimization.

### Out of Scope (MVP)

- ❌ **Public website** (using plugin architecture instead - content is self-contained)
- ❌ LinkedIn publishing (Twitter-only for MVP)
- ❌ Newsletter publishing (Twitter-only for MVP)
- ❌ Subscriptions and monetization
- ❌ B2B partnerships and API access
- ❌ Advanced AI/ML for content optimization
- ❌ A/B testing framework
- ❌ Multi-language support
- ❌ Mobile app
- ❌ Cloud deployment (stays local for MVP)
- ❌ Auto-posting without human approval

---

## Technical Architecture

### Updated System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Public Website (Next.js)                     │
│                    (Content Display, Search, SEO)                    │
└─────────────────────────────────────────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Admin Dashboard (React)                      │
│              (Evaluation, Approval, Scheduling, Analytics)           │
└─────────────────────────────────────────────────────────────────────┘
                              │ WebSocket + REST
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                              │
│         (REST API, WebSocket, Publishing Worker, Analytics)          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Twitter  │  │ LinkedIn │  │SendGrid  │
        │   API    │  │   API    │  │   API    │
        └──────────┘  └──────────┘  └──────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                             │
│    (Events, Outputs, Evaluations, ContentQueue, PublishedContent,   │
│                     Analytics, UserPreferences)                      │
└─────────────────────────────────────────────────────────────────────┘
```

### New Database Tables

#### 1. Content Queue (Enhanced with Selective Publishing)
```python
class ContentQueue(Base):
    __tablename__ = "content_queue"

    # Identifiers
    id = UUID(primary_key=True)
    event_id = UUID(ForeignKey("events.id"))
    output_id = UUID(ForeignKey("outputs.id"))

    # Status Flow: approved → selected_for_publishing → generating → ready_to_schedule → scheduled → published
    status = String  # Status values:
                     # - "approved": Passed quality check, waiting for user selection
                     # - "selected_for_publishing": User chose to publish this
                     # - "skipped": User chose NOT to publish (even though it passed)
                     # - "generating": Creating platform-specific content
                     # - "ready_to_schedule": Platform content ready, can be scheduled
                     # - "scheduled": Scheduled for future publish
                     # - "published": Live on platform
                     # - "rejected": Failed quality check

    # Selection & Approval
    approved_at = DateTime  # When PASS evaluation happened
    selected_at = DateTime  # When user selected this for publishing
    notes = Text  # Optional user notes

    # Scheduling
    scheduled_for = DateTime  # When to publish

    # Publishing
    published_at = DateTime  # When actually published
    platform = String  # "twitter" (linkedin, newsletter in future)

    # Timestamps
    created_at = DateTime
    updated_at = DateTime
```

#### 2. Generated Content (New - Platform-Specific Versions)
```python
class GeneratedContent(Base):
    """Stores platform-specific formatted content (Twitter, LinkedIn, Newsletter)"""
    __tablename__ = "generated_content"

    id = UUID(primary_key=True)
    output_id = UUID(ForeignKey("outputs.id"))  # Link to raw LLM output
    content_queue_id = UUID(ForeignKey("content_queue.id"))  # Link to queue item

    # Platform Info
    platform = String  # "twitter" (linkedin, newsletter in future)

    # Generated Content
    content_text = Text  # Platform-formatted text (e.g., Twitter: 280 chars + hashtags)
    hashtags = ARRAY(String)  # Extracted hashtags
    character_count = Integer  # For validation

    # Metadata
    generated_at = DateTime
    created_at = DateTime
```

#### 3. Published Content (New - Live Platform Posts)
```python
class PublishedContent(Base):
    """Tracks content that's been published to platforms"""
    __tablename__ = "published_content"

    id = UUID(primary_key=True)
    content_queue_id = UUID(ForeignKey("content_queue.id"))
    generated_content_id = UUID(ForeignKey("generated_content.id"))

    # Platform Info
    platform = String  # "twitter"
    platform_post_id = String  # Twitter tweet ID
    platform_url = String  # Direct link to tweet

    # Published Content
    content_text = Text  # Exact text that was published
    published_at = DateTime

    # Engagement Metrics (synced from platform)
    engagement_metrics = JSONB  # {likes, retweets, replies, impressions, etc.}
    last_synced_at = DateTime

    created_at = DateTime
```

#### 4. Twitter Analytics (New - Time-Series Metrics)
```python
class TwitterAnalytics(Base):
    """Time-series analytics data for Twitter posts"""
    __tablename__ = "twitter_analytics"

    id = UUID(primary_key=True)
    published_content_id = UUID(ForeignKey("published_content.id"))

    # Time Tracking
    metric_date = Date  # Date of measurement
    metric_timestamp = DateTime

    # Twitter Metrics (from API v2)
    impressions = Integer  # How many times tweet was seen
    likes = Integer  # Likes/hearts
    retweets = Integer  # Retweets
    replies = Integer  # Replies
    quote_tweets = Integer  # Quote tweets
    bookmarks = Integer  # Bookmarks/saves (if available)

    # Calculated Metrics
    total_engagements = Integer  # likes + retweets + replies + quotes
    engagement_rate = Float  # engagements / impressions

    created_at = DateTime
```

#### 4. User Preferences (New)
```python
class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = UUID(primary_key=True)
    user_id = String  # Editor identifier
    preferred_schedule_times = JSONB  # Optimal posting times
    platform_enabled = JSONB  # Which platforms to auto-post
    notification_settings = JSONB
    created_at = DateTime
    updated_at = DateTime
```

### New Backend Services

#### 1. Content Selection Service (New - Handles Selective Publishing)
```python
# services/selection_service.py

class ContentSelectionService:
    """Manages the selection and curation of approved content"""

    def get_approved_queue(self, limit=50) -> List[Output]:
        """Get all PASS items waiting for selection"""
        # Returns outputs with evaluation.verdict = PASS and no content_queue entry

    def select_for_publishing(self, output_ids: List[UUID], selected_by: str):
        """User selects which approved items to publish"""
        # Creates content_queue entries with status = "selected_for_publishing"
        # Triggers platform content generation

    def skip_content(self, output_ids: List[UUID], reason: str):
        """User chooses NOT to publish approved items"""
        # Creates content_queue entries with status = "skipped"

    def bulk_select(self, output_ids: List[UUID]):
        """Select multiple items at once"""
```

#### 2. Content Generator Service (New - Creates Platform-Specific Content)
```python
# services/content_generator.py

class ContentGeneratorService:
    """Transforms raw LLM output into platform-specific format"""

    def generate_twitter_content(self, output: Output) -> GeneratedContent:
        """
        Convert raw LLM output (200-400 words) → Twitter format (280 chars)

        Steps:
        1. Extract key points from raw output
        2. Condense to 250-260 chars (leave room for hashtags)
        3. Add relevant hashtags based on event type
        4. Validate character count
        5. Store as GeneratedContent record
        """
        pass

    def get_hashtags_for_event_type(self, event_type: str) -> List[str]:
        """
        FINANCE_POLICY → #Finance #RBI #Policy
        MARKET_MOVEMENT → #Markets #Stocks #Trading
        MACRO_ECONOMIC → #Economy #GDP #Inflation
        GEO_FINANCIAL → #Trade #GlobalMarkets
        """
        pass

    def validate_twitter_format(self, content: str) -> tuple[bool, List[str]]:
        """Ensure content meets Twitter requirements"""
        # Check character count <= 280
        # Check no forbidden phrases
        # Return (is_valid, errors)
```

#### 3. Approval Service (Updated)
```python
# services/approval_service.py

class ApprovalService:
    """Handles evaluation PASS/FAIL - simplified for single user"""

    def mark_as_pass(self, output_id: UUID):
        """Evaluation marks output as PASS (quality approved)"""
        # Updates evaluation.verdict = PASS
        # Output now appears in "Approved Queue"

    def mark_as_fail(self, output_id: UUID, reason: str):
        """Evaluation marks output as FAIL (quality rejected)"""
        # Updates evaluation.verdict = FAIL
        # Content won't appear in Approved Queue

    def get_approved_queue(self):
        """Get all PASS items not yet selected/skipped"""
        # Returns outputs ready for user selection
```

#### 4. Scheduling Service (Twitter Only)
```python
# services/scheduling_service.py

class SchedulingService:
    """Manages scheduled tweet publishing"""

    def schedule_tweet(self, content_queue_id: UUID, scheduled_time: datetime):
        """Schedule a tweet for future publishing"""
        # Update content_queue.scheduled_for
        # Update status = "scheduled"

    def suggest_optimal_time_twitter(self, event_type: str) -> datetime:
        """Suggest best time to tweet based on event type"""
        # Peak times: 8-10 AM, 12-1 PM, 5-6 PM IST
        # Avoid late night (11 PM - 6 AM)

    def get_scheduled_tweets(self, start_date: date, end_date: date):
        """Get all scheduled tweets in date range"""

    def reschedule_tweet(self, content_queue_id: UUID, new_time: datetime):
        """Change scheduled time"""

    def cancel_scheduled(self, content_queue_id: UUID):
        """Cancel scheduled tweet"""
```

#### 5. Twitter Publishing Service
```python
# services/twitter_publishing.py

class TwitterPublishingService:
    """Publishes tweets to Twitter via API v2"""

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        """Initialize Twitter API client"""

    def publish_tweet(self, content_queue_id: UUID) -> dict:
        """
        Publish a tweet immediately

        Steps:
        1. Get generated_content for this queue item
        2. Post to Twitter API v2: POST /2/tweets
        3. Store tweet ID and URL in published_content
        4. Update content_queue.status = "published"
        5. Return success/failure
        """

    def handle_rate_limits(self):
        """Twitter free tier: 50 tweets/24 hours"""
        # Check if approaching limit
        # Wait if needed

    def retry_failed_tweet(self, content_queue_id: UUID):
        """Retry failed tweet publish"""
```

#### 6. Twitter Analytics Service
```python
# services/twitter_analytics.py

class TwitterAnalyticsService:
    """Fetches engagement metrics from Twitter API"""

    def sync_tweet_metrics(self, published_content_id: UUID):
        """
        Fetch latest metrics for a tweet

        Twitter API v2: GET /2/tweets/{id}?tweet.fields=public_metrics
        Returns: impression_count, like_count, retweet_count, reply_count, quote_count
        """

    def calculate_engagement_rate(self, published_content_id: UUID) -> float:
        """engagement_rate = total_engagements / impressions"""

    def get_top_performers(self, limit: int = 10) -> List[PublishedContent]:
        """Get tweets with highest engagement rate"""

    def get_bottom_performers(self, limit: int = 10) -> List[PublishedContent]:
        """Get tweets with lowest engagement rate"""

    def get_performance_by_event_type(self) -> dict:
        """Compare engagement across event types"""
        # Returns: {"FINANCE_POLICY": 0.045, "MARKET_MOVEMENT": 0.023, ...}

    def generate_performance_report(self, start_date: date, end_date: date):
        """Generate analytics report for date range"""
```

#### 7. Twitter Publishing Worker
```python
# workers/twitter_publishing_worker.py

class TwitterPublishingWorker:
    """Background worker that publishes scheduled tweets"""

    def run(self):
        """
        Runs every minute:
        1. Find content_queue items with status="scheduled" and scheduled_for <= now + 5 minutes
        2. For each item:
           - Get generated_content (Twitter version)
           - Call TwitterPublishingService.publish_tweet()
           - Update status to "published"
           - Create published_content record with tweet ID/URL
        3. Handle errors:
           - Retry up to 3 times with exponential backoff
           - If all retries fail, mark as "failed" and alert admin
        4. Log all operations
        """

    def check_health(self):
        """Health check endpoint for monitoring"""
```

#### 8. Twitter Analytics Worker
```python
# workers/twitter_analytics_worker.py

class TwitterAnalyticsWorker:
    """Background worker that syncs tweet metrics"""

    def run(self):
        """
        Runs every hour:
        1. Find published_content with platform="twitter" published in last 7 days
        2. For each tweet:
           - Fetch latest metrics from Twitter API
           - Update twitter_analytics table (new record for time-series)
           - Update engagement_metrics JSONB in published_content
        3. Calculate engagement rates
        4. Store timestamp of sync
        """

    def generate_daily_summary(self):
        """Run at 9 AM daily - generate summary report"""
```

---

## Phase-by-Phase Implementation Plan

### Phase 1: Content Selection & Twitter Content Generation (Week 1-2)

**Key Innovation:** Separate **quality approval** (PASS/FAIL) from **publishing decision** (select which to publish).

**Scenario:** 10 events PASS quality check → User selects only 3-4 to publish → System generates Twitter versions for those 3-4.

---

#### Backend Tasks

1. **Create GeneratedContent Table**
   - Store platform-specific content versions (Twitter format)
   - Link to original output (raw LLM explanation)
   - Track character count, hashtags, formatting

2. **Enhance ContentQueue Table**
   - Add new status flow: `approved` → `selected_for_publishing` → `generating` → `ready_to_schedule`
   - Add `selected_at` timestamp
   - Add `skipped` status for approved-but-not-published items

3. **Build Content Selection API Endpoints**
   ```
   GET    /api/selection/approved-queue          # Get all PASS items not yet selected
   POST   /api/selection/select-for-publishing   # User selects items to publish
   POST   /api/selection/skip                    # User skips approved items
   GET    /api/selection/selected                # Get selected items pending generation
   ```

4. **Build Twitter Content Generation API Endpoints**
   ```
   POST   /api/generation/generate-twitter/{output_id}  # Generate Twitter version
   POST   /api/generation/bulk-generate                 # Generate for multiple
   GET    /api/generation/preview/{generated_id}        # Preview Twitter version
   POST   /api/generation/regenerate/{generated_id}     # Regenerate if needed
   ```

5. **Implement ContentGeneratorService**
   - `generate_twitter_content(output)` - Transform 200-400 words → 280 chars
   - Extract key points from raw explanation
   - Add hashtags based on event type
   - Validate character count
   - Store as GeneratedContent record

6. **Implement ContentSelectionService**
   - `get_approved_queue()` - Get PASS outputs not yet selected
   - `select_for_publishing(output_ids)` - Mark items as selected
   - `skip_content(output_ids)` - Mark items as skipped
   - Trigger content generation after selection

#### Frontend Tasks

1. **Approved Queue Page (New) - Primary Selection Interface**

   **Layout:**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │ Approved Queue (10 items ready for publishing)              │
   ├─────────────────────────────────────────────────────────────┤
   │ [Select All] [Deselect All]                                 │
   │ 3 of 10 items selected                                      │
   │ [Generate Twitter Content (3)] [Skip Selected (3)]          │
   ├─────────────────────────────────────────────────────────────┤
   │                                                              │
   │ [✓] RBI announces new payment security guidelines           │
   │     FINANCE_POLICY • EXPLANATORY • LOW RISK                 │
   │     "The Reserve Bank of India has issued comprehensive..." │
   │     [View Full] [Preview]                                   │
   │                                                              │
   │ [✓] Fed holds interest rates steady at 5.25-5.50%          │
   │     MACRO_ECONOMIC • DESCRIPTIVE • LOW RISK                 │
   │     "The Federal Reserve kept its benchmark interest..."    │
   │     [View Full] [Preview]                                   │
   │                                                              │
   │ [ ] Sensex closes 200 points higher on IT gains            │
   │     MARKET_MOVEMENT • DESCRIPTIVE • MEDIUM RISK             │
   │     "Indian stock markets ended positive on Monday..."      │
   │     [View Full] [Preview]                                   │
   │                                                              │
   │ [✓] SEBI tightens disclosure norms for mutual funds        │
   │     FINANCE_POLICY • EXPLANATORY • LOW RISK                 │
   │     "SEBI has strengthened disclosure requirements..."      │
   │     [View Full] [Preview]                                   │
   │                                                              │
   │ ... (6 more items)                                          │
   └─────────────────────────────────────────────────────────────┘
   ```

   **Features:**
   - Checkbox next to each approved item
   - Show event metadata (type, intent, risk level)
   - Show first 100 chars of raw explanation
   - "Select All" / "Deselect All" bulk actions
   - Counter showing "X of Y items selected"
   - "Generate Twitter Content (X)" button - only enabled if >0 selected
   - "Skip Selected (X)" button - marks items as skipped
   - "View Full" modal - shows complete raw LLM output
   - "Preview" modal - shows how it will look on Twitter (after generation)

2. **Twitter Content Preview Page (New)**
   - After generation, show Twitter-formatted version
   - Display character count (e.g., "245 / 280")
   - Show hashtags
   - Preview how tweet will appear (Twitter-style card)
   - "Regenerate" button if unhappy with output
   - "Approve for Scheduling" button → moves to scheduling queue

3. **Update Evaluations Page**
   - Add "Add to Approved Queue" button for PASS items
   - Show if item is already in Approved Queue
   - Link to Approved Queue page

#### Exit Criteria Phase 1

- ✅ Approved Queue shows all PASS outputs not yet selected/skipped
- ✅ User can select multiple items with checkboxes
- ✅ "Generate Twitter Content" creates GeneratedContent records for selected items
- ✅ Twitter version is 280 chars or less with relevant hashtags
- ✅ Preview shows Twitter-formatted version accurately
- ✅ "Skip Selected" marks items as skipped (not published)
- ✅ Content generation takes <10 seconds per item
- ✅ WebSocket updates reflect selection/generation changes in real-time
- ✅ Status flow works: approved → selected_for_publishing → generating → ready_to_schedule

---

### Phase 2: Scheduling System (Week 2-3)

#### Backend Tasks

1. **Scheduling API Endpoints**
   ```
   POST   /api/scheduling/schedule
   GET    /api/scheduling/calendar
   PUT    /api/scheduling/reschedule/{content_queue_id}
   DELETE /api/scheduling/cancel/{content_queue_id}
   GET    /api/scheduling/suggest-time
   ```

2. **Implement Scheduling Service**
   - Store scheduled datetime in content queue
   - Calculate optimal times per platform
   - Handle timezone conversions (IST → UTC → Platform local)
   - Prevent scheduling conflicts

3. **Platform-Specific Timing Logic**
   - Twitter: Peak times 8-10 AM, 12-1 PM, 5-6 PM IST
   - LinkedIn: Business hours 9 AM - 5 PM IST, Tue-Thu preferred
   - Newsletter: Weekday mornings 8 AM IST

#### Frontend Tasks

1. **Scheduling Interface**
   - Calendar view showing scheduled content
   - Drag-and-drop to reschedule
   - "Schedule Now" quick action
   - "Schedule for optimal time" smart button
   - Timezone selector (default IST)

2. **Schedule Preview**
   - Show what will post at what time
   - Color-code by platform
   - Show content preview on hover
   - Alert for conflicts (multiple posts same time)

3. **Bulk Scheduling**
   - Select multiple approved items
   - Auto-distribute across optimal times
   - Respect platform rate limits

#### Exit Criteria Phase 2

- ✅ Content can be scheduled for future datetime
- ✅ Calendar view displays scheduled content
- ✅ Optimal time suggestions work for each platform
- ✅ Rescheduling and cancellation work correctly
- ✅ Timezone handling is accurate

---

### Phase 3: Twitter Publishing (Week 3-4)

**Goal:** Publish scheduled tweets to Twitter automatically via background worker.

---

#### Backend Tasks

1. **Twitter API v2 Integration**

   **Authentication:**
   - OAuth 2.0 flow for user authentication
   - Store access tokens securely (encrypted in database)
   - Auto-refresh tokens when expired

   **Publishing Endpoint:**
   - POST /2/tweets
   - Request body: `{"text": "tweet content here"}`
   - Response: tweet ID, creation time, author ID

   **Rate Limits:**
   - Free tier: 50 tweets / 24 hours
   - Standard tier: 3000 tweets / 24 hours ($100/month)
   - Handle rate limit errors gracefully

2. **Twitter Publishing API Endpoints**
   ```
   POST   /api/twitter/publish-now/{content_queue_id}    # Publish immediately
   POST   /api/twitter/publish-scheduled                 # Called by worker
   GET    /api/twitter/status/{content_queue_id}         # Check publish status
   POST   /api/twitter/retry/{content_queue_id}          # Retry failed tweet
   GET    /api/twitter/test-connection                   # Test Twitter auth
   ```

3. **Implement TwitterPublishingService**
   ```python
   class TwitterPublishingService:
       def publish_tweet(self, content_queue_id: UUID):
           """
           1. Get generated_content (Twitter version)
           2. POST to Twitter API: /2/tweets
           3. Store tweet ID and URL in published_content
           4. Update content_queue.status = "published"
           5. Return {success: True, tweet_id, tweet_url}
           """

       def handle_rate_limit(self):
           """Check if approaching 50 tweets/day limit"""

       def retry_with_backoff(self, content_queue_id):
           """Exponential backoff: 1s, 2s, 4s, 8s"""
   ```

4. **Create TwitterPublishingWorker**
   ```python
   class TwitterPublishingWorker:
       """Runs every minute as background process"""

       def run(self):
           # 1. Find content_queue with status="scheduled" and scheduled_for <= now + 5 min
           # 2. For each item:
           #    - Call TwitterPublishingService.publish_tweet()
           #    - Update status to "published"
           #    - Create published_content record
           # 3. Handle errors (retry up to 3 times)
           # 4. Send WebSocket notification on success/failure

       def check_health(self):
           """Health check for monitoring"""
   ```

5. **Error Handling & Retry Logic**
   - **Rate limit error (429):** Wait until reset time, then retry
   - **Auth error (401):** Refresh token, retry
   - **Server error (500):** Exponential backoff, retry 3 times
   - **Client error (400):** Log error, mark as failed (don't retry)
   - All errors logged to database and sent to admin

6. **Store Tweet Data**
   - Create `PublishedContent` record with:
     - `platform_post_id`: Twitter tweet ID
     - `platform_url`: https://twitter.com/user/status/{tweet_id}
     - `content_text`: Exact text that was tweeted
     - `published_at`: Timestamp
   - Update `content_queue.status` to "published"
   - Update `content_queue.published_at`

#### Frontend Tasks

1. **Twitter Authentication Page**
   - "Connect Twitter Account" button
   - OAuth 2.0 flow (redirect to Twitter, callback)
   - Display connected account info (username, profile pic)
   - "Test Connection" button
   - "Disconnect" option

2. **Publishing Status Dashboard (New)**

   **Layout:**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │ Published Content (23 tweets)                               │
   ├─────────────────────────────────────────────────────────────┤
   │ Filter: [All] [Last 7 Days] [Last 30 Days]                 │
   │ Sort: [Newest] [Oldest] [Most Engaged]                     │
   ├─────────────────────────────────────────────────────────────┤
   │                                                              │
   │ 🐦 RBI announces new payment security guidelines            │
   │     Published: Jan 21, 2026 10:15 AM IST                   │
   │     Likes: 45 | Retweets: 12 | Replies: 8                  │
   │     [View on Twitter ↗] [View Analytics]                   │
   │                                                              │
   │ 🐦 Fed holds interest rates steady at 5.25-5.50%           │
   │     Published: Jan 21, 2026 8:30 AM IST                    │
   │     Likes: 78 | Retweets: 23 | Replies: 15                 │
   │     [View on Twitter ↗] [View Analytics]                   │
   │                                                              │
   │ ... (more tweets)                                           │
   └─────────────────────────────────────────────────────────────┘
   ```

   **Features:**
   - List all published tweets
   - Show engagement metrics (likes, retweets, replies)
   - Link to view tweet on Twitter (opens in new tab)
   - Filter by date range
   - Sort by newest, oldest, or most engaged

3. **Publishing Error Handling UI**
   - Show failed tweets with error reason
   - "Retry" button for failed tweets
   - Display rate limit status (e.g., "42 / 50 tweets used today")
   - Alert if approaching daily limit

4. **Real-time Publishing Notifications**
   - WebSocket notification when tweet publishes successfully
   - Show toast: "✅ Tweet published successfully - View on Twitter"
   - Show error toast if publish fails: "❌ Tweet failed to publish - Retry"

#### Exit Criteria Phase 3

- ✅ Twitter OAuth 2.0 authentication works
- ✅ Tweets publish successfully to Twitter
- ✅ Tweet IDs and URLs stored in database
- ✅ Publishing worker runs every minute without errors
- ✅ Worker reliability ≥99% uptime (24-hour test)
- ✅ Rate limits handled correctly (no 429 errors unhandled)
- ✅ Error handling works (3 retries with exponential backoff)
- ✅ Failed tweets can be retried manually
- ✅ Publishing Status Dashboard displays accurate data
- ✅ "View on Twitter" links work correctly
- ✅ Real-time WebSocket notifications work

---

### Phase 4: Public Website (Week 4-5)

#### Tech Stack for Website

- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **Deployment:** Local (Nginx reverse proxy)
- **Domain:** TBD (e.g., finagent.com)

#### Website Structure

```
/                    # Homepage with latest content
/about               # About FinAgent, philosophy, team
/content             # All published content (paginated)
/content/[id]        # Individual content page
/search              # Search and filter interface
/rss                 # RSS feed
/api/*               # API endpoints (same FastAPI backend)
```

#### Backend Tasks

1. **Public API Endpoints**
   ```
   GET    /api/public/content/latest
   GET    /api/public/content/{id}
   GET    /api/public/content/search
   GET    /api/public/content/by-type/{event_type}
   GET    /api/public/content/by-source/{source}
   GET    /api/public/rss
   ```

2. **SEO Optimization**
   - Generate meta tags for each content page
   - Create sitemap.xml
   - Add structured data (JSON-LD)
   - OpenGraph tags for social sharing

#### Frontend Tasks (Next.js)

1. **Homepage**
   - Hero section with value proposition
   - Latest published content (5-10 items)
   - Event type categories
   - Source highlights
   - Newsletter signup form

2. **Content List Page**
   - Paginated list of published content
   - Filter by event type, source, date range
   - Search functionality
   - Sort options (newest, most engaged)

3. **Content Detail Page**
   - Full content display
   - Event metadata (source, date, type)
   - Link to original article
   - Social share buttons
   - Related content suggestions

4. **About Page**
   - Mission and vision
   - Content philosophy (from CLAUDE.md)
   - How it works (system overview)
   - Why trust FinAgent
   - Contact information

5. **Responsive Design**
   - Mobile-first approach
   - Optimized for all screen sizes
   - Fast loading (< 3 seconds)
   - Accessibility (WCAG AA)

#### Exit Criteria Phase 4

- ✅ Homepage loads and displays latest content
- ✅ Content detail pages render correctly
- ✅ Search and filtering work
- ✅ About page explains FinAgent clearly
- ✅ SEO meta tags present on all pages
- ✅ Mobile responsive design works
- ✅ RSS feed generates correctly
- ✅ Website loads in <3 seconds

---

### Phase 5: Twitter Analytics Integration (Week 5-6) ⚠️ **CRITICAL MVP COMPONENT**

**Goal:** Understand which tweets resonate with the audience. Track every like, retweet, reply, and impression. Answer: "Which posts are most liked/preferred? What content works best?"

---

#### Backend Tasks

1. **Twitter Analytics Collection**

   **Twitter API v2 Metrics Endpoint:**
   ```python
   # GET /2/tweets/{id}?tweet.fields=public_metrics
   #
   # Returns:
   # {
   #   "data": {
   #     "id": "1234567890",
   #     "text": "Tweet content...",
   #     "public_metrics": {
   #       "impression_count": 1523,     # How many times tweet was seen
   #       "like_count": 45,             # Direct engagement
   #       "retweet_count": 12,          # Virality signal
   #       "reply_count": 8,             # Deep engagement
   #       "quote_count": 3,             # Quote tweets
   #       "bookmark_count": 7           # Saves (if available)
   #     }
   #   }
   # }
   ```

   **Critical Metrics:**
   - **Impressions:** Reach (how many people saw it)
   - **Likes:** Direct engagement indicator
   - **Retweets:** Virality signal (content is share-worthy)
   - **Replies:** Deep engagement (content sparked discussion)
   - **Quote Tweets:** High-value engagement (people adding their take)
   - **Engagement Rate:** (likes + retweets + replies + quotes) / impressions

2. **Twitter Analytics API Endpoints**
   ```
   POST   /api/twitter/analytics/sync/{published_content_id}   # Sync metrics for one tweet
   POST   /api/twitter/analytics/sync-all                      # Sync all tweets (last 7 days)
   GET    /api/twitter/analytics/summary                       # Overall Twitter performance
   GET    /api/twitter/analytics/top-performers                # Top 10 most engaged tweets
   GET    /api/twitter/analytics/bottom-performers             # Bottom 10 least engaged tweets
   GET    /api/twitter/analytics/by-event-type                 # Which topics get most engagement
   GET    /api/twitter/analytics/by-tweet/{published_content_id} # Detailed metrics for single tweet
   GET    /api/twitter/analytics/by-date-range                 # Performance over time (7/30/90 days)
   GET    /api/twitter/analytics/trends                        # Engagement trends (growing/declining)
   GET    /api/twitter/analytics/comparison                    # Compare multiple tweets side-by-side
   POST   /api/twitter/analytics/export                        # Export to CSV/PDF
   ```

3. **Implement TwitterAnalyticsService**
   ```python
   class TwitterAnalyticsService:
       def sync_tweet_metrics(self, published_content_id: UUID):
           """
           1. Get tweet ID from published_content
           2. Call Twitter API: GET /2/tweets/{id}?tweet.fields=public_metrics
           3. Parse response
           4. Create twitter_analytics record (time-series)
           5. Update published_content.engagement_metrics JSONB
           6. Calculate engagement_rate = total_engagements / impressions
           7. Update last_synced_at timestamp
           """

       def get_top_performers(self, limit: int = 10):
           """Get tweets with highest engagement rate"""
           # Query twitter_analytics, order by engagement_rate DESC
           # Returns: List[{tweet, metrics, engagement_rate}]

       def get_bottom_performers(self, limit: int = 10):
           """Get tweets with lowest engagement rate"""
           # Query twitter_analytics, order by engagement_rate ASC
           # Returns: List[{tweet, metrics, engagement_rate}]

       def get_performance_by_event_type(self):
           """
           Answer: "Which event types get most engagement on Twitter?"

           Example response:
           {
               "FINANCE_POLICY": {"avg_engagement_rate": 0.045, "tweet_count": 15},
               "MACRO_ECONOMIC": {"avg_engagement_rate": 0.032, "tweet_count": 8},
               "MARKET_MOVEMENT": {"avg_engagement_rate": 0.023, "tweet_count": 12}
           }
           """

       def get_engagement_trends(self, days: int = 30):
           """
           Answer: "Is engagement growing or declining?"

           Returns daily engagement rate for last N days
           """

       def generate_performance_report(self, start_date, end_date):
           """Generate comprehensive analytics report"""
           # Total tweets published
           # Average engagement rate
           # Top 5 performers
           # Bottom 5 performers
           # Best performing event type
           # Engagement trend
   ```

4. **TwitterAnalyticsWorker**
   ```python
   class TwitterAnalyticsWorker:
       """Runs every hour, syncs tweet metrics"""

       def run(self):
           """
           1. Find published_content with platform="twitter" published in last 7 days
           2. For each tweet:
              - Fetch latest metrics from Twitter API
              - Create new twitter_analytics record (time-series)
              - Update engagement_metrics in published_content
           3. Calculate engagement rates
           4. Store sync timestamp
           5. Log any API errors
           """

       def generate_daily_summary(self):
           """
           Runs at 9 AM IST daily

           Creates summary report:
           - Yesterday's tweets (count, avg engagement)
           - Top 3 performers from yesterday
           - Week-over-week engagement comparison
           - Best performing event type this week
           """

       def send_weekly_digest(self):
           """
           Runs Monday 9 AM IST

           Email digest with:
           - Last 7 days summary
           - Top 10 performers
           - Engagement trends
           - Recommendations (e.g., "Policy tweets getting 2x engagement")
           """
   ```

#### Frontend Tasks

1. **Twitter Analytics Dashboard Page (New)** - Primary View for Understanding Tweet Performance

   **Layout:**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │ Twitter Analytics                                            │
   ├─────────────────────────────────────────────────────────────┤
   │ Overview (Last 30 Days)                                     │
   │                                                              │
   │ Total Tweets: 23        Total Impressions: 45,234          │
   │ Avg Engagement Rate: 3.2%    Total Likes: 892              │
   │ Total Retweets: 234     Total Replies: 145                 │
   │                                                              │
   │ 📈 Engagement Trend: +15% vs previous 30 days              │
   ├─────────────────────────────────────────────────────────────┤
   │ ⭐ Top Performers (Most Engaged Tweets)                     │
   │                                                              │
   │ 1. 🔥 RBI keeps repo rate at 6.5% for 5th time             │
   │    Likes: 78 | RT: 23 | Replies: 15 | ER: 7.6%            │
   │    MACRO_ECONOMIC • Published: Jan 20, 8:30 AM             │
   │    [View Tweet ↗] [View Details]                           │
   │                                                              │
   │ 2. ⭐ SEBI tightens disclosure norms for mutual funds       │
   │    Likes: 65 | RT: 18 | Replies: 12 | ER: 6.2%            │
   │    FINANCE_POLICY • Published: Jan 19, 10:15 AM            │
   │    [View Tweet ↗] [View Details]                           │
   │                                                              │
   │ ... (8 more)                                                │
   │                                                              │
   │ [Show All Top Performers]                                   │
   ├─────────────────────────────────────────────────────────────┤
   │ 📉 Bottom Performers (Learn from Low Engagement)            │
   │                                                              │
   │ 1. Sensex closes 150 points higher                         │
   │    Likes: 8 | RT: 2 | Replies: 1 | ER: 1.1%               │
   │    MARKET_MOVEMENT • Published: Jan 21, 5:00 PM            │
   │    [View Tweet ↗] [Analyze]                                │
   │                                                              │
   │ ... (9 more)                                                │
   ├─────────────────────────────────────────────────────────────┤
   │ 📊 Performance by Event Type                                │
   │                                                              │
   │ FINANCE_POLICY    ████████████ 4.5% (15 tweets)           │
   │ MACRO_ECONOMIC    ████████ 3.2% (8 tweets)                │
   │ MARKET_MOVEMENT   █████ 2.3% (12 tweets)                  │
   │ GEO_FINANCIAL     ███████ 2.8% (5 tweets)                 │
   │                                                              │
   │ 💡 Insight: Policy explanations get 2x more engagement     │
   ├─────────────────────────────────────────────────────────────┤
   │ 📈 Engagement Trend (Last 30 Days)                          │
   │                                                              │
   │   [Line chart showing daily engagement rate]                │
   │                                                              │
   │ 📅 Best Days: Tue, Wed, Thu                                │
   │ 🕐 Best Times: 8-10 AM IST, 12-1 PM IST                   │
   ├─────────────────────────────────────────────────────────────┤
   │ [Export to CSV] [Export to PDF] [Schedule Report]          │
   └─────────────────────────────────────────────────────────────┘
   ```

   **Features:**
   - **Overview Section:**
     - Total tweets published (last 30 days)
     - Total impressions, likes, retweets, replies
     - Average engagement rate
     - Trend indicator (↑ increasing, ↓ decreasing)

   - **Top Performers Section:** ⭐ **MOST IMPORTANT**
     - Show top 10 tweets by engagement rate
     - Display: Title, metrics (likes, RTs, replies), engagement rate %
     - Visual indicators: 🔥 for viral (>5% ER), ⭐ for high (>3% ER)
     - Link to view tweet on Twitter
     - "View Details" for drill-down

   - **Bottom Performers Section:** 📉
     - Show bottom 10 tweets by engagement rate
     - Identify patterns in low-performing content
     - Help learn what doesn't work

   - **Performance by Event Type:**
     - Horizontal bar chart showing avg engagement rate per event type
     - Show tweet count for each type
     - Actionable insights: "Policy tweets perform best - focus here"

   - **Engagement Trend Chart:**
     - Line chart: daily engagement rate over last 30 days
     - Identify best days of week and times to post
     - Spot viral moments (spikes in engagement)

2. **Single Tweet Analytics Page (Drill-down)**

   **Layout:**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │ Tweet Analytics: RBI keeps repo rate at 6.5% for 5th time   │
   ├─────────────────────────────────────────────────────────────┤
   │ Tweet Preview:                                              │
   │ "🏦 RBI keeps repo rate steady at 6.5% for 5th time       │
   │                                                              │
   │ The central bank's focus remains on controlling inflation,  │
   │ which has cooled to 5.5%. This means borrowing costs stay   │
   │ the same for now.                                           │
   │                                                              │
   │ 💡 What it means: Your loan EMIs won't change yet.         │
   │                                                              │
   │ #RBI #MonetaryPolicy #Finance"                             │
   │                                                              │
   │ [View on Twitter ↗]                                         │
   ├─────────────────────────────────────────────────────────────┤
   │ Metrics (as of Jan 21, 2026 6:00 PM IST)                   │
   │                                                              │
   │ Impressions: 1,523     Engagement Rate: 7.6%               │
   │ Likes: 78              Retweets: 23                        │
   │ Replies: 15            Quote Tweets: 3                     │
   │ Bookmarks: 7                                               │
   │                                                              │
   │ Total Engagements: 126                                     │
   ├─────────────────────────────────────────────────────────────┤
   │ Performance Comparison                                      │
   │                                                              │
   │ This tweet: 7.6% ER                                        │
   │ Your average: 3.2% ER                                      │
   │ Performance: 🔥 2.4x better than average                   │
   │                                                              │
   │ Event Type Avg (MACRO_ECONOMIC): 3.2% ER                  │
   │ Performance: 2.4x better than similar content              │
   ├─────────────────────────────────────────────────────────────┤
   │ Engagement Timeline                                         │
   │                                                              │
   │ [Line chart showing how metrics grew over time]            │
   │                                                              │
   │ Peak engagement: Jan 20, 9-11 AM (2 hours after publish)   │
   ├─────────────────────────────────────────────────────────────┤
   │ 💡 Insights & Recommendations                               │
   │                                                              │
   │ ✅ Posted at optimal time (8:30 AM IST)                    │
   │ ✅ MACRO_ECONOMIC content performs well                    │
   │ ✅ Morning posts get 2x more engagement                    │
   │                                                              │
   │ 💡 Recommendation: Post more policy/macro content at       │
   │    8-10 AM IST                                             │
   └─────────────────────────────────────────────────────────────┘
   ```

3. **Export & Reporting**
   - **Export to CSV:**
     - All tweets with full metrics
     - Columns: date, title, event_type, impressions, likes, RTs, replies, ER
     - Date range filter (7/30/90 days, custom)

   - **Export to PDF:**
     - Formatted report with charts
     - Overview summary
     - Top 10 performers table
     - Performance by event type chart
     - Trends chart
     - Insights and recommendations

   - **Scheduled Reports:**
     - Weekly email digest (Monday 9 AM IST)
     - Monthly performance report (1st of month)
     - Custom schedule (daily/weekly/monthly)

#### Exit Criteria Phase 5 ⚠️ **MUST PASS TO COMPLETE MVP**

- ✅ Analytics sync from Twitter API works (hourly worker)
- ✅ Dashboard displays accurate metrics (manually verified against Twitter data)
- ✅ **Top Performers section shows 10 most engaged tweets** ⭐
- ✅ **Bottom Performers section shows 10 least engaged tweets** 📉
- ✅ **Can answer: "Which event type gets most engagement on Twitter?"** (e.g., Policy vs Market)
- ✅ **Can answer: "Is Twitter engagement growing or declining?"** (trend analysis)
- ✅ **Can answer: "Which tweets are most liked/preferred?"** (top performers list)
- ✅ **Can answer: "What time is best to tweet?"** (engagement by time analysis)
- ✅ Performance comparison charts render correctly
- ✅ Export to CSV works with all metrics
- ✅ Export to PDF generates formatted report with charts
- ✅ Weekly summary email sends Monday 9 AM IST with top performers
- ✅ Analytics worker runs every hour without errors
- ✅ All published tweets have metrics synced (100% coverage)
- ✅ Single tweet analytics page shows detailed metrics and insights
- ✅ Engagement rate calculated correctly: (likes + RTs + replies + quotes) / impressions
- ✅ Performance comparison shows "X better than average" correctly

**Success Validation:** Editor can look at dashboard and immediately identify:
1. **Which 3 tweets performed best this week** ⭐
2. **What type of content gets most engagement** (event type analysis)
3. **Whether overall engagement is improving or declining** (trend chart)
4. **Best time to post on Twitter** (based on historical engagement data)
5. **Which topics to focus on** (actionable insights)

---

## Implementation Status Summary

### ✅ What's Working (Phases 1-2 Complete)

**Content Selection & Generation:**
- ✅ Approved Queue page showing all PASS items
- ✅ User can select which approved items to publish
- ✅ Twitter content generator (280 chars + hashtags)
- ✅ Bulk selection actions
- ✅ Status tracking workflow
- ✅ Content preview before scheduling

**Scheduling System:**
- ✅ Calendar interface for scheduling
- ✅ Optimal time suggestions
- ✅ IST timezone support
- ✅ Content queue management
- ✅ Smart scheduler service

### ❌ What's Missing (Phase 3 Required)

**Twitter Publishing:**
- ❌ Twitter API v2 integration
- ❌ OAuth authentication
- ❌ Actual tweet posting
- ❌ Publishing worker
- ❌ PublishedContent database table
- ❌ Error handling & retries

**Analytics:**
- ❌ Tweet performance tracking
- ❌ Engagement metrics collection
- ❌ Analytics dashboard

### 🎯 Current Blocker

**Cannot publish to Twitter.** The system can:
- Generate tweet content ✅
- Schedule when to post ✅
- But CANNOT actually post to Twitter ❌

**Next Step:** Implement Phase 3 (Twitter API integration)

---

## MVP Exit Criteria

### Functional Requirements

| Requirement | Status |
|-------------|--------|
| **Approval Workflow** | |
| Editors can approve/reject content | ✅ Complete (Pre-MVP) |
| Editors can edit content before publishing | ✅ Complete (Pre-MVP Gap 4) |
| Bulk selection works | ✅ Complete (Phase 1) |
| **Content Selection** | |
| Select which approved items to publish | ✅ Complete (Phase 1) |
| Generate Twitter content for selected | ✅ Complete (Phase 1) |
| Preview Twitter content | ✅ Complete (Phase 1) |
| **Scheduling** | |
| Content can be scheduled for future datetime | ✅ Complete (Phase 2) |
| Calendar view shows scheduled content | ✅ Complete (Phase 2) |
| Optimal time suggestions work | ✅ Complete (Phase 2) |
| **Publishing** | |
| Publishes successfully to Twitter | ❌ TODO (Phase 3) |
| Publishing worker runs reliably | ❌ TODO (Phase 3) |
| **Analytics** | |
| Metrics sync from Twitter | ❌ TODO (Phase 5) |
| Dashboard displays accurate data | ❌ TODO (Phase 5) |
| Export functionality works | ❌ TODO (Phase 5) |

### Performance Requirements

| Metric | Target | Status |
|--------|--------|--------|
| Publishing Success Rate | ≥95% | ⏳ Pending (Phase 3) |
| API Response Time | <500ms (p95) | ✅ Meeting (verified) |
| Worker Reliability | ≥99% uptime | ⏳ Pending (Phase 3) |
| Analytics Sync Accuracy | 100% | ⏳ Pending (Phase 5) |
| Tweet Generation Time | <10 seconds | ✅ Meeting (Phase 1) |

### Quality Requirements

| Requirement | Target | Status |
|-------------|--------|--------|
| Test Coverage | ≥80% | ⏳ Pending |
| Zero Critical Bugs | 0 | ⏳ Pending |
| Documentation Complete | 100% | ⏳ Pending |
| User Acceptance Testing | 100% pass | ⏳ Pending |

---

## Risk Management

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Platform API Changes** | High | Version lock APIs, monitor for deprecation notices |
| **Rate Limiting** | Medium | Implement queue system, respect limits, upgrade plans if needed |
| **Authentication Failures** | High | Automatic token refresh, fallback mechanisms, admin alerts |
| **Publishing Worker Crashes** | High | Health check monitoring, automatic restart, error logging |
| **Database Performance** | Medium | Indexing, query optimization, connection pooling |

### Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Content Approval Bottleneck** | Medium | Bulk approval, optimal time suggestions, streamlined UI |
| **Platform Policy Violations** | High | Content review checklist, platform guidelines enforcement |
| **Website Downtime** | Medium | Nginx monitoring, automatic restart, uptime alerts |
| **Data Loss** | High | Daily backups, database replication, transaction logging |

### Content Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Advice Language Slips Through** | Critical | Pre-publishing validation, human final review |
| **Factual Errors** | High | Human editorial review, source verification |
| **Brand Reputation** | High | Strict content guidelines, approval workflow, retraction policy |

---

## Resource Requirements

### Development Team

| Role | Responsibility | Time Commitment |
|------|----------------|-----------------|
| **Full-Stack Developer** | All phases | 40 hours/week |
| **Frontend Developer** (Optional) | Website (Phase 4) | 20 hours/week for 2 weeks |
| **DevOps Engineer** (Optional) | Worker setup, monitoring | 10 hours/week |

### Infrastructure

| Component | Requirement | Cost (Estimated) |
|-----------|-------------|------------------|
| **PostgreSQL** | Existing (local) | $0 |
| **Nginx** | New (reverse proxy) | $0 |
| **Domain Name** | New (e.g., finagent.com) | $10-15/year |
| **SSL Certificate** | Let's Encrypt | $0 |
| **Twitter API** | Free tier (50 tweets/day) | $0 (upgrade to $100/mo for 3000 tweets/day if needed) |
| **LinkedIn API** | Free (standard rate limits) | $0 |
| **SendGrid** | Free tier (100 emails/day) | $0 (upgrade to $15/mo for 40k emails if needed) |

### Third-Party Services

1. **Twitter API Access**
   - Apply for API access
   - Get OAuth credentials
   - Review rate limits

2. **LinkedIn API Access**
   - Create LinkedIn App
   - Get OAuth credentials
   - Review API documentation

3. **SendGrid Account**
   - Sign up for free account
   - Get API key
   - Create email template

---

## Testing Strategy

### Unit Tests

- Approval service functions
- Scheduling logic
- Platform formatters
- Analytics calculations
- Publishing worker methods

**Target Coverage:** ≥80%

### Integration Tests

- End-to-end approval workflow
- Scheduling → Publishing flow
- Platform API calls (mocked)
- Analytics sync (mocked)
- Database transactions

**Target:** All critical paths covered

### User Acceptance Tests

1. **Approval Workflow**
   - Can editor approve content?
   - Can editor reject content?
   - Can editor edit content?
   - Does bulk approval work?

2. **Scheduling**
   - Can content be scheduled?
   - Does calendar view work?
   - Do optimal time suggestions work?

3. **Publishing**
   - Does content post to Twitter?
   - Does content post to LinkedIn?
   - Do newsletter emails send?

4. **Website**
   - Does homepage load?
   - Do content pages load?
   - Does search work?
   - Is it mobile responsive?

5. **Analytics**
   - Do metrics sync?
   - Is dashboard accurate?
   - Does export work?

---

## Deployment Plan

### Phase 1-2 Deployment (Backend + Admin Dashboard)

1. Update database schema (migration scripts)
2. Deploy FastAPI backend updates
3. Deploy React dashboard updates
4. Test approval workflow end-to-end

### Phase 3 Deployment (Publishing)

1. Configure platform API credentials
2. Deploy publishing service
3. Start publishing worker process
4. Test publishing to all platforms
5. Monitor for 24 hours

### Phase 4 Deployment (Website)

1. Build Next.js production bundle
2. Configure Nginx reverse proxy
3. Set up SSL certificate (Let's Encrypt)
4. Deploy website
5. Test public access

### Phase 5 Deployment (Analytics)

1. Deploy analytics service
2. Start analytics worker process
3. Backfill analytics for existing published content
4. Test analytics dashboard

### Production Checklist

- [ ] Database migrations run successfully
- [ ] All environment variables configured
- [ ] Platform API credentials tested
- [ ] Workers running and monitored
- [ ] Nginx configured correctly
- [ ] SSL certificate active
- [ ] Domain DNS configured
- [ ] Backup system tested
- [ ] Error monitoring set up
- [ ] Documentation updated

---

## Monitoring & Maintenance

### Monitoring Dashboard

**Key Metrics to Track:**
- Publishing success rate (daily)
- Worker uptime (hourly check)
- API error rates (per endpoint)
- Website uptime (minute-by-minute)
- Platform API rate limit usage
- Database query performance
- Disk space usage

### Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| Publishing failure | >3 failures in 1 hour | Email admin |
| Worker down | Health check fails 3x | Email admin + restart |
| Website down | HTTP 500/502 | Email admin + restart Nginx |
| Database slow | Query >5s | Email admin + investigate |
| Rate limit approaching | >80% of limit | Email admin + pause publishing |

### Maintenance Tasks

**Daily:**
- Review publishing logs
- Check error logs
- Verify worker health
- Monitor analytics sync

**Weekly:**
- Review performance metrics
- Backup database
- Update dependencies (if needed)
- Review content quality

**Monthly:**
- Generate performance report
- Review platform API usage
- Optimize database queries
- Update documentation

---

## Success Criteria for MVP Completion

### Must Meet ALL of the Following:

1. **Approval Workflow**
   - ✅ 100% of PASS evaluations can be approved with one click
   - ✅ Editors can edit content before approval
   - ✅ Approval queue shows all pending items
   - ✅ Bulk approval works for ≥10 items simultaneously

2. **Scheduling**
   - ✅ Content can be scheduled 1-30 days in advance
   - ✅ Calendar view displays all scheduled content
   - ✅ Optimal time suggestions provided for each platform
   - ✅ Rescheduling works without errors

3. **Publishing**
   - ✅ Publishing success rate ≥95% over 30 days
   - ✅ Content posts to Twitter successfully
   - ✅ Content posts to LinkedIn successfully
   - ✅ Newsletter emails send successfully
   - ✅ Worker runs continuously without manual intervention
   - ✅ All published content has platform post IDs stored

4. **Website**
   - ✅ Homepage loads in <3 seconds
   - ✅ All content pages render correctly
   - ✅ Search returns accurate results
   - ✅ Mobile responsive on iOS and Android
   - ✅ SEO meta tags present on all pages
   - ✅ Website uptime ≥99% over 30 days

5. **Analytics**
   - ✅ Metrics sync successfully from all 3 platforms
   - ✅ Dashboard displays accurate data (verified manually)
   - ✅ Export to CSV works
   - ✅ Weekly summary email sends automatically

### Performance Benchmarks

- **API Response Time:** <500ms (95th percentile)
- **Website Load Time:** <3 seconds (95th percentile)
- **Publishing Latency:** Content publishes within 1 minute of scheduled time
- **Analytics Sync Latency:** Metrics updated within 1 hour of publication
- **Worker Reliability:** ≥99% uptime

---

## Post-MVP Plans (Scale Phase)

After MVP completion, the next phase focuses on:

1. **Cloud Deployment**
   - Migrate to AWS/GCP/Azure
   - Implement auto-scaling
   - Set up CI/CD pipeline
   - Add monitoring (DataDog, New Relic)

2. **Content Optimization**
   - A/B testing framework
   - ML-based timing optimization
   - Audience segmentation
   - Personalized content

3. **Monetization**
   - Subscription tiers (Free, Pro, Premium)
   - B2B API access
   - Sponsored content (ethical)
   - Data insights products

4. **Advanced Features**
   - Multi-language support
   - Mobile app (iOS, Android)
   - Video content generation
   - Podcast automation

---

## Appendix

### A. Platform API Documentation

- **Twitter API v2:** https://developer.twitter.com/en/docs/twitter-api
- **LinkedIn Shares API:** https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- **SendGrid API:** https://docs.sendgrid.com/api-reference

### B. Twitter Content Generation Examples

**Example 1: FINANCE_POLICY → Twitter**

**Raw LLM Output (200 words):**
```
The Reserve Bank of India has kept the repo rate unchanged at 6.5% for the fifth
consecutive monetary policy meeting. This decision reflects the central bank's
continued focus on controlling inflation, which has moderated to 5.5% but remains
above the 4% target. The repo rate is the interest rate at which RBI lends to
commercial banks, and changes to this rate directly impact lending rates across
the economy. By maintaining the status quo, RBI is signaling that while inflation
has cooled from earlier highs, it's not ready to cut rates yet. This means
borrowing costs for loans like home loans, car loans, and personal loans will
remain stable for now. Savings account interest rates will also stay unchanged.
The decision balances the need to support economic growth while ensuring inflation
doesn't flare up again. Future rate decisions will depend on inflation trends
and economic indicators over the coming months.
```

**Generated Twitter Content (275 chars):**
```
🏦 RBI keeps repo rate steady at 6.5% for 5th time

The central bank's focus remains on controlling inflation, which has cooled to
5.5%. This means borrowing costs stay the same for now.

💡 What it means: Your loan EMIs won't change yet.

#RBI #MonetaryPolicy #Finance
```

---

**Example 2: MACRO_ECONOMIC → Twitter**

**Raw LLM Output (250 words):**
```
India's retail inflation, measured by the Consumer Price Index (CPI), rose to
5.69% in December, up from 5.48% in November. This uptick was primarily driven
by higher food prices, particularly vegetables and pulses, which saw significant
increases during the month. Food inflation accounts for nearly half of the CPI
basket and has a direct impact on household budgets. The Reserve Bank of India
targets inflation at 4% with a tolerance band of +/- 2%. At 5.69%, inflation
remains within the tolerance band but above the target. This could influence
RBI's future monetary policy decisions. Higher inflation erodes purchasing power,
meaning the same amount of money buys fewer goods and services. For consumers,
this translates to higher grocery bills and living costs. The government and RBI
will monitor these trends closely, especially food inflation, which tends to be
volatile due to seasonal factors and supply chain issues.
```

**Generated Twitter Content (268 chars):**
```
📊 India's retail inflation rises to 5.69% in December

Food prices, especially vegetables, drove the increase. While inflation remains
within RBI's tolerance band (4% ±2%), it's above the 4% target.

💰 Impact: Higher grocery bills for households.

#Inflation #Economy #India
```

---

**Example 3: MARKET_MOVEMENT → Twitter**

**Raw LLM Output (180 words):**
```
India's benchmark stock indices, Sensex and Nifty, closed higher on Monday, with
the Sensex gaining 215 points and Nifty up 63 points. The rally was led by gains
in IT and banking stocks, with investors reacting positively to strong quarterly
earnings from major companies. IT stocks benefited from positive commentary on
US spending trends, while banking stocks saw buying interest ahead of the Q3
earnings season. Broader markets also participated in the rally, with mid-cap and
small-cap indices posting gains. Market analysts note that investor sentiment
remains cautiously optimistic, supported by stable macroeconomic indicators and
expectations of continued earnings growth. However, global cues and oil price
movements remain key factors to watch.
```

**Generated Twitter Content (245 chars):**
```
📈 Sensex closes 215 points higher, led by IT and banking stocks

Strong quarterly earnings and positive US spending trends supported the rally.
Broader markets also gained.

📊 Market sentiment: Cautiously optimistic

#Markets #Sensex #Nifty #Stocks
```

---

### C. Twitter Best Practices

**Character Limits:**
- Maximum: 280 characters
- Best practice: 250-270 characters (leave room for hashtags)
- If longer: Truncate main message to ~250 chars, add link to website for full article

**Hashtags:**
- Use 2-3 relevant hashtags
- Place at end of tweet
- Event type → hashtag mapping:
  - `FINANCE_POLICY` → #Finance #RBI #Policy #SEBI
  - `MACRO_ECONOMIC` → #Economy #GDP #Inflation #India
  - `MARKET_MOVEMENT` → #Markets #Stocks #Sensex #Nifty
  - `GEO_FINANCIAL` → #Trade #GlobalMarkets #Geopolitics

**Emojis:**
- Use 1-2 relevant emojis for visual interest
- 🏦 for central bank/policy
- 📊 for data/statistics
- 📈 for market gains
- 📉 for market declines
- 💰 for money/finance
- 💡 for key insights

**Tone:**
- Clear and concise
- Avoid jargon
- Lead with key insight
- No advice or predictions
- Factual and educational

### D. Optimal Twitter Posting Times (IST)

| Time Slot | Engagement Level | Recommendation |
|-----------|------------------|----------------|
| **8-10 AM** | ⭐ High | Best for policy/macro news |
| **12-1 PM** | ⭐ High | Lunch break browsing |
| **5-6 PM** | ⭐ High | Post-work engagement |
| 11 AM-12 PM | Medium | Acceptable |
| 2-4 PM | Medium | Acceptable |
| 6-11 PM | Low | Avoid if possible |
| 11 PM-6 AM | Very Low | Never post |

**Best Days:** Monday - Friday (avoid weekends unless major news)

**Frequency:** 3-5 tweets/day maximum (avoid overwhelming followers)

---

### E. Data Retention Policy

**Critical Decision:** Data retention strategy impacts analytics, learning, and compliance.

---

#### Recommended Policy

**For Pre-MVP/MVP (Current - Next 6 Months):**

```python
# Keep ALL data, no deletion
retention_days = None  # Unlimited
```

**Why Keep Everything During MVP:**
- Need historical data for Phase 5 Analytics (30/90 day trends)
- HITL automation requires learning from past decisions (need 100+ evaluations)
- Pattern recognition needs sufficient data (200+ posts for Phase 3 automation)
- Audit trail for any content complaints or legal issues
- Storage cost is minimal (<$5/month for 1000s of events)

**After MVP (6+ Months):**

```python
# Selective retention based on data type
RETENTION_POLICY = {
    "events": 90,              # Need for pattern learning
    "outputs": 90,             # Need for similarity comparison
    "evaluations": 90,         # Need for HITL training
    "published_content": None, # Forever (audit + analytics)
    "analytics": None,         # Forever (trend analysis)
    "content_queue": 30,       # Unpublished items only
}
```

**Rationale for Post-MVP Policy:**
- **90 days for learning data**: Sufficient for HITL pattern recognition and auto-approval training
- **Forever for published content**: Legal audit trail, engagement analysis, liability protection
- **Forever for analytics**: Long-term trend analysis, year-over-year comparisons
- **30 days for queue**: Unpublished items unlikely to be selected after a month

---

#### Common Concerns Addressed

| Concern | Reality | Solution |
|---------|---------|----------|
| **Database Size** | PostgreSQL can handle 100K+ events easily | Storage is cheap (~$1-5/month), premature optimization |
| **Query Performance** | Indexes and partitioning solve this | Use database optimization, not deletion |
| **Privacy** | Financial news from RSS feeds is public data | No personal/private information stored |
| **Legal Liability** | Need audit trail for published content | Deleting = losing proof of compliance |
| **Analytics Requirements** | Need 30/90 day trends for MVP Phase 5 | Can't calculate trends without historical data |

---

#### Why Short Retention (10 Days) is Problematic

**Breaks MVP Requirements:**
- ❌ Can't do "last 30 days" analytics comparison
- ❌ Can't track "which content performed best this month"
- ❌ Can't identify patterns for HITL automation
- ❌ Loses audit trail for published content

**Prevents Future Automation:**
- ❌ Can't train on "similar content passed 10+ times before"
- ❌ Can't calculate "avg engagement for this event type"
- ❌ Deletes learning data before AI can learn from it

**Legal/Compliance Risk:**
- ❌ Someone complains about 15-day-old tweet → no record exists
- ❌ Can't prove content went through quality checks
- ❌ No liability protection for financial content

---

#### Implementation Timeline

**Phase 1: Pre-MVP/MVP (Now - Month 6)**
- Keep all data indefinitely
- Focus on building features, not optimizing storage
- Collect analytics for 6+ months

**Phase 2: Post-MVP (Month 7+)**
- Implement selective retention policy
- Archive old learning data (90+ days)
- Keep published content and analytics forever

**Phase 3: Scale (Year 2+)**
- Move old data to cheaper storage (S3/archive)
- Keep last 30 days in main DB (fast queries)
- Archive rest for compliance/analysis

---

#### Storage Cost Estimates

**Pre-MVP (6 months, ~5000 events):**
- PostgreSQL database: ~2 GB
- Cost on managed hosting: $5-10/month
- Completely negligible

**Post-MVP (12 months, ~10000 events):**
- Database: ~5 GB
- Cost: $10-20/month
- Still very cheap

**Scale (2 years, ~50000 events):**
- Active DB (90 days): ~5 GB → $10-20/month
- Archive (older): ~20 GB → $1-2/month on S3
- Total: ~$12-22/month

**Conclusion:** Storage cost is trivial compared to value of data. Don't optimize prematurely.

---

**End of MVP Plan**

*Created on: January 21, 2026*
*Plan Version: 1.0*
*Target Completion: 4-6 weeks*
