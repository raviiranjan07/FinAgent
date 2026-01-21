# Analytics Implementation Plan
**FinAgent - Understanding Content Performance**

---

## Overview

**Goal:** Track and analyze every published post's performance to understand what content resonates with the audience.

**Key Questions Analytics Must Answer:**
1. **Which posts are most liked/preferred?** (Top performers)
2. **Which posts underperformed?** (Bottom performers - learn from these)
3. **What type of content gets most engagement?** (Policy vs Market vs Macro)
4. **Which platform performs best?** (Twitter vs LinkedIn vs Newsletter)
5. **Is our content improving over time?** (Engagement trends)
6. **What's the best time to post?** (Timing analysis)

---

## Metrics We Track

### Primary Engagement Metrics

| Metric | Description | Importance | Calculation |
|--------|-------------|------------|-------------|
| **Likes** | Direct appreciation | High | Count from platform API |
| **Shares** | Content spreading | Very High | Retweets (Twitter), Shares (LinkedIn) |
| **Comments** | Deep engagement | Very High | Replies/Comments count |
| **Impressions** | Reach | Medium | How many saw the post |
| **Clicks** | Action taken | High | Link clicks, "read more" clicks |
| **Engagement Rate** | Overall performance | **Critical** | (Likes + Shares + Comments) / Impressions × 100 |

### Derived Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| **Virality Score** | Shares / Impressions × 100 | How shareable is the content |
| **Discussion Score** | Comments / Likes | How thought-provoking |
| **Conversion Rate** | Clicks / Impressions × 100 | How compelling is the content |
| **Performance Rank** | Percentile ranking | Compare post to all posts |

---

## Database Schema

### Analytics Table (Enhanced)

```python
class Analytics(Base):
    __tablename__ = "analytics"

    # Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    published_content_id = Column(UUID(as_uuid=True), ForeignKey("published_content.id"), nullable=False)

    # Time tracking
    metric_date = Column(Date, nullable=False)  # Date of measurement
    metric_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Platform
    platform = Column(String(50), nullable=False)  # twitter, linkedin, newsletter

    # Raw Metrics (from platform APIs)
    impressions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)  # retweets for twitter
    comments = Column(Integer, default=0)  # replies for twitter
    clicks = Column(Integer, default=0)
    saves = Column(Integer, default=0)  # bookmarks
    quote_tweets = Column(Integer, default=0)  # twitter-specific

    # Calculated Metrics
    total_engagements = Column(Integer, default=0)  # likes + shares + comments
    engagement_rate = Column(Float, default=0.0)  # (engagements / impressions) * 100
    virality_score = Column(Float, default=0.0)  # (shares / impressions) * 100
    discussion_score = Column(Float, default=0.0)  # comments / likes (0 if no likes)
    conversion_rate = Column(Float, default=0.0)  # (clicks / impressions) * 100

    # Ranking (compared to other posts)
    performance_rank = Column(Integer)  # 1 = best, higher = worse
    performance_percentile = Column(Float)  # 95th percentile = top 5%

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    published_content = relationship("PublishedContent", back_populates="analytics")

    # Indexes for fast queries
    __table_args__ = (
        Index('idx_analytics_platform', 'platform'),
        Index('idx_analytics_date', 'metric_date'),
        Index('idx_analytics_engagement_rate', 'engagement_rate'),
        Index('idx_analytics_performance_rank', 'performance_rank'),
    )
```

### Content Performance Summary Table (New)

```python
class ContentPerformanceSummary(Base):
    """Aggregated performance summary per content, updated hourly"""
    __tablename__ = "content_performance_summary"

    # Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    published_content_id = Column(UUID(as_uuid=True), ForeignKey("published_content.id"), unique=True)

    # Event context
    event_type = Column(String(50))  # FINANCE_POLICY, MARKET_MOVEMENT, etc.
    event_source = Column(String(100))  # RBI, SEBI, Bloomberg, etc.

    # Aggregated metrics (sum across all platforms)
    total_impressions = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_engagements = Column(Integer, default=0)

    # Best platform for this content
    best_platform = Column(String(50))  # Platform with highest engagement
    best_platform_engagement_rate = Column(Float, default=0.0)

    # Overall performance
    overall_engagement_rate = Column(Float, default=0.0)
    overall_virality_score = Column(Float, default=0.0)
    overall_performance_rank = Column(Integer)

    # Time tracking
    published_at = Column(DateTime)
    first_24h_engagement = Column(Integer, default=0)  # Engagement in first 24 hours
    peak_engagement_at = Column(DateTime)  # When engagement peaked

    # Timestamps
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    published_content = relationship("PublishedContent", back_populates="performance_summary")
```

### Event Type Performance Table (New)

```python
class EventTypePerformance(Base):
    """Track which event types perform best"""
    __tablename__ = "event_type_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # FINANCE_POLICY, MARKET_MOVEMENT, etc.

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Statistics
    total_posts = Column(Integer, default=0)
    total_impressions = Column(Integer, default=0)
    total_engagements = Column(Integer, default=0)
    avg_engagement_rate = Column(Float, default=0.0)

    # Best/Worst posts
    best_post_id = Column(UUID(as_uuid=True), ForeignKey("published_content.id"))
    worst_post_id = Column(UUID(as_uuid=True), ForeignKey("published_content.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## API Endpoints

### Analytics Collection Endpoints

```python
# Sync analytics from platforms
POST   /api/analytics/sync/{published_content_id}
POST   /api/analytics/sync-all                     # Sync all recent content
POST   /api/analytics/sync-platform/{platform}     # Sync all from one platform
```

### Analytics Query Endpoints

```python
# Summary & Overview
GET    /api/analytics/summary                       # Overall performance summary
GET    /api/analytics/summary/platform/{platform}   # Summary for specific platform

# Top & Bottom Performers (Answer: "Which posts are preferred?")
GET    /api/analytics/top-performers?limit=10&period=7d
GET    /api/analytics/bottom-performers?limit=10&period=7d
GET    /api/analytics/top-by-event-type/{event_type}

# Performance Analysis (Answer: "What content works best?")
GET    /api/analytics/by-event-type                 # Performance grouped by event type
GET    /api/analytics/by-platform                   # Compare platforms
GET    /api/analytics/by-source                     # Performance by source (RBI, Bloomberg, etc.)

# Specific Content
GET    /api/analytics/by-content/{published_content_id}
GET    /api/analytics/compare?ids=uuid1,uuid2,uuid3  # Compare multiple posts

# Trends (Answer: "Is engagement improving?")
GET    /api/analytics/trends?period=30d              # Engagement trends over time
GET    /api/analytics/trends/platform/{platform}     # Platform-specific trends
GET    /api/analytics/trends/event-type/{event_type} # Event type trends

# Time Analysis
GET    /api/analytics/best-posting-times             # When to post for max engagement
GET    /api/analytics/hourly-breakdown               # Engagement by hour of day

# Export
POST   /api/analytics/export?format=csv              # Export to CSV
POST   /api/analytics/export?format=pdf              # Export to PDF report
```

### Response Examples

**Top Performers Response:**
```json
{
  "period": {
    "start": "2026-01-14",
    "end": "2026-01-21"
  },
  "top_performers": [
    {
      "rank": 1,
      "published_content_id": "uuid-1",
      "title": "RBI keeps repo rate steady at 6.5%",
      "event_type": "FINANCE_POLICY",
      "published_at": "2026-01-20T09:00:00Z",
      "platforms": {
        "twitter": {
          "likes": 450,
          "shares": 120,
          "comments": 35,
          "impressions": 15000,
          "engagement_rate": 4.03
        },
        "linkedin": {
          "likes": 230,
          "shares": 45,
          "comments": 18,
          "impressions": 8000,
          "engagement_rate": 3.66
        }
      },
      "overall_engagement_rate": 3.88,
      "performance_percentile": 98.5,
      "reason": "Policy explanations resonate well with audience"
    },
    // ... more top performers
  ],
  "insights": [
    "FINANCE_POLICY content averages 3.2% engagement vs 1.8% for MARKET_MOVEMENT",
    "LinkedIn performs 1.5x better than Twitter for policy content",
    "Engagement is 25% higher when posted between 8-10 AM IST"
  ]
}
```

**Event Type Performance Response:**
```json
{
  "period": {
    "start": "2026-01-01",
    "end": "2026-01-21"
  },
  "event_types": [
    {
      "event_type": "FINANCE_POLICY",
      "total_posts": 42,
      "avg_engagement_rate": 3.45,
      "total_impressions": 450000,
      "total_engagements": 15525,
      "best_post": {
        "id": "uuid-1",
        "title": "RBI announces new digital lending rules",
        "engagement_rate": 5.2
      },
      "worst_post": {
        "id": "uuid-2",
        "title": "Minor SEBI circular update",
        "engagement_rate": 0.8
      },
      "trend": "growing",
      "recommendation": "Focus more on policy explanations"
    },
    {
      "event_type": "MARKET_MOVEMENT",
      "total_posts": 38,
      "avg_engagement_rate": 1.85,
      "total_impressions": 320000,
      "total_engagements": 5920,
      "trend": "stable",
      "recommendation": "Market updates get lower engagement - consider reducing frequency"
    },
    // ... more event types
  ]
}
```

---

## Analytics Service Implementation

### Core Service Class

```python
# services/analytics_service.py

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from database.models import Analytics, PublishedContent, ContentPerformanceSummary, EventTypePerformance
from integrations.twitter_api import TwitterAPI
from integrations.linkedin_api import LinkedInAPI
from integrations.sendgrid_api import SendGridAPI

class AnalyticsService:
    """
    Service for tracking and analyzing content performance

    Answers key questions:
    1. Which posts are most liked/preferred?
    2. What content type performs best?
    3. Which platform is most effective?
    4. Is engagement growing or declining?
    """

    def __init__(self, db_session):
        self.db = db_session
        self.twitter = TwitterAPI()
        self.linkedin = LinkedInAPI()
        self.sendgrid = SendGridAPI()

    # ===== Data Collection Methods =====

    async def sync_analytics(self, published_content_id: str) -> Dict:
        """
        Fetch latest metrics from all platforms for a published post

        This is called:
        - Immediately after publishing (get baseline)
        - Every hour for first 24 hours (active monitoring)
        - Every 6 hours for next 7 days (decay monitoring)
        - Daily after 7 days (long-tail tracking)
        """
        content = self.db.query(PublishedContent).filter_by(id=published_content_id).first()
        if not content:
            raise ValueError(f"Content {published_content_id} not found")

        results = {}

        # Sync from each platform
        if content.platform == "twitter":
            metrics = await self.twitter.get_tweet_metrics(content.platform_post_id)
            results["twitter"] = await self._store_twitter_metrics(content.id, metrics)

        elif content.platform == "linkedin":
            metrics = await self.linkedin.get_post_metrics(content.platform_post_id)
            results["linkedin"] = await self._store_linkedin_metrics(content.id, metrics)

        elif content.platform == "newsletter":
            metrics = await self.sendgrid.get_campaign_metrics(content.platform_post_id)
            results["newsletter"] = await self._store_newsletter_metrics(content.id, metrics)

        # Update performance summary
        await self._update_performance_summary(content.id)

        return results

    async def _store_twitter_metrics(self, published_content_id: str, metrics: Dict) -> Dict:
        """Store Twitter metrics in analytics table"""
        impressions = metrics.get("impression_count", 0)
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        quotes = metrics.get("quote_count", 0)

        total_engagements = likes + retweets + replies + quotes
        engagement_rate = (total_engagements / impressions * 100) if impressions > 0 else 0.0
        virality_score = (retweets / impressions * 100) if impressions > 0 else 0.0
        discussion_score = (replies / likes) if likes > 0 else 0.0

        analytics = Analytics(
            published_content_id=published_content_id,
            metric_date=datetime.utcnow().date(),
            metric_timestamp=datetime.utcnow(),
            platform="twitter",
            impressions=impressions,
            likes=likes,
            shares=retweets,
            comments=replies,
            quote_tweets=quotes,
            total_engagements=total_engagements,
            engagement_rate=engagement_rate,
            virality_score=virality_score,
            discussion_score=discussion_score
        )

        self.db.add(analytics)
        self.db.commit()

        return {
            "platform": "twitter",
            "engagement_rate": engagement_rate,
            "total_engagements": total_engagements
        }

    async def _store_linkedin_metrics(self, published_content_id: str, metrics: Dict) -> Dict:
        """Store LinkedIn metrics in analytics table"""
        impressions = metrics.get("impressionCount", 0)
        likes = metrics.get("likeCount", 0)
        shares = metrics.get("shareCount", 0)
        comments = metrics.get("commentCount", 0)
        clicks = metrics.get("clickCount", 0)

        total_engagements = likes + shares + comments
        engagement_rate = (total_engagements / impressions * 100) if impressions > 0 else 0.0
        virality_score = (shares / impressions * 100) if impressions > 0 else 0.0
        discussion_score = (comments / likes) if likes > 0 else 0.0
        conversion_rate = (clicks / impressions * 100) if impressions > 0 else 0.0

        analytics = Analytics(
            published_content_id=published_content_id,
            metric_date=datetime.utcnow().date(),
            metric_timestamp=datetime.utcnow(),
            platform="linkedin",
            impressions=impressions,
            likes=likes,
            shares=shares,
            comments=comments,
            clicks=clicks,
            total_engagements=total_engagements,
            engagement_rate=engagement_rate,
            virality_score=virality_score,
            discussion_score=discussion_score,
            conversion_rate=conversion_rate
        )

        self.db.add(analytics)
        self.db.commit()

        return {
            "platform": "linkedin",
            "engagement_rate": engagement_rate,
            "total_engagements": total_engagements
        }

    async def _store_newsletter_metrics(self, published_content_id: str, metrics: Dict) -> Dict:
        """Store newsletter metrics in analytics table"""
        sent = metrics.get("sent", 0)
        opens = metrics.get("opens", 0)
        clicks = metrics.get("clicks", 0)

        # For newsletter, "impressions" = emails opened
        # "engagement" = clicks (action taken)
        engagement_rate = (clicks / opens * 100) if opens > 0 else 0.0
        open_rate = (opens / sent * 100) if sent > 0 else 0.0

        analytics = Analytics(
            published_content_id=published_content_id,
            metric_date=datetime.utcnow().date(),
            metric_timestamp=datetime.utcnow(),
            platform="newsletter",
            impressions=opens,  # Opened emails = impressions
            clicks=clicks,
            total_engagements=clicks,
            engagement_rate=engagement_rate,
            conversion_rate=open_rate
        )

        self.db.add(analytics)
        self.db.commit()

        return {
            "platform": "newsletter",
            "open_rate": open_rate,
            "engagement_rate": engagement_rate,
            "total_engagements": clicks
        }

    # ===== Performance Summary Methods =====

    async def _update_performance_summary(self, published_content_id: str):
        """Update aggregated performance summary for a content"""
        # Get all analytics for this content
        analytics_records = self.db.query(Analytics).filter_by(
            published_content_id=published_content_id
        ).all()

        if not analytics_records:
            return

        # Aggregate metrics across platforms
        total_impressions = sum(a.impressions for a in analytics_records)
        total_likes = sum(a.likes for a in analytics_records)
        total_shares = sum(a.shares for a in analytics_records)
        total_comments = sum(a.comments for a in analytics_records)
        total_clicks = sum(a.clicks for a in analytics_records)
        total_engagements = sum(a.total_engagements for a in analytics_records)

        overall_engagement_rate = (total_engagements / total_impressions * 100) if total_impressions > 0 else 0.0
        overall_virality_score = (total_shares / total_impressions * 100) if total_impressions > 0 else 0.0

        # Find best platform
        best_platform_record = max(analytics_records, key=lambda a: a.engagement_rate)

        # Get or create summary
        summary = self.db.query(ContentPerformanceSummary).filter_by(
            published_content_id=published_content_id
        ).first()

        if not summary:
            content = self.db.query(PublishedContent).filter_by(id=published_content_id).first()
            summary = ContentPerformanceSummary(
                published_content_id=published_content_id,
                event_type=content.event_type,
                event_source=content.event_source,
                published_at=content.published_at
            )
            self.db.add(summary)

        # Update summary
        summary.total_impressions = total_impressions
        summary.total_likes = total_likes
        summary.total_shares = total_shares
        summary.total_comments = total_comments
        summary.total_clicks = total_clicks
        summary.total_engagements = total_engagements
        summary.overall_engagement_rate = overall_engagement_rate
        summary.overall_virality_score = overall_virality_score
        summary.best_platform = best_platform_record.platform
        summary.best_platform_engagement_rate = best_platform_record.engagement_rate
        summary.last_synced_at = datetime.utcnow()

        self.db.commit()

    # ===== Query Methods (Answer key questions) =====

    def get_top_performers(self, limit: int = 10, period_days: int = 7) -> List[Dict]:
        """
        Answer: "Which posts are most liked/preferred?"

        Returns top performing posts ranked by engagement rate
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        top_content = self.db.query(ContentPerformanceSummary).filter(
            ContentPerformanceSummary.published_at >= cutoff_date
        ).order_by(
            desc(ContentPerformanceSummary.overall_engagement_rate)
        ).limit(limit).all()

        results = []
        for rank, content_summary in enumerate(top_content, start=1):
            # Get full content details
            content = self.db.query(PublishedContent).filter_by(
                id=content_summary.published_content_id
            ).first()

            results.append({
                "rank": rank,
                "published_content_id": str(content_summary.published_content_id),
                "title": content.title,
                "event_type": content_summary.event_type,
                "published_at": content_summary.published_at.isoformat(),
                "overall_engagement_rate": content_summary.overall_engagement_rate,
                "total_likes": content_summary.total_likes,
                "total_shares": content_summary.total_shares,
                "total_comments": content_summary.total_comments,
                "best_platform": content_summary.best_platform,
                "performance_percentile": self._calculate_percentile(content_summary.overall_engagement_rate)
            })

        return results

    def get_bottom_performers(self, limit: int = 10, period_days: int = 7) -> List[Dict]:
        """
        Answer: "Which posts underperformed?"

        Returns bottom performing posts to learn from
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        bottom_content = self.db.query(ContentPerformanceSummary).filter(
            ContentPerformanceSummary.published_at >= cutoff_date
        ).order_by(
            ContentPerformanceSummary.overall_engagement_rate.asc()
        ).limit(limit).all()

        results = []
        for content_summary in bottom_content:
            content = self.db.query(PublishedContent).filter_by(
                id=content_summary.published_content_id
            ).first()

            results.append({
                "published_content_id": str(content_summary.published_content_id),
                "title": content.title,
                "event_type": content_summary.event_type,
                "published_at": content_summary.published_at.isoformat(),
                "overall_engagement_rate": content_summary.overall_engagement_rate,
                "total_impressions": content_summary.total_impressions,
                "total_engagements": content_summary.total_engagements,
                "issue": self._diagnose_low_performance(content_summary)
            })

        return results

    def get_performance_by_event_type(self, period_days: int = 30) -> List[Dict]:
        """
        Answer: "What type of content gets most engagement?"

        Returns performance grouped by event type
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        # Aggregate by event type
        results = self.db.query(
            ContentPerformanceSummary.event_type,
            func.count(ContentPerformanceSummary.id).label("total_posts"),
            func.sum(ContentPerformanceSummary.total_impressions).label("total_impressions"),
            func.sum(ContentPerformanceSummary.total_engagements).label("total_engagements"),
            func.avg(ContentPerformanceSummary.overall_engagement_rate).label("avg_engagement_rate")
        ).filter(
            ContentPerformanceSummary.published_at >= cutoff_date
        ).group_by(
            ContentPerformanceSummary.event_type
        ).order_by(
            desc("avg_engagement_rate")
        ).all()

        formatted_results = []
        for result in results:
            formatted_results.append({
                "event_type": result.event_type,
                "total_posts": result.total_posts,
                "total_impressions": result.total_impressions,
                "total_engagements": result.total_engagements,
                "avg_engagement_rate": round(result.avg_engagement_rate, 2),
                "recommendation": self._get_event_type_recommendation(
                    result.event_type,
                    result.avg_engagement_rate
                )
            })

        return formatted_results

    def get_performance_by_platform(self, period_days: int = 30) -> List[Dict]:
        """
        Answer: "Which platform performs best?"

        Returns performance comparison across platforms
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        # Aggregate by platform
        results = self.db.query(
            Analytics.platform,
            func.count(Analytics.id).label("total_posts"),
            func.sum(Analytics.impressions).label("total_impressions"),
            func.sum(Analytics.total_engagements).label("total_engagements"),
            func.avg(Analytics.engagement_rate).label("avg_engagement_rate"),
            func.avg(Analytics.virality_score).label("avg_virality_score")
        ).filter(
            Analytics.metric_date >= cutoff_date
        ).group_by(
            Analytics.platform
        ).order_by(
            desc("avg_engagement_rate")
        ).all()

        formatted_results = []
        for result in results:
            formatted_results.append({
                "platform": result.platform,
                "total_posts": result.total_posts,
                "total_impressions": result.total_impressions,
                "total_engagements": result.total_engagements,
                "avg_engagement_rate": round(result.avg_engagement_rate, 2),
                "avg_virality_score": round(result.avg_virality_score, 2),
                "recommendation": self._get_platform_recommendation(
                    result.platform,
                    result.avg_engagement_rate
                )
            })

        return formatted_results

    def get_engagement_trends(self, period_days: int = 30) -> Dict:
        """
        Answer: "Is our engagement improving over time?"

        Returns daily engagement trends
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        # Get daily aggregates
        daily_results = self.db.query(
            Analytics.metric_date,
            func.sum(Analytics.impressions).label("impressions"),
            func.sum(Analytics.total_engagements).label("engagements"),
            func.avg(Analytics.engagement_rate).label("avg_engagement_rate")
        ).filter(
            Analytics.metric_date >= cutoff_date
        ).group_by(
            Analytics.metric_date
        ).order_by(
            Analytics.metric_date
        ).all()

        # Calculate trend (linear regression on engagement rate)
        dates = [r.metric_date for r in daily_results]
        rates = [r.avg_engagement_rate for r in daily_results]

        trend_direction = self._calculate_trend(rates)

        return {
            "period_days": period_days,
            "daily_data": [
                {
                    "date": str(r.metric_date),
                    "impressions": r.impressions,
                    "engagements": r.engagements,
                    "engagement_rate": round(r.avg_engagement_rate, 2)
                }
                for r in daily_results
            ],
            "trend": trend_direction,  # "growing", "declining", "stable"
            "trend_percentage": self._calculate_trend_percentage(rates),
            "recommendation": self._get_trend_recommendation(trend_direction)
        }

    # ===== Helper Methods =====

    def _calculate_percentile(self, engagement_rate: float) -> float:
        """Calculate what percentile this engagement rate is at"""
        total_content = self.db.query(ContentPerformanceSummary).count()
        better_content = self.db.query(ContentPerformanceSummary).filter(
            ContentPerformanceSummary.overall_engagement_rate > engagement_rate
        ).count()

        percentile = ((total_content - better_content) / total_content * 100) if total_content > 0 else 0
        return round(percentile, 1)

    def _diagnose_low_performance(self, content_summary: ContentPerformanceSummary) -> str:
        """Diagnose why a post underperformed"""
        if content_summary.total_impressions < 1000:
            return "Low reach - content didn't get enough impressions"
        elif content_summary.total_likes < 10:
            return "Low interest - content didn't resonate with audience"
        elif content_summary.total_shares == 0:
            return "Not shareable - content lacks viral potential"
        elif content_summary.total_comments == 0:
            return "Not thought-provoking - didn't inspire discussion"
        else:
            return "General low engagement - review content quality"

    def _get_event_type_recommendation(self, event_type: str, avg_engagement_rate: float) -> str:
        """Get recommendation based on event type performance"""
        if avg_engagement_rate > 3.0:
            return f"✅ {event_type} performs excellently - create more content like this"
        elif avg_engagement_rate > 2.0:
            return f"✓ {event_type} performs well - maintain current frequency"
        elif avg_engagement_rate > 1.0:
            return f"⚠ {event_type} performs below average - review content approach"
        else:
            return f"❌ {event_type} underperforms - consider reducing or improving"

    def _get_platform_recommendation(self, platform: str, avg_engagement_rate: float) -> str:
        """Get recommendation based on platform performance"""
        if avg_engagement_rate > 3.0:
            return f"✅ {platform.title()} is highly effective - prioritize this platform"
        elif avg_engagement_rate > 2.0:
            return f"✓ {platform.title()} performs well - maintain current strategy"
        else:
            return f"⚠ {platform.title()} underperforms - review posting strategy"

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate if values are growing, declining, or stable"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression slope
        x = list(range(len(values)))
        n = len(values)

        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x_i ** 2 for x_i in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

        if slope > 0.05:
            return "growing"
        elif slope < -0.05:
            return "declining"
        else:
            return "stable"

    def _calculate_trend_percentage(self, values: List[float]) -> float:
        """Calculate percentage change from first to last value"""
        if len(values) < 2:
            return 0.0

        first_val = values[0]
        last_val = values[-1]

        if first_val == 0:
            return 0.0

        percentage_change = ((last_val - first_val) / first_val) * 100
        return round(percentage_change, 1)

    def _get_trend_recommendation(self, trend: str) -> str:
        """Get recommendation based on engagement trend"""
        if trend == "growing":
            return "🚀 Engagement is growing - keep up the current content strategy"
        elif trend == "declining":
            return "📉 Engagement is declining - review and adjust content approach"
        else:
            return "➡️ Engagement is stable - consider experimenting with new content types"

    # ===== Export Methods =====

    def export_analytics_csv(self, period_days: int = 30) -> str:
        """Export analytics to CSV file"""
        import csv
        from io import StringIO

        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        content_summaries = self.db.query(ContentPerformanceSummary).filter(
            ContentPerformanceSummary.published_at >= cutoff_date
        ).order_by(
            desc(ContentPerformanceSummary.overall_engagement_rate)
        ).all()

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Rank",
            "Title",
            "Event Type",
            "Published At",
            "Total Impressions",
            "Total Likes",
            "Total Shares",
            "Total Comments",
            "Total Clicks",
            "Total Engagements",
            "Engagement Rate (%)",
            "Best Platform",
            "Virality Score (%)"
        ])

        # Data rows
        for rank, summary in enumerate(content_summaries, start=1):
            content = self.db.query(PublishedContent).filter_by(
                id=summary.published_content_id
            ).first()

            writer.writerow([
                rank,
                content.title,
                summary.event_type,
                summary.published_at.strftime("%Y-%m-%d %H:%M"),
                summary.total_impressions,
                summary.total_likes,
                summary.total_shares,
                summary.total_comments,
                summary.total_clicks,
                summary.total_engagements,
                round(summary.overall_engagement_rate, 2),
                summary.best_platform,
                round(summary.overall_virality_score, 2)
            ])

        return output.getvalue()
```

---

## Analytics Worker

### Background Worker for Automatic Sync

```python
# workers/analytics_worker.py

import asyncio
from datetime import datetime, timedelta
from typing import List
from database.session import get_db_session
from database.models import PublishedContent
from services.analytics_service import AnalyticsService

class AnalyticsWorker:
    """
    Background worker that syncs analytics from platforms

    Sync Schedule:
    - Content published <24h ago: sync every hour
    - Content published 1-7 days ago: sync every 6 hours
    - Content published >7 days ago: sync daily
    """

    def __init__(self):
        self.analytics_service = None
        self.running = False

    async def start(self):
        """Start the analytics worker"""
        self.running = True
        print("Analytics Worker started")

        while self.running:
            try:
                await self.sync_cycle()
            except Exception as e:
                print(f"Error in analytics worker: {e}")

            # Sleep for 1 hour before next cycle
            await asyncio.sleep(3600)

    async def sync_cycle(self):
        """Run one sync cycle"""
        db = next(get_db_session())
        self.analytics_service = AnalyticsService(db)

        print(f"[{datetime.utcnow()}] Analytics sync cycle started")

        # Get content that needs syncing
        content_to_sync = self._get_content_for_sync(db)

        print(f"Found {len(content_to_sync)} content items to sync")

        # Sync each content
        for content in content_to_sync:
            try:
                await self.analytics_service.sync_analytics(str(content.id))
                print(f"✓ Synced analytics for content {content.id}")
            except Exception as e:
                print(f"✗ Failed to sync content {content.id}: {e}")

        # Update event type performance summaries
        await self._update_event_type_summaries(db)

        print(f"[{datetime.utcnow()}] Analytics sync cycle completed")

        db.close()

    def _get_content_for_sync(self, db) -> List[PublishedContent]:
        """
        Determine which content needs analytics sync based on age
        """
        now = datetime.utcnow()

        # Content published in last 24 hours (sync every hour - happens automatically)
        recent_content = db.query(PublishedContent).filter(
            PublishedContent.published_at >= now - timedelta(hours=24)
        ).all()

        # Content published 1-7 days ago (sync every 6 hours)
        last_sync_cutoff_6h = now - timedelta(hours=6)
        week_old_content = db.query(PublishedContent).join(
            ContentPerformanceSummary
        ).filter(
            and_(
                PublishedContent.published_at >= now - timedelta(days=7),
                PublishedContent.published_at < now - timedelta(hours=24),
                ContentPerformanceSummary.last_synced_at < last_sync_cutoff_6h
            )
        ).all()

        # Content published >7 days ago (sync daily)
        last_sync_cutoff_24h = now - timedelta(hours=24)
        old_content = db.query(PublishedContent).join(
            ContentPerformanceSummary
        ).filter(
            and_(
                PublishedContent.published_at < now - timedelta(days=7),
                ContentPerformanceSummary.last_synced_at < last_sync_cutoff_24h
            )
        ).limit(50).all()  # Limit to 50 old posts per cycle

        return recent_content + week_old_content + old_content

    async def _update_event_type_summaries(self, db):
        """Update event type performance summaries"""
        # This would calculate and store event type performance
        # for various time periods (7 days, 30 days, all time)
        pass

    def stop(self):
        """Stop the analytics worker"""
        self.running = False
        print("Analytics Worker stopped")


# Run the worker
if __name__ == "__main__":
    worker = AnalyticsWorker()
    asyncio.run(worker.start())
```

---

## Dashboard UI Components

### Analytics Dashboard Layout

```typescript
// dashboard/src/pages/Analytics.tsx

import React, { useState, useEffect } from 'react';
import { LineChart, BarChart, PieChart } from 'recharts';
import { api } from '../services/api';

interface AnalyticsData {
  summary: SummaryMetrics;
  topPerformers: ContentPerformance[];
  bottomPerformers: ContentPerformance[];
  eventTypePerformance: EventTypeMetrics[];
  platformPerformance: PlatformMetrics[];
  trends: TrendData;
}

export function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [period, setPeriod] = useState(7); // Default 7 days
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const [summary, topPerformers, bottomPerformers, eventTypes, platforms, trends] = await Promise.all([
        api.get('/analytics/summary'),
        api.get(`/analytics/top-performers?limit=10&period=${period}d`),
        api.get(`/analytics/bottom-performers?limit=10&period=${period}d`),
        api.get(`/analytics/by-event-type?period=${period}d`),
        api.get('/analytics/by-platform'),
        api.get(`/analytics/trends?period=${period}d`)
      ]);

      setData({
        summary,
        topPerformers,
        bottomPerformers,
        eventTypePerformance: eventTypes,
        platformPerformance: platforms,
        trends
      });
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading analytics...</div>;
  }

  return (
    <div className="analytics-dashboard">
      {/* Period Selector */}
      <div className="period-selector">
        <button onClick={() => setPeriod(7)} className={period === 7 ? 'active' : ''}>
          Last 7 Days
        </button>
        <button onClick={() => setPeriod(30)} className={period === 30 ? 'active' : ''}>
          Last 30 Days
        </button>
        <button onClick={() => setPeriod(90)} className={period === 90 ? 'active' : ''}>
          Last 90 Days
        </button>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <SummaryCard
          title="Total Impressions"
          value={data.summary.total_impressions.toLocaleString()}
          trend={data.trends.trend}
        />
        <SummaryCard
          title="Total Engagements"
          value={data.summary.total_engagements.toLocaleString()}
          trend={data.trends.trend}
        />
        <SummaryCard
          title="Avg Engagement Rate"
          value={`${data.summary.avg_engagement_rate}%`}
          trend={data.trends.trend}
        />
        <SummaryCard
          title="Total Posts"
          value={data.summary.total_posts}
        />
      </div>

      {/* Top Performers Section */}
      <section className="top-performers">
        <h2>⭐ Top Performers</h2>
        <p className="subtitle">Most liked and engaged posts</p>
        <TopPerformersTable performers={data.topPerformers} />
      </section>

      {/* Bottom Performers Section */}
      <section className="bottom-performers">
        <h2>📉 Bottom Performers</h2>
        <p className="subtitle">Learn from low engagement</p>
        <BottomPerformersTable performers={data.bottomPerformers} />
      </section>

      {/* Event Type Performance */}
      <section className="event-type-performance">
        <h2>📊 Performance by Content Type</h2>
        <p className="subtitle">Which topics resonate most?</p>
        <EventTypeChart data={data.eventTypePerformance} />
      </section>

      {/* Platform Performance */}
      <section className="platform-performance">
        <h2>🌐 Performance by Platform</h2>
        <p className="subtitle">Which platform works best?</p>
        <PlatformChart data={data.platformPerformance} />
      </section>

      {/* Engagement Trends */}
      <section className="engagement-trends">
        <h2>📈 Engagement Trends</h2>
        <p className="subtitle">Is engagement growing or declining?</p>
        <TrendChart data={data.trends} />
      </section>

      {/* Export Button */}
      <button
        className="export-btn"
        onClick={() => exportAnalytics()}
      >
        Export to CSV
      </button>
    </div>
  );
}
```

### Top Performers Table Component

```typescript
// dashboard/src/components/TopPerformersTable.tsx

import React from 'react';
import { ContentPerformance } from '../types';

interface Props {
  performers: ContentPerformance[];
}

export function TopPerformersTable({ performers }: Props) {
  return (
    <table className="performers-table">
      <thead>
        <tr>
          <th>Rank</th>
          <th>Content</th>
          <th>Type</th>
          <th>Platform</th>
          <th>Likes</th>
          <th>Shares</th>
          <th>Comments</th>
          <th>Engagement Rate</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {performers.map((performer) => (
          <tr key={performer.published_content_id} className="performer-row">
            <td className="rank">
              {performer.rank === 1 ? '🥇' : performer.rank === 2 ? '🥈' : performer.rank === 3 ? '🥉' : performer.rank}
            </td>
            <td className="content-title">
              <div className="title">{performer.title}</div>
              <div className="metadata">
                {new Date(performer.published_at).toLocaleDateString()}
              </div>
            </td>
            <td>
              <span className="event-type-badge">{performer.event_type}</span>
            </td>
            <td>
              <span className={`platform-badge ${performer.best_platform}`}>
                {performer.best_platform}
              </span>
            </td>
            <td className="metric likes">
              ❤️ {performer.total_likes.toLocaleString()}
            </td>
            <td className="metric shares">
              🔄 {performer.total_shares.toLocaleString()}
            </td>
            <td className="metric comments">
              💬 {performer.total_comments.toLocaleString()}
            </td>
            <td className="metric engagement-rate">
              <span className="rate">{performer.overall_engagement_rate}%</span>
              <span className="percentile">Top {100 - performer.performance_percentile}%</span>
            </td>
            <td>
              <button onClick={() => viewDetails(performer.published_content_id)}>
                View Details
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## Platform API Integration Examples

### Twitter Analytics Fetching

```python
# integrations/twitter_api.py

import requests
from typing import Dict

class TwitterAPI:
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"

    async def get_tweet_metrics(self, tweet_id: str) -> Dict:
        """
        Fetch metrics for a specific tweet

        API Endpoint: GET /2/tweets/:id
        Required fields: public_metrics
        """
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }

        params = {
            "tweet.fields": "public_metrics,created_at",
            "expansions": "author_id"
        }

        response = requests.get(
            f"{self.base_url}/tweets/{tweet_id}",
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(f"Twitter API error: {response.text}")

        data = response.json()
        metrics = data["data"]["public_metrics"]

        return {
            "impression_count": metrics.get("impression_count", 0),
            "like_count": metrics.get("like_count", 0),
            "retweet_count": metrics.get("retweet_count", 0),
            "reply_count": metrics.get("reply_count", 0),
            "quote_count": metrics.get("quote_count", 0)
        }
```

### LinkedIn Analytics Fetching

```python
# integrations/linkedin_api.py

import requests
from typing import Dict

class LinkedInAPI:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.linkedin.com/v2"

    async def get_post_metrics(self, post_id: str) -> Dict:
        """
        Fetch metrics for a LinkedIn post

        API Endpoint: GET /organizationalEntityShareStatistics
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        params = {
            "q": "organizationalEntity",
            "organizationalEntity": post_id
        }

        response = requests.get(
            f"{self.base_url}/organizationalEntityShareStatistics",
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(f"LinkedIn API error: {response.text}")

        data = response.json()
        metrics = data["elements"][0]["totalShareStatistics"]

        return {
            "impressionCount": metrics.get("impressionCount", 0),
            "likeCount": metrics.get("likeCount", 0),
            "shareCount": metrics.get("shareCount", 0),
            "commentCount": metrics.get("commentCount", 0),
            "clickCount": metrics.get("clickCount", 0)
        }
```

### SendGrid Newsletter Analytics

```python
# integrations/sendgrid_api.py

import requests
from typing import Dict

class SendGridAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.sendgrid.com/v3"

    async def get_campaign_metrics(self, campaign_id: str) -> Dict:
        """
        Fetch metrics for a newsletter campaign

        API Endpoint: GET /campaigns/{campaign_id}/stats
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.get(
            f"{self.base_url}/campaigns/{campaign_id}/stats",
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"SendGrid API error: {response.text}")

        data = response.json()

        return {
            "sent": data.get("stats", {}).get("requests", 0),
            "opens": data.get("stats", {}).get("unique_opens", 0),
            "clicks": data.get("stats", {}).get("unique_clicks", 0),
            "bounces": data.get("stats", {}).get("bounces", 0),
            "spam_reports": data.get("stats", {}).get("spam_reports", 0)
        }
```

---

## Testing Strategy

### Unit Tests for Analytics Service

```python
# tests/test_analytics_service.py

import pytest
from services.analytics_service import AnalyticsService
from database.models import Analytics, PublishedContent, ContentPerformanceSummary

def test_calculate_engagement_rate():
    """Test engagement rate calculation"""
    service = AnalyticsService(db_session)

    # Test with valid values
    impressions = 10000
    likes = 250
    shares = 50
    comments = 20

    total_engagements = likes + shares + comments  # 320
    expected_rate = (320 / 10000) * 100  # 3.2%

    # Verify calculation
    assert service._calculate_engagement_rate(impressions, total_engagements) == expected_rate

def test_top_performers_query():
    """Test that top performers are correctly identified"""
    service = AnalyticsService(db_session)

    # Insert test data
    # Content A: 5% engagement rate
    # Content B: 3% engagement rate
    # Content C: 1% engagement rate

    top_performers = service.get_top_performers(limit=2)

    assert len(top_performers) == 2
    assert top_performers[0]["overall_engagement_rate"] > top_performers[1]["overall_engagement_rate"]
    assert top_performers[0]["rank"] == 1
    assert top_performers[1]["rank"] == 2

def test_event_type_performance():
    """Test event type performance aggregation"""
    service = AnalyticsService(db_session)

    # Insert test data with different event types
    # FINANCE_POLICY: avg 3.5% engagement
    # MARKET_MOVEMENT: avg 1.8% engagement

    results = service.get_performance_by_event_type()

    assert len(results) == 2
    assert results[0]["event_type"] == "FINANCE_POLICY"
    assert results[0]["avg_engagement_rate"] > results[1]["avg_engagement_rate"]
```

### Integration Tests

```python
# tests/test_analytics_integration.py

import pytest
from services.analytics_service import AnalyticsService
from integrations.twitter_api import TwitterAPI
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_sync_twitter_analytics():
    """Test syncing analytics from Twitter API"""
    service = AnalyticsService(db_session)

    # Mock Twitter API response
    mock_response = {
        "impression_count": 15000,
        "like_count": 450,
        "retweet_count": 120,
        "reply_count": 35,
        "quote_count": 10
    }

    with patch.object(TwitterAPI, 'get_tweet_metrics', return_value=mock_response):
        result = await service.sync_analytics(published_content_id)

        # Verify analytics were stored
        analytics = db_session.query(Analytics).filter_by(
            published_content_id=published_content_id,
            platform="twitter"
        ).first()

        assert analytics is not None
        assert analytics.impressions == 15000
        assert analytics.likes == 450
        assert analytics.shares == 120
        assert analytics.comments == 35
        assert analytics.engagement_rate > 0
```

---

## Success Metrics for Analytics Phase

### Must Pass ALL:

| Metric | Target | Validation |
|--------|--------|------------|
| **Data Coverage** | 100% of published content has analytics | Query database, verify no nulls |
| **Sync Accuracy** | Analytics match platform data (±5%) | Manual spot check 10 posts |
| **Top Performers** | Dashboard shows correct top 10 | Compare rankings manually |
| **Event Type Insights** | Correctly identifies best/worst types | Verify aggregation logic |
| **Platform Comparison** | Accurate comparison across platforms | Cross-reference with platform data |
| **Trend Detection** | Correctly identifies growing/declining trends | Verify with historical data |
| **Export Functionality** | CSV export contains all data | Open CSV, verify completeness |
| **Worker Reliability** | Analytics worker runs without errors for 7 days | Check logs daily |

---

## MVP Exit Criteria (Analytics-Focused)

**Before proceeding to Scale Phase, we MUST be able to answer:**

1. ✅ **Which 10 posts got the most likes/engagement this month?**
2. ✅ **Which event type (Policy, Market, Macro) gets best engagement?**
3. ✅ **Which platform (Twitter, LinkedIn, Newsletter) performs best?**
4. ✅ **Is our overall engagement growing or declining?**
5. ✅ **What time of day gets most engagement?**
6. ✅ **Why did low-performing posts underperform?**
7. ✅ **What patterns exist in high-performing content?**

**If we can't answer these questions with data, MVP is not complete.**

---

*Created on: January 21, 2026*
*Version: 1.0*
*Status: Ready for Implementation*
