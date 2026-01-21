# Complete MVP Flow
**End-to-End Process from RSS to Publishing**

---

## Question 1: Does Human Evaluation Still Happen in MVP?

**YES, absolutely!**

Human evaluation is the **quality gate** that happens BEFORE content generation. Nothing gets published without human approval.

---

## Question 2: How Does Content Generation Flow Work?

Content generation happens in TWO stages:

**Stage 1: Initial LLM Generation** (Pre-MVP - Already Working)
- Generates raw 200-400 word explanation
- Educational, calm, factual content
- Gets evaluated by human

**Stage 2: Platform-Specific Generation** (MVP - New)
- Takes PASS-evaluated raw output
- Transforms into Twitter/LinkedIn/Newsletter formats
- Different length, structure, tone for each platform

---

## Complete End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PHASE 1: INGESTION                          │
└─────────────────────────────────────────────────────────────────────┘
                              |
                              ↓
                    📡 RSS Feed Polling
                    (Every 30 minutes)
                              |
                              ↓
                    32 RSS Sources Fetched
                              |
                              ↓
                    Deduplication Check
                    (Skip if already processed)
                              |
                              ↓
                    Source Prioritization
                    (Select by category quotas)
                              |
                              ↓
                    Store Event in Database
                              |
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 2: INITIAL CONTENT GENERATION (LLM)               │
└─────────────────────────────────────────────────────────────────────┘
                              |
                              ↓
              📝 Event Type Classification
              (6 categories: FINANCE_POLICY, etc.)
                              |
                              ↓
              📝 Intent Classification
              (EXPLANATORY/DESCRIPTIVE/MARKET_OPINION)
                              |
                              ↓
              🤖 LLM Generation (Ollama llama3)
              Input: RSS event title + summary
              Output: 200-400 word educational explanation
              Time: ~20 seconds
                              |
                              ↓
              ✅ Clarity Validation
              (Check for advice, predictions, jargon)
                              |
                              ↓
              ⚠️ HITL Decision
              (Flag if risky/unclear)
                              |
                              ↓
              💾 Store Output in Database
              (Status: Pending Evaluation)
                              |
                              ↓
              📢 WebSocket Update → Dashboard
                              |
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 3: HUMAN EVALUATION ⚠️ CRITICAL GATE              │
└─────────────────────────────────────────────────────────────────────┘
                              |
                              ↓
              👤 HUMAN EDITOR REVIEWS OUTPUT
              (Via Dashboard - Outputs Page)
                              |
                ┌─────────────┴─────────────┐
                ↓                           ↓
            ❌ FAIL                      ✅ PASS
    (Does not proceed further)      (Continues to next phase)
                |                           |
                ↓                           ↓
    Store evaluation verdict        Store evaluation verdict
    Output stays in database        Output marked as PASS
    Can be re-evaluated later      Ready for content generation
                                            |
                                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│        PHASE 4: PLATFORM-SPECIFIC CONTENT GENERATION (NEW!)          │
└─────────────────────────────────────────────────────────────────────┘
                                            |
                                            ↓
              👤 EDITOR CLICKS "GENERATE CONTENT"
              (Button appears for PASS evaluations)
                                            |
                                            ↓
              🔌 Plugin Registry Activated
              (Loads all enabled platform plugins)
                                            |
                ┌───────────────────────────┼───────────────────────────┐
                ↓                           ↓                           ↓
        🐦 Twitter Plugin          💼 LinkedIn Plugin         📧 Newsletter Plugin
        generate_content()         generate_content()         generate_content()
                |                           |                           |
                ↓                           ↓                           ↓
        🤖 LLM Call                🤖 LLM Call                🤖 LLM Call
        Transform raw output       Transform raw output       Transform raw output
        into 3-5 tweet thread      into 500-800 word post     into full HTML article
                |                           |                           |
                ↓                           ↓                           ↓
        Twitter Thread Format      LinkedIn Post Format       Newsletter Format
        {                          {                          {
          "tweets": [                "text": "...",             "html": "<html>...",
            {"order": 1, ...},       "hashtags": [...]          "subject": "...",
            {"order": 2, ...}      }                            "preview_text": "..."
          ]                                                     }
        }
                |                           |                           |
                ↓                           ↓                           ↓
        Validate Content           Validate Content           Validate Content
        (280 chars, no advice)     (3000 chars, no advice)    (HTML valid, no advice)
                |                           |                           |
                ↓                           ↓                           ↓
        💾 Store Generated         💾 Store Generated         💾 Store Generated
        Content in Database        Content in Database        Content in Database
                |                           |                           |
                └───────────────────────────┴───────────────────────────┘
                                            |
                                            ↓
              ✅ ALL PLATFORMS GENERATED
              (3 formats stored in generated_content table)
                                            |
                                            ↓
              📢 WebSocket Update → Dashboard
              "Content generation complete"
                                            |
                                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 5: CONTENT PREVIEW & SELECTION                    │
└─────────────────────────────────────────────────────────────────────┘
                                            |
                                            ↓
              👤 EDITOR SEES PREVIEW MODAL
              (Shows all 3 generated formats)
                                            |
                                            ↓
              📑 Tabbed Interface:
              - Tab 1: Twitter Thread (3-5 tweets preview)
              - Tab 2: LinkedIn Post (full post preview)
              - Tab 3: Newsletter (HTML email preview)
                                            |
                                            ↓
              👤 EDITOR REVIEWS EACH FORMAT
              - Does Twitter thread flow well?
              - Is LinkedIn post professional?
              - Is newsletter comprehensive?
                                            |
                ┌───────────────────────────┼───────────────────────────┐
                ↓                           ↓                           ↓
    Option 1: Approve All          Option 2: Edit & Approve    Option 3: Reject
    (All 3 platforms)              (Modify specific platform)  (Go back)
                |                           |                           |
                ↓                           ↓                           ↓
    Mark all 3 as approved         Open inline editor          Do not proceed
    Send to scheduling queue       Edit content for platform   Can regenerate later
                                   Save edited version
                                   Mark as approved
                                            |
                └───────────────────────────┴───────────────────────────┘
                                            |
                                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 6: CONTENT APPROVAL (HUMAN GATE #2)               │
└─────────────────────────────────────────────────────────────────────┘
                                            |
                                            ↓
              👤 EDITOR FINAL APPROVAL
              For each platform individually:
              - ✅ Approve for Twitter
              - ✅ Approve for LinkedIn
              - ✅ Approve for Newsletter
              (Can approve all or subset)
                                            |
                                            ↓
              💾 Update Status → "approved"
              Store approval metadata:
              - approved_by: editor_id
              - approved_at: timestamp
              - platform: twitter/linkedin/newsletter
                                            |
                                            ↓
              📢 WebSocket Update → Dashboard
                                            |
                                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 7: SCHEDULING                                     │
└─────────────────────────────────────────────────────────────────────┘
                                            |
                                            ↓
              👤 EDITOR SCHEDULES CONTENT
              (Via Scheduling Interface)
                                            |
                ┌───────────────────────────┼───────────────────────────┐
                ↓                           ↓                           ↓
    Option 1: Schedule Now        Option 2: Schedule Later    Option 3: Optimal Time
    (Publish immediately)         (Pick date/time)            (System suggests best time)
                |                           |                           |
                ↓                           ↓                           ↓
    scheduled_for = now()          scheduled_for = user_time   scheduled_for = optimal_time
                                                                (9 AM IST for Twitter, etc.)
                                            |
                └───────────────────────────┴───────────────────────────┘
                                            |
                                            ↓
              💾 Update Content Queue
              - status: "scheduled"
              - scheduled_for: datetime
              - platform: twitter/linkedin/newsletter
                                            |
                                            ↓
              📅 Add to Calendar View
              (Shows in scheduling dashboard)
                                            |
                                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 8: PUBLISHING (AUTOMATED)                         │
└─────────────────────────────────────────────────────────────────────┘
                                            |
                                            ↓
              ⏰ Publishing Worker Running
              (Background process checks every minute)
                                            |
                                            ↓
              🔍 Query: SELECT * FROM content_queue
              WHERE status = 'scheduled'
              AND scheduled_for <= NOW() + 5 minutes
                                            |
                                            ↓
              📋 Found content ready to publish
                                            |
                ┌───────────────────────────┼───────────────────────────┐
                ↓                           ↓                           ↓
        🐦 Twitter                  💼 LinkedIn                📧 Newsletter
        TwitterPlugin               LinkedInPlugin             NewsletterPlugin
        publish()                   publish()                  publish()
                |                           |                           |
                ↓                           ↓                           ↓
        Get credentials             Get credentials            Get credentials
        from platform_credentials   from platform_credentials  from platform_credentials
                |                           |                           |
                ↓                           ↓                           ↓
        🌐 API Call                 🌐 API Call                🌐 API Call
        POST /2/tweets              POST /v2/ugcPosts          POST /v3/mail/send
        (Twitter API v2)            (LinkedIn API)             (SendGrid API)
                |                           |                           |
                ↓                           ↓                           ↓
        📝 Post Thread              📝 Post Single Post        📧 Send Email
        - Tweet 1                   - Full post with           - HTML email to list
        - Tweet 2                     hashtags                 - Subject + preview
        - Tweet 3                   - Professional tone        - Link to website
        - Tweet 4
        - Tweet 5
                |                           |                           |
                ↓                           ↓                           ↓
        ✅ Success                  ✅ Success                 ✅ Success
        platform_id: tweet_id       platform_id: post_id       platform_id: campaign_id
        platform_url: twitter.com/  platform_url: linkedin.    platform_url: sendgrid
          status/12345                com/feed/update/67890      dashboard
                |                           |                           |
                └───────────────────────────┴───────────────────────────┘
                                            |
                                            ↓
              💾 Store Published Content
              - status: "published"
              - platform_post_id: external_id
              - platform_url: direct_link
              - published_at: timestamp
                                            |
                                            ↓
              📢 WebSocket Update → Dashboard
              "Content published successfully"
                                            |
                                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 9: ANALYTICS (ONGOING)                            │
└─────────────────────────────────────────────────────────────────────┘
                                            |
                                            ↓
              ⏰ Analytics Worker Running
              (Background process runs every hour)
                                            |
                                            ↓
              🔍 Query: SELECT * FROM published_content
              WHERE published_at > NOW() - 7 days
                                            |
                                            ↓
              📋 Found published content to sync
                                            |
                ┌───────────────────────────┼───────────────────────────┐
                ↓                           ↓                           ↓
        🐦 Twitter Analytics        💼 LinkedIn Analytics      📧 Newsletter Analytics
        TwitterPlugin               LinkedInPlugin             SendGridPlugin
        fetch_analytics()           fetch_analytics()          fetch_analytics()
                |                           |                           |
                ↓                           ↓                           ↓
        🌐 API Call                 🌐 API Call                🌐 API Call
        GET /2/tweets/{id}          GET /v2/organizational     GET /v3/stats
        ?tweet.fields=              EntityShareStatistics      ?start_date=...
          public_metrics
                |                           |                           |
                ↓                           ↓                           ↓
        📊 Fetch Metrics            📊 Fetch Metrics           📊 Fetch Metrics
        - impressions: 1250         - impressions: 850         - opens: 320
        - likes: 45                 - likes: 32                - clicks: 65
        - retweets: 12              - shares: 8                - bounces: 2
        - replies: 6                - comments: 5              - unsubscribes: 1
        - bookmarks: 8              - clicks: 28
                |                           |                           |
                └───────────────────────────┴───────────────────────────┘
                                            |
                                            ↓
              💾 Store Analytics
              - Update analytics table
              - Calculate engagement_rate
              - Update last_synced_at
                                            |
                                            ↓
              📊 Update Dashboard
              (Analytics page shows latest metrics)
```

---

## Detailed Breakdown by Phase

### Phase 1-2: Initial Content Generation (Existing System)

**What Happens:**
1. RSS event fetched
2. LLM generates 200-400 word explanation
3. Stored as "Output" in database

**Who Does It:**
- System (automated)

**Time:**
- ~20 seconds per event

**Result:**
- Raw output ready for evaluation
- Status: "Pending Evaluation"

---

### Phase 3: Human Evaluation ⚠️ CRITICAL GATE

**What Happens:**
1. Editor opens Outputs page in dashboard
2. Sees list of pending outputs
3. Clicks on output to review
4. Reads LLM-generated explanation
5. Checks for:
   - Advice language (❌ "you should buy")
   - Predictions (❌ "market will crash")
   - Jargon not explained (❌ "repo rate" without explanation)
   - Factual errors (❌ wrong numbers/dates)
   - Incomplete explanations (❌ missing context)
   - Sensationalism (❌ "shocking news!")
6. Makes verdict:
   - **PASS** → Content is good, proceed to generation
   - **FAIL** → Content has issues, does not proceed

**Who Does It:**
- **HUMAN EDITOR** (manual review)

**Time:**
- 1-3 minutes per output

**Result:**
- PASS: Output can proceed to platform-specific generation
- FAIL: Output stops here, stored in database for reference

**Question 1 Answer:**
YES, human evaluation STILL happens in MVP. It's the quality gate before any content gets published.

---

### Phase 4: Platform-Specific Content Generation (NEW in MVP)

**What Happens:**
1. Editor clicks "Generate Content" button (only visible for PASS outputs)
2. System calls Plugin Registry
3. Plugin Registry loads all enabled plugins (Twitter, LinkedIn, Newsletter)
4. Each plugin receives the raw output (200-400 words)
5. Each plugin uses LLM to transform raw output into platform-specific format:
   - **Twitter Plugin:** Transforms into 3-5 tweet thread
   - **LinkedIn Plugin:** Transforms into 500-800 word professional post
   - **Newsletter Plugin:** Transforms into full HTML article
6. Each plugin validates its generated content
7. All 3 formats stored in `generated_content` table

**Who Does It:**
- System (automated after human clicks button)

**Time:**
- ~60 seconds (all 3 formats generated in parallel)

**Result:**
- 3 different content formats stored in database
- Each format optimized for its platform
- Status: "generated"

**Question 2 Answer - Part 1:**
Content generation happens in TWO stages:
1. **Stage 1 (Pre-MVP):** LLM generates raw 200-400 word explanation
2. **Stage 2 (MVP):** Plugins transform raw output into platform-specific formats

---

### Phase 5: Content Preview & Selection

**What Happens:**
1. Modal appears showing all 3 generated formats
2. Tabbed interface:
   - **Twitter Tab:** Shows 3-5 tweet thread with preview of how it looks on Twitter
   - **LinkedIn Tab:** Shows full post with preview of how it looks on LinkedIn
   - **Newsletter Tab:** Shows HTML email with preview
3. Editor reviews each format:
   - Does Twitter thread have good flow?
   - Is LinkedIn post professional enough?
   - Is newsletter comprehensive?
4. Editor can:
   - **Approve All:** All 3 formats good to go
   - **Edit & Approve:** Modify specific platform content inline
   - **Reject:** Go back, don't proceed

**Who Does It:**
- **HUMAN EDITOR** (manual review)

**Time:**
- 2-5 minutes per output

**Result:**
- Editor decides which platforms to publish to
- Can publish to all 3 or just 1-2 platforms

---

### Phase 6: Content Approval (Human Gate #2)

**What Happens:**
1. For each platform individually:
   - Editor clicks "Approve for Twitter"
   - Editor clicks "Approve for LinkedIn"
   - Editor clicks "Approve for Newsletter"
2. System records approval metadata:
   - Who approved (editor_id)
   - When approved (timestamp)
   - Which platform
3. Status updated to "approved"

**Who Does It:**
- **HUMAN EDITOR** (final approval)

**Time:**
- 1-2 minutes

**Result:**
- Content approved for specific platforms
- Ready for scheduling

---

### Phase 7: Scheduling

**What Happens:**
1. Editor opens Scheduling interface
2. Sees calendar view with scheduled content
3. For each approved content, editor chooses:
   - **Option 1:** Schedule Now (publish immediately)
   - **Option 2:** Schedule Later (pick specific date/time)
   - **Option 3:** Optimal Time (system suggests best time for each platform)
4. System stores scheduled_for datetime
5. Content appears in calendar view

**Who Does It:**
- **HUMAN EDITOR** (sets schedule)

**Time:**
- 1-2 minutes

**Result:**
- Content scheduled for specific date/time
- Status: "scheduled"

---

### Phase 8: Publishing (Automated)

**What Happens:**
1. Publishing Worker runs every minute (background process)
2. Queries database for content where:
   - status = "scheduled"
   - scheduled_for <= NOW() + 5 minutes
3. For each content ready to publish:
   - Get appropriate plugin (Twitter/LinkedIn/Newsletter)
   - Get platform credentials from database
   - Call plugin.publish()
   - Plugin makes API call to external platform
   - Platform returns post ID and URL
4. Store published content:
   - platform_post_id
   - platform_url
   - published_at timestamp
5. Update status to "published"

**Who Does It:**
- **SYSTEM** (fully automated)

**Time:**
- ~2-5 seconds per platform

**Result:**
- Content live on Twitter/LinkedIn/Newsletter
- URLs stored in database
- Status: "published"

---

### Phase 9: Analytics (Ongoing)

**What Happens:**
1. Analytics Worker runs every hour (background process)
2. Queries database for published content from last 7 days
3. For each published content:
   - Get appropriate plugin
   - Call plugin.fetch_analytics()
   - Plugin makes API call to platform
   - Fetches metrics (impressions, likes, shares, clicks)
4. Store analytics in database
5. Update dashboard with latest metrics

**Who Does It:**
- **SYSTEM** (fully automated)

**Time:**
- Runs every hour

**Result:**
- Up-to-date engagement metrics
- Analytics dashboard shows performance

---

## Key Differences: Stage 1 vs Stage 2 Content Generation

### Stage 1: Initial LLM Generation (Pre-MVP - Existing)

**Input:**
```
RSS Event Title: "RBI keeps repo rate at 6.5%"
RSS Event Summary: "The Reserve Bank of India..."
```

**Prompt:**
```
You are a finance educator. Explain this event in simple terms:
- What happened?
- Why is it important?
- What does it mean for readers?
- Keep it factual, no advice, no predictions.
```

**Output:**
```
The Reserve Bank of India has kept the repo rate unchanged at 6.5%
for the fifth consecutive meeting. The repo rate is the rate at which
RBI lends to banks. When it goes up, loans become more expensive...

[200-400 words total]
```

**Purpose:**
- Create educational explanation
- Human-readable content
- Foundation for platform-specific content

---

### Stage 2: Platform-Specific Generation (MVP - New)

**Input:**
```
Raw Output: [The 200-400 word explanation from Stage 1]
Event Type: FINANCE_POLICY
Source: RBI_PRESS
```

**Twitter Plugin Prompt:**
```
Transform the following into a Twitter thread (3-5 tweets):
[Raw output from Stage 1]

Requirements:
- Tweet 1: Hook with emoji
- Tweet 2: Context
- Tweet 3: Impact (bullets)
- Tweet 4: Education
- Tweet 5: CTA + hashtags
- Max 280 chars per tweet
```

**Twitter Output:**
```json
{
  "format": "thread",
  "tweets": [
    {"order": 1, "text": "🏦 RBI keeps repo rate at 6.5%..."},
    {"order": 2, "text": "The central bank's focus..."},
    {"order": 3, "text": "What this means: • EMIs stay same..."},
    {"order": 4, "text": "The repo rate is..."},
    {"order": 5, "text": "📖 Read more: [link] #RBI #Finance"}
  ]
}
```

**LinkedIn Plugin Prompt:**
```
Transform the following into a LinkedIn post (500-800 words):
[Raw output from Stage 1]

Requirements:
- Professional tone
- Emoji headers (🎯, 💼, 📈)
- "What This Means for You" section
- 3-5 hashtags
```

**LinkedIn Output:**
```json
{
  "format": "single_post",
  "text": "📊 RBI Holds Repo Rate Steady at 6.5%\n\n🎯 Why?\nThe RBI is...",
  "hashtags": ["Finance", "RBI", "InterestRates"]
}
```

**Newsletter Plugin Prompt:**
```
Transform the following into a newsletter article (HTML):
[Raw output from Stage 1]

Requirements:
- HTML format with h1, h2, p, ul tags
- Subject line (max 60 chars)
- Preview text (max 100 chars)
- Comprehensive (400-800 words)
```

**Newsletter Output:**
```json
{
  "format": "article",
  "html": "<h1>RBI Keeps Repo Rate at 6.5%</h1><p><strong>Quick Summary...</p>...",
  "subject": "RBI Holds Rates: What It Means for Your Money",
  "preview_text": "The central bank kept interest rates unchanged..."
}
```

**Purpose:**
- Adapt content for each platform's audience
- Optimize length and format
- Add platform-specific elements (hashtags, emojis, structure)

---

## Summary: Answers to Your Questions

### Question 1: Does human evaluation still happen in MVP?

**YES, absolutely!**

Human evaluation happens at **TWO critical gates:**

1. **Gate #1: Initial Evaluation (Phase 3)**
   - Human evaluates raw LLM output
   - Verdict: PASS or FAIL
   - Only PASS outputs proceed to content generation

2. **Gate #2: Content Approval (Phase 6)**
   - Human reviews platform-specific generated content
   - Can edit any platform version
   - Approves each platform individually
   - Only approved content goes to scheduling

**Nothing gets published without human approval at both gates.**

---

### Question 2: How does content generation flow work?

**Content generation happens in TWO stages:**

**Stage 1: Initial Generation (Existing - Pre-MVP)**
```
RSS Event → LLM → 200-400 word explanation → Database
Time: ~20 seconds
Result: Raw output ready for evaluation
```

**Stage 2: Platform-Specific Generation (New - MVP)**
```
PASS Evaluation → Human clicks "Generate" → Plugin Registry → All Plugins → 3 Formats
Time: ~60 seconds (parallel)
Result: Twitter thread + LinkedIn post + Newsletter article
```

**Then:**
```
Human reviews all 3 formats → Edits if needed → Approves selected platforms → Schedules → Publishes
```

**Key Point:**
- Stage 1 creates ONE universal explanation
- Stage 2 transforms that ONE explanation into THREE platform-specific formats
- Each format optimized for its platform's audience and constraints

---

**End of Complete MVP Flow**

*Created: January 21, 2026*
*Version: 1.0*
