# FinAgent MVP Plan
**AI Finance Media & Intelligence System**

---

## Executive Summary

**Current Phase:** Pre-MVP ✅ COMPLETED (97.56% human-system agreement)

**Next Phase:** MVP - Content Approval Workflow & Multi-Platform Publishing

**Timeline:** 4-6 weeks

**Primary Goal:** Transform FinAgent from an evaluation system into a production-ready content publishing platform that can automatically post finance content to multiple channels with human approval workflow.

---

## MVP Vision

**"From Evaluation to Publication"**

The MVP will enable:
1. Human editors to approve/reject/edit AI-generated content
2. Scheduled publishing to Twitter, LinkedIn, and email newsletter
3. Public website displaying published content
4. Analytics tracking for content performance
5. Feedback loop for continuous improvement

---

## MVP Objectives

### Primary Objectives

1. **Content Approval Workflow** - Enable human-in-the-loop content review, editing, and approval
2. **Multi-Platform Publishing** - Automated posting to Twitter, LinkedIn, and Newsletter
3. **Public Website** - Display published content with search and filtering
4. **Scheduling System** - Queue and schedule content for optimal timing
5. **Analytics Integration** - Track engagement and performance metrics

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Content Approval Cycle Time | <5 minutes/piece | Time from evaluation PASS to scheduled |
| Publishing Success Rate | ≥95% | Successful posts / scheduled posts |
| Multi-Platform Coverage | 100% | All PASS content published to all 3 platforms |
| Website Uptime | ≥99% | Monthly uptime percentage |
| Analytics Tracking | 100% | All published content tracked |

---

## MVP Scope

### In Scope (Must Have)

**Phase 1: Content Approval Workflow (Week 1-2)**
- ✅ Content queue with approval statuses (pending, approved, rejected, scheduled, published)
- ✅ Content editing interface for approved items
- ✅ One-click approve/reject from evaluation screen
- ✅ Bulk approval actions
- ✅ Approval history tracking
- ✅ Editor role management

**Phase 2: Scheduling System (Week 2-3)**
- ✅ Calendar-based scheduling interface
- ✅ Optimal timing suggestions based on platform best practices
- ✅ Timezone-aware scheduling (IST primary, platform-specific)
- ✅ Content queue management (reorder, reschedule, cancel)
- ✅ Publishing worker process
- ✅ Error handling and retry logic

**Phase 3: Multi-Platform Publishing (Week 3-4)**
- ✅ Twitter API integration (v2)
- ✅ LinkedIn API integration (Shares API)
- ✅ Email newsletter system (SendGrid or similar)
- ✅ Platform-specific content formatting
- ✅ Character limit handling
- ✅ Hashtag and mention optimization
- ✅ Platform authentication and credentials management

**Phase 4: Public Website (Week 4-5)**
- ✅ Public-facing content display pages
- ✅ Search and filtering by event type, source, date
- ✅ RSS feed for published content
- ✅ Responsive design for mobile/desktop
- ✅ SEO optimization (meta tags, sitemap)
- ✅ About/Philosophy pages
- ✅ Contact form

**Phase 5: Analytics Integration (Week 5-6)** ⚠️ **CRITICAL MVP COMPONENT**
- ✅ Track engagement metrics (likes, shares, comments, clicks) for EVERY published post
- ✅ Dashboard showing which posts are most liked/preferred
- ✅ Platform-specific analytics integration (Twitter, LinkedIn, Newsletter)
- ✅ Performance comparison: identify best/worst performing content
- ✅ Analyze trends: what content type gets most engagement
- ✅ Export analytics reports for decision-making
- ✅ Weekly summary emails with top performers

**Why Critical:** Without analytics, we can't understand what content resonates with the audience. This data drives all future content decisions and optimization.

### Out of Scope (Future Phases)

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

#### 1. Content Queue (Existing - Enhanced)
```python
class ContentQueue(Base):
    __tablename__ = "content_queue"

    id = UUID(primary_key=True)
    event_id = UUID(ForeignKey("events.id"))
    output_id = UUID(ForeignKey("outputs.id"))
    status = String  # pending, approved, rejected, scheduled, published
    edited_content = Text  # Human-edited version
    scheduled_for = DateTime  # When to publish
    published_at = DateTime  # When actually published
    platform = String  # twitter, linkedin, newsletter, all
    platform_post_id = String  # External platform ID
    approved_by = String  # Editor username
    approved_at = DateTime
    rejection_reason = Text
    created_at = DateTime
    updated_at = DateTime
```

#### 2. Published Content (New)
```python
class PublishedContent(Base):
    __tablename__ = "published_content"

    id = UUID(primary_key=True)
    content_queue_id = UUID(ForeignKey("content_queue.id"))
    platform = String  # twitter, linkedin, newsletter
    platform_post_id = String  # External platform ID
    platform_url = String  # Direct link to post
    content_text = Text  # Final published text
    published_at = DateTime
    engagement_metrics = JSONB  # likes, shares, comments, clicks
    last_synced_at = DateTime
    created_at = DateTime
```

#### 3. Analytics (New)
```python
class Analytics(Base):
    __tablename__ = "analytics"

    id = UUID(primary_key=True)
    published_content_id = UUID(ForeignKey("published_content.id"))
    metric_date = Date  # Date of measurement
    platform = String
    impressions = Integer
    engagements = Integer  # likes + shares + comments
    clicks = Integer
    saves = Integer
    shares = Integer
    comments = Integer
    engagement_rate = Float
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

#### 1. Approval Service
```python
# services/approval_service.py

class ApprovalService:
    def approve_content(self, output_id, approved_by, platform="all")
    def reject_content(self, output_id, reason, rejected_by)
    def edit_content(self, content_queue_id, new_text, edited_by)
    def bulk_approve(self, output_ids, approved_by)
    def get_approval_queue(self, status, limit)
```

#### 2. Scheduling Service
```python
# services/scheduling_service.py

class SchedulingService:
    def schedule_content(self, content_queue_id, scheduled_time, platform)
    def suggest_optimal_time(self, platform, content_type)
    def get_scheduled_content(self, start_date, end_date)
    def reschedule_content(self, content_queue_id, new_time)
    def cancel_scheduled(self, content_queue_id)
```

#### 3. Publishing Service
```python
# services/publishing_service.py

class PublishingService:
    def publish_to_twitter(self, content_queue_id)
    def publish_to_linkedin(self, content_queue_id)
    def publish_to_newsletter(self, content_queue_id)
    def format_for_platform(self, text, platform)
    def handle_character_limits(self, text, limit)
    def add_hashtags(self, text, event_type)
```

#### 4. Analytics Service
```python
# services/analytics_service.py

class AnalyticsService:
    def fetch_twitter_metrics(self, post_id)
    def fetch_linkedin_metrics(self, post_id)
    def fetch_newsletter_metrics(self, campaign_id)
    def calculate_engagement_rate(self, published_content_id)
    def generate_performance_report(self, start_date, end_date)
    def compare_platform_performance()
```

#### 5. Publishing Worker
```python
# workers/publishing_worker.py

class PublishingWorker:
    """Background worker that publishes scheduled content"""

    def run(self):
        # Check every minute for content scheduled in next 5 minutes
        # Publish to all platforms
        # Handle errors and retry logic
        # Update status and store platform IDs
        # Send notifications on success/failure
```

---

## Phase-by-Phase Implementation Plan

### Phase 1: Content Approval Workflow (Week 1-2)

#### Backend Tasks

1. **Enhance Content Queue Model**
   - Add `approved_by`, `approved_at`, `rejection_reason` fields
   - Update status enum to include `approved`, `rejected`
   - Add `edited_content` field for human edits

2. **Create Approval API Endpoints**
   ```
   POST   /api/content-queue/approve/{output_id}
   POST   /api/content-queue/reject/{output_id}
   POST   /api/content-queue/edit/{content_queue_id}
   POST   /api/content-queue/bulk-approve
   GET    /api/content-queue/pending
   GET    /api/content-queue/approved
   ```

3. **Implement Approval Service**
   - Validate content before approval
   - Create content queue entry on approval
   - Log approval history
   - Send WebSocket updates

#### Frontend Tasks

1. **Approval Interface in Outputs Page**
   - Add "Approve" button for PASS evaluations
   - Add "Quick Edit" modal for minor content changes
   - Show approval status badges
   - Add bulk selection and approval

2. **Content Queue Page (New)**
   - List pending approvals
   - List approved content (awaiting schedule)
   - Filter by status, platform, date
   - Edit content inline
   - Preview how content will look on each platform

3. **Approval History Modal**
   - Show who approved/rejected
   - Show when approved/rejected
   - Show edit history
   - Show original vs edited content

#### Exit Criteria Phase 1

- ✅ Editors can approve PASS evaluations with one click
- ✅ Editors can edit content before approval
- ✅ Bulk approval works for multiple items
- ✅ Approval queue shows all pending items
- ✅ WebSocket updates reflect approval changes in real-time

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

### Phase 3: Multi-Platform Publishing (Week 3-4)

#### Backend Tasks

1. **Platform API Integrations**

   **Twitter (X) API v2:**
   - OAuth 2.0 authentication
   - POST /2/tweets endpoint
   - Character limit: 280 chars
   - Handle media uploads (future)
   - Rate limits: 50 tweets per 24 hours (free tier)

   **LinkedIn Shares API:**
   - OAuth 2.0 authentication
   - POST /v2/ugcPosts endpoint
   - Character limit: 3000 chars
   - Company page posting (optional)
   - Rate limits: Check documentation

   **SendGrid Email API:**
   - API key authentication
   - Transactional email sending
   - Newsletter list management
   - Template system
   - Analytics tracking

2. **Publishing API Endpoints**
   ```
   POST   /api/publishing/publish-now/{content_queue_id}
   POST   /api/publishing/publish-scheduled  # Called by worker
   GET    /api/publishing/status/{content_queue_id}
   POST   /api/publishing/retry/{content_queue_id}
   ```

3. **Create Publishing Service**
   - Format content for each platform
   - Handle character limits (truncate + link)
   - Add hashtags based on event type
   - Post to platform APIs
   - Store platform post IDs
   - Handle errors and retry logic

4. **Create Publishing Worker**
   - Background process checking every minute
   - Find content scheduled for next 5 minutes
   - Publish to all enabled platforms
   - Update status to "published"
   - Log success/failure
   - Send notifications

5. **Platform Formatters**
   ```python
   # formatters/twitter_formatter.py
   def format_for_twitter(content, event_type):
       # Truncate to 260 chars (leave room for hashtags)
       # Add relevant hashtags (#Finance #Markets #RBI etc.)
       # Add link to full article on website
       return formatted_tweet

   # formatters/linkedin_formatter.py
   def format_for_linkedin(content, event_type):
       # Can be longer (up to 3000 chars)
       # More professional tone
       # Add relevant hashtags
       # Add link to website
       return formatted_post

   # formatters/newsletter_formatter.py
   def format_for_newsletter(contents_batch):
       # Batch multiple items into digest
       # HTML template with styling
       # Group by event type
       # Add CTAs and website link
       return html_email
   ```

#### Frontend Tasks

1. **Platform Configuration Page**
   - Connect Twitter account (OAuth flow)
   - Connect LinkedIn account (OAuth flow)
   - Configure SendGrid API key
   - Test connection for each platform
   - Enable/disable platforms

2. **Publishing Preview**
   - Preview how content looks on each platform
   - Character count indicator
   - Hashtag preview
   - Platform-specific formatting preview

3. **Publishing Status Dashboard**
   - Show published content
   - Platform-specific URLs (click to view)
   - Publishing errors and retry options
   - Filter by platform, date, status

#### Exit Criteria Phase 3

- ✅ Content publishes successfully to Twitter
- ✅ Content publishes successfully to LinkedIn
- ✅ Newsletter emails send successfully
- ✅ Platform authentication works (OAuth flows)
- ✅ Character limits handled correctly
- ✅ Hashtags added appropriately
- ✅ Platform post IDs stored in database
- ✅ Publishing worker runs without errors
- ✅ Error handling and retry logic works

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

### Phase 5: Analytics Integration (Week 5-6) ⚠️ **CRITICAL MVP COMPONENT**

**Goal:** Understand which content resonates with the audience by tracking every like, comment, share, and click. This data is essential for optimizing future content and validating our content philosophy.

#### Backend Tasks

1. **Analytics Collection** (Fetch from Every Platform)

   **Twitter Analytics:**
   ```python
   # GET /2/tweets/{id} with tweet.fields=public_metrics
   # Returns: impression_count, like_count, retweet_count, reply_count, quote_count
   #
   # CRITICAL METRICS:
   # - Likes: Direct engagement indicator
   # - Retweets/Shares: Virality signal
   # - Replies/Comments: Deep engagement
   # - Impressions: Reach
   ```

   **LinkedIn Analytics:**
   ```python
   # GET /v2/organizationalEntityShareStatistics
   # Returns: impressions, clicks, likes, comments, shares
   #
   # CRITICAL METRICS:
   # - Likes/Reactions: Professional audience approval
   # - Comments: Thought-provoking content indicator
   # - Shares: Professional network spread
   # - Click-through rate: Content effectiveness
   ```

   **SendGrid Analytics:**
   ```python
   # GET /v3/stats
   # Returns: opens, clicks, bounces, spam_reports
   #
   # CRITICAL METRICS:
   # - Open rate: Subject line effectiveness
   # - Click rate: Content relevance
   # - Engagement over time: Subscriber interest
   ```

2. **Analytics API Endpoints** (Answer: "Which posts are preferred?")
   ```
   POST   /api/analytics/sync/{published_content_id}      # Sync metrics from platform
   GET    /api/analytics/summary                          # Overall performance summary
   GET    /api/analytics/top-performers                   # Top 10 most liked/engaged posts
   GET    /api/analytics/bottom-performers                # Bottom 10 least engaged posts
   GET    /api/analytics/by-platform                      # Compare Twitter vs LinkedIn vs Newsletter
   GET    /api/analytics/by-event-type                    # Which topics get most engagement
   GET    /api/analytics/by-content/{published_content_id} # Detailed metrics for single post
   GET    /api/analytics/by-date-range                    # Performance over time
   GET    /api/analytics/trends                           # Engagement trends (growing/declining)
   GET    /api/analytics/comparison                       # Compare 2+ posts side-by-side
   POST   /api/analytics/export                           # Export to CSV/PDF
   ```

3. **Implement Analytics Service** (Focus: Answer "Which posts work best?")
   - Fetch metrics from each platform (hourly sync)
   - Store in analytics table (time-series data)
   - Calculate engagement rate = (likes + shares + comments) / impressions
   - Identify top performers by engagement rate
   - Identify bottom performers for learning
   - Analyze patterns: which event types get most engagement
   - Compare performance across platforms (Twitter vs LinkedIn vs Newsletter)
   - Generate insights: "Policy explanations get 2x more likes than market updates"
   - Track trends over time: "Engagement increasing/decreasing"

4. **Analytics Worker**
   - Run every hour
   - Sync metrics for content published in last 7 days
   - Update engagement_metrics in published_content table
   - Generate daily summary report
   - Send weekly email digest

#### Frontend Tasks

1. **Analytics Dashboard Page (New)** - Primary View for Understanding Performance

   **Overview Section:**
   - Total impressions, engagements, clicks across all platforms
   - Overall engagement rate trend (last 30 days)
   - Platform breakdown: Twitter vs LinkedIn vs Newsletter

   **Top Performers Section:** ⭐ **MOST IMPORTANT**
   - Table showing top 10 most liked/engaged posts
   - Display: Title, Platform, Likes, Shares, Comments, Engagement Rate
   - Visual indicator: 🔥 for viral posts, ⭐ for high engagement
   - Click to view full post details

   **Bottom Performers Section:** 📉 (Learn from low engagement)
   - Table showing bottom 10 posts
   - Identify patterns in low-performing content
   - Help improve future content

   **Performance by Content Type:**
   - Bar chart: Which event types get most engagement?
   - Example: "FINANCE_POLICY gets 45% engagement, MARKET_MOVEMENT gets 20%"
   - Actionable insight: "Focus on policy explanations"

   **Performance by Platform:**
   - Compare Twitter vs LinkedIn vs Newsletter
   - Understand audience preferences on each platform
   - Optimize content strategy per platform

   **Trends Over Time:**
   - Line chart showing engagement over last 30 days
   - Identify growth or decline patterns
   - Spot viral moments

2. **Content Performance View** (Drill-down per post)
   - **Single Post Analytics:**
     - All metrics: Likes, Shares, Comments, Impressions, Clicks
     - Engagement timeline: How metrics changed over time
     - Platform comparison: Twitter vs LinkedIn performance
     - Compare to average: "This post performed 2.3x better than average"

   - **Audience Insights:**
     - Best time to post (based on when this post got engagement)
     - Demographic data (if available from platforms)
     - Top comments/reactions

   - **Actionable Recommendations:**
     - "Similar content performed well - consider more like this"
     - "This topic resonates with LinkedIn audience"

3. **Export & Reporting Functionality**
   - Export to CSV (all metrics)
   - Export to PDF report (formatted with charts)
   - Date range selector (last 7/30/90 days, custom)
   - Filter by platform, event type, source
   - Schedule automated weekly/monthly reports

#### Exit Criteria Phase 5 ⚠️ **MUST PASS TO COMPLETE MVP**

- ✅ Analytics sync from all 3 platforms (Twitter, LinkedIn, Newsletter)
- ✅ Dashboard displays accurate metrics (manually verified against platform data)
- ✅ **Top Performers section shows most liked/engaged posts** ⭐
- ✅ **Bottom Performers section shows least engaged posts** 📉
- ✅ **Can answer: "Which event type gets most engagement?"** (e.g., Policy vs Market)
- ✅ **Can answer: "Which platform performs best?"** (Twitter vs LinkedIn vs Newsletter)
- ✅ **Can answer: "Is engagement growing or declining?"** (trend analysis)
- ✅ Performance comparison charts render correctly
- ✅ Export to CSV/PDF works with all metrics
- ✅ Weekly summary email sends with top performers highlighted
- ✅ Analytics worker runs hourly without errors
- ✅ All published content has metrics (100% coverage)

**Success Validation:** Editor can look at dashboard and immediately identify:
1. Which 3 posts performed best this week
2. What type of content gets most engagement
3. Which platform has highest engagement rate
4. Whether overall engagement is improving or declining

---

## MVP Exit Criteria

### Functional Requirements

| Requirement | Status |
|-------------|--------|
| **Approval Workflow** | |
| Editors can approve/reject content | ⏳ Pending |
| Editors can edit content before publishing | ⏳ Pending |
| Bulk approval works | ⏳ Pending |
| **Scheduling** | |
| Content can be scheduled for future datetime | ⏳ Pending |
| Calendar view shows scheduled content | ⏳ Pending |
| Optimal time suggestions work | ⏳ Pending |
| **Publishing** | |
| Publishes successfully to Twitter | ⏳ Pending |
| Publishes successfully to LinkedIn | ⏳ Pending |
| Newsletter emails send successfully | ⏳ Pending |
| Publishing worker runs reliably | ⏳ Pending |
| **Website** | |
| Public website displays content | ⏳ Pending |
| Search and filtering work | ⏳ Pending |
| SEO optimized | ⏳ Pending |
| Mobile responsive | ⏳ Pending |
| **Analytics** | |
| Metrics sync from all platforms | ⏳ Pending |
| Dashboard displays accurate data | ⏳ Pending |
| Export functionality works | ⏳ Pending |

### Performance Requirements

| Metric | Target | Status |
|--------|--------|--------|
| Publishing Success Rate | ≥95% | ⏳ Pending |
| Website Load Time | <3 seconds | ⏳ Pending |
| API Response Time | <500ms (p95) | ⏳ Pending |
| Worker Reliability | ≥99% uptime | ⏳ Pending |
| Analytics Sync Accuracy | 100% | ⏳ Pending |

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

### B. Example Content Formats

**Twitter (280 chars):**
```
🏦 RBI keeps repo rate steady at 6.5% for 5th time

The central bank's focus remains on controlling inflation, which has cooled to 5.5%. This means borrowing costs stay the same for now.

💡 What it means: Your loan EMIs won't change yet.

#RBI #MonetaryPolicy
```

**LinkedIn (longer form):**
```
📊 RBI Maintains Status Quo on Interest Rates

The Reserve Bank of India has kept the repo rate unchanged at 6.5% for the fifth consecutive meeting. Here's what you need to know:

🎯 Key Takeaway: The focus remains on bringing inflation down to the 4% target. While inflation has moderated to 5.5%, the RBI is staying cautious.

💼 What This Means for You:
• Home loan EMIs remain stable
• Savings account interest rates unchanged
• No immediate impact on borrowing costs

The RBI continues to balance growth and inflation concerns. Future rate decisions will depend on how inflation behaves in the coming months.

Learn more: [link to website]

#Finance #RBI #InterestRates #IndianEconomy
```

**Newsletter (HTML email):**
```html
<h2>🏦 RBI Holds Repo Rate at 6.5%</h2>

<p>The Reserve Bank of India kept interest rates unchanged at 6.5% in today's policy meeting—the fifth straight hold. Here's a quick breakdown of what this means:</p>

<h3>📌 Key Points:</h3>
<ul>
  <li><strong>Inflation Focus:</strong> RBI's priority is bringing inflation to 4% (currently 5.5%)</li>
  <li><strong>No Rate Hikes:</strong> Borrowing costs remain stable for now</li>
  <li><strong>Your Money:</strong> EMIs and savings rates unchanged</li>
</ul>

<p>The central bank is taking a cautious approach, monitoring inflation closely before making any moves.</p>

<a href="[website link]" style="background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Read Full Analysis →</a>
```

### C. Platform Character Limits & Best Practices

| Platform | Character Limit | Best Practice Length | Hashtags | Links |
|----------|----------------|---------------------|----------|-------|
| Twitter | 280 chars | 250-270 chars | 2-3 | Always shorten |
| LinkedIn | 3000 chars | 600-1000 chars | 3-5 | Full URL OK |
| Newsletter | No limit | 200-300 words | N/A | Full URL |

### D. Optimal Posting Times (IST)

| Platform | Best Days | Best Times (IST) | Worst Times |
|----------|-----------|------------------|-------------|
| Twitter | Mon-Fri | 8-10 AM, 12-1 PM, 5-6 PM | Late night (11 PM - 6 AM) |
| LinkedIn | Tue-Thu | 9-11 AM, 2-3 PM | Weekends |
| Newsletter | Tue-Thu | 8-9 AM | Fridays, Weekends |

---

**End of MVP Plan**

*Created on: January 21, 2026*
*Plan Version: 1.0*
*Target Completion: 4-6 weeks*
