"""Smart Scheduling Service with Anti-Bot Detection Features.

This service schedules tweets with human-like patterns to avoid Twitter bot detection:
- Time randomization (±15-30 minutes)
- Variable gaps between posts (1.5-3.5 hours)
- Daily variation (3-6 posts/day)
- Weekend behavior (reduced activity)
- Occasional skip days (15% probability)
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo


class SmartScheduler:
    """Human-like tweet scheduling to avoid bot detection."""

    # Timezone
    IST = ZoneInfo("Asia/Kolkata")

    # Configuration
    MIN_POSTS_PER_DAY = 3
    MAX_POSTS_PER_DAY = 8
    WEEKEND_REDUCTION = 2 

    MIN_GAP_HOURS = 1.5
    MAX_GAP_HOURS = 3.5

    MIN_TIME_JITTER_MINUTES = -15
    MAX_TIME_JITTER_MINUTES = 30

    SKIP_DAY_PROBABILITY = 0.15  # 15% chance to skip a day

    # Optimal time windows (IST) - when audience is most active
    TIME_WINDOWS = [
        ("08:00", "10:00"),  # Morning window (best engagement)
        ("12:00", "13:00"),  # Lunch window
        ("17:00", "19:00"),  # Evening window (good engagement)
    ]

    def __init__(self):
        """Initialize the smart scheduler."""
        pass

    def get_last_tweet_time(self, db) -> Optional[datetime]:
        """
        Get the most recent tweet time (published or scheduled).

        This ensures incremental scheduling - new tweets are scheduled AFTER
        existing ones, not reset to tomorrow.

        Args:
            db: Database session

        Returns:
            Most recent datetime (published_at or scheduled_for), or None if no tweets
        """
        from database.models import ContentQueue

        # Query for most recent published tweet
        last_published = (
            db.query(ContentQueue.published_at)
            .filter(ContentQueue.published_at.isnot(None))
            .order_by(ContentQueue.published_at.desc())
            .first()
        )

        # Query for most recent scheduled tweet
        last_scheduled = (
            db.query(ContentQueue.scheduled_for)
            .filter(ContentQueue.scheduled_for.isnot(None))
            .filter(ContentQueue.status == "scheduled")
            .order_by(ContentQueue.scheduled_for.desc())
            .first()
        )

        # Find the most recent of the two
        times = []
        if last_published and last_published[0]:
            times.append(last_published[0])
        if last_scheduled and last_scheduled[0]:
            times.append(last_scheduled[0])

        if not times:
            return None

        # Return the most recent time (ensure timezone-aware)
        most_recent = max(times)

        # Database stores naive IST timestamps - just add IST timezone info
        if most_recent.tzinfo is None:
            most_recent = most_recent.replace(tzinfo=self.IST)

        return most_recent

    def should_skip_day(self, date: datetime) -> bool:
        """
        Determine if we should skip posting on this day (human-like behavior).

        Args:
            date: The date to check

        Returns:
            True if should skip, False otherwise
        """
        # Random skip with probability
        if random.random() < self.SKIP_DAY_PROBABILITY:
            return True

        return False

    def get_posts_for_day(self, date: datetime, available_count: int) -> int:
        """
        Determine how many posts to schedule for a given day.

        Args:
            date: The date to schedule for
            available_count: How many items are available to post

        Returns:
            Number of posts to schedule (randomized, human-like)
        """
        # Check if should skip day
        if self.should_skip_day(date):
            return 0

        # Base posts: random between min and max
        posts = random.randint(self.MIN_POSTS_PER_DAY, self.MAX_POSTS_PER_DAY)

        # Reduce on weekends (human behavior)
        if date.weekday() >= 5:  # Saturday=5, Sunday=6
            posts = max(1, posts - self.WEEKEND_REDUCTION)

        # Cap at available items
        posts = min(posts, available_count)

        return posts

    def generate_random_time_in_window(self, window: tuple) -> datetime:
        """
        Generate a random time within a time window.

        Args:
            window: Tuple of (start_time, end_time) as "HH:MM" strings

        Returns:
            Random datetime within the window
        """
        start_str, end_str = window

        # Parse times
        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))

        # Convert to minutes since midnight
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Random time in range
        random_minutes = random.randint(start_minutes, end_minutes)

        # Convert back to hours and minutes
        hour = random_minutes // 60
        minute = random_minutes % 60

        # Create datetime (date will be set by caller)
        return datetime.now(self.IST).replace(hour=hour, minute=minute, second=0, microsecond=0)

    def add_time_jitter(self, time: datetime) -> datetime:
        """
        Add random jitter to a time (±15-30 minutes) for human-like variation.

        Args:
            time: Base time

        Returns:
            Time with random jitter applied
        """
        jitter_minutes = random.randint(self.MIN_TIME_JITTER_MINUTES, self.MAX_TIME_JITTER_MINUTES)
        return time + timedelta(minutes=jitter_minutes)

    def schedule_for_day(self, date: datetime, items_count: int) -> List[datetime]:
        """
        Generate a schedule for a single day with human-like patterns.

        Args:
            date: The date to schedule for
            items_count: Number of items available to schedule

        Returns:
            List of scheduled times with randomization applied
        """
        # Determine how many posts for this day
        posts_today = self.get_posts_for_day(date, items_count)

        if posts_today == 0:
            return []

        scheduled_times = []

        # Distribute posts across time windows
        for i in range(posts_today):
            # Pick a random time window
            window = random.choice(self.TIME_WINDOWS)

            # Generate random time in that window
            base_time = self.generate_random_time_in_window(window)

            # Set the correct date
            base_time = base_time.replace(year=date.year, month=date.month, day=date.day)

            # Add jitter for humanization
            scheduled_time = self.add_time_jitter(base_time)

            scheduled_times.append(scheduled_time)

        # Sort by time
        scheduled_times.sort()

        # Ensure minimum gaps between posts (anti-bot)
        adjusted_times = []
        last_time = None

        for time in scheduled_times:
            if last_time:
                # Calculate gap from last post
                min_gap = timedelta(hours=self.MIN_GAP_HOURS)

                if time - last_time < min_gap:
                    # Adjust time to maintain minimum gap
                    time = last_time + min_gap + timedelta(minutes=random.randint(0, 30))

            adjusted_times.append(time)
            last_time = time

        return adjusted_times

    def schedule_items(
        self,
        items: List[Dict],
        start_date: Optional[datetime] = None,
        days: int = 7,
        db=None
    ) -> List[Dict]:
        """
        Schedule items across multiple days with smart randomization.

        CRITICAL: Schedules INCREMENTALLY after last published/scheduled tweet.
        Does NOT reset to tomorrow unless no tweets exist.

        Args:
            items: List of items to schedule (each with 'id' field)
            start_date: Start date (optional - overrides auto-detection)
            days: Number of days to spread items across
            db: Database session (required for incremental scheduling)

        Returns:
            List of scheduled items with 'scheduled_for' datetimes
        """
        if not items:
            return []

        # INCREMENTAL SCHEDULING: Start after last tweet
        if start_date is None:
            if db:
                last_tweet_time = self.get_last_tweet_time(db)
                if last_tweet_time:
                    # Start AFTER last tweet with minimum gap
                    start_date = last_tweet_time + timedelta(hours=self.MIN_GAP_HOURS)
                    print(f"[SmartScheduler] Last tweet: {last_tweet_time.strftime('%Y-%m-%d %H:%M IST')}")
                    print(f"[SmartScheduler] Starting new schedule from: {start_date.strftime('%Y-%m-%d %H:%M IST')}")
                else:
                    # No tweets yet - start tomorrow
                    start_date = (datetime.now(self.IST) + timedelta(days=1)).replace(
                        hour=8, minute=0, second=0, microsecond=0
                    )
                    print(f"[SmartScheduler] No existing tweets - starting from tomorrow morning")
            else:
                # No DB provided - default to tomorrow
                start_date = (datetime.now(self.IST) + timedelta(days=1)).replace(
                    hour=8, minute=0, second=0, microsecond=0
                )

        # Safety check: Don't schedule in the past
        now = datetime.now(self.IST)
        is_asap_mode = False
        if start_date < now:
            # Calculate how far behind schedule we are
            gap_hours = (now - start_date).total_seconds() / 3600

            if gap_hours > 6:
                # Way behind schedule (> 6 hours) - catch up ASAP (2-5 minutes)
                start_date = now + timedelta(minutes=random.randint(2, 5))
                is_asap_mode = True  # Flag to disable heavy jitter
                print(f"[SmartScheduler] {gap_hours:.1f}h gap detected - scheduling ASAP: {start_date.strftime('%Y-%m-%d %H:%M IST')}")
            else:
                # Small gap - use normal minimum gap
                start_date = now + timedelta(hours=self.MIN_GAP_HOURS)
                print(f"[SmartScheduler] Adjusted start_date to avoid past: {start_date.strftime('%Y-%m-%d %H:%M IST')}")

        scheduled_items = []
        remaining_items = list(items)
        current_time = start_date
        max_end_date = start_date + timedelta(days=days)

        # INCREMENTAL SCHEDULING: Schedule items sequentially with gaps
        for i, item in enumerate(remaining_items):
            # For first item, use start_date directly (no additional gap)
            # For subsequent items, add random gap from previous post
            if i > 0:
                gap_hours = random.uniform(self.MIN_GAP_HOURS, self.MAX_GAP_HOURS)
                current_time = current_time + timedelta(hours=gap_hours)

            # Add jitter for human-like variation
            # In ASAP mode (catching up), use minimal jitter (0-1 min) instead of standard (-15 to +30 min)
            if is_asap_mode and i == 0:
                # First item in ASAP mode: minimal jitter (0-60 seconds)
                jitter_seconds = random.randint(0, 60)
                scheduled_time = current_time + timedelta(seconds=jitter_seconds)
            else:
                # Normal jitter for all other cases
                scheduled_time = self.add_time_jitter(current_time)

            # Skip dead night hours (1 AM - 5 AM only) - move to morning
            if 1 <= scheduled_time.hour < 5:
                # Move to same day at 5 AM (or next day if already past)
                scheduled_time = scheduled_time.replace(hour=5, minute=0, second=0, microsecond=0)
                # Add jitter to morning time
                scheduled_time = self.add_time_jitter(scheduled_time)

            # Safety check: Don't schedule beyond max days
            if scheduled_time > max_end_date:
                print(f"[SmartScheduler] Warning: Stopping at item {len(scheduled_items)}/{len(items)} - would exceed {days} day limit")
                break

            scheduled_items.append({
                "id": item.get("id"),
                "content_queue_id": item.get("content_queue_id"),
                "scheduled_for": scheduled_time,
                "content_preview": item.get("content_text", "")[:100] + "...",
            })

            # Update current_time for next iteration
            current_time = scheduled_time

        return scheduled_items

    def suggest_optimal_time(self, event_type: Optional[str] = None) -> Dict:
        """
        Suggest an optimal time to post based on event type and best practices.

        Args:
            event_type: Type of event (FINANCE_POLICY, MACRO_ECONOMIC, etc.)

        Returns:
            Dict with suggested window and reasoning
        """
        # Morning is best for financial news (when people check markets)
        if event_type in ["FINANCE_POLICY", "MACRO_ECONOMIC"]:
            window = ("08:00", "10:00")
            reason = "Financial news gets highest engagement in morning hours when people check market updates"
        else:
            # Default to morning or lunch
            window = random.choice([("08:00", "10:00"), ("12:00", "13:00")])
            reason = "Morning and lunch hours show best engagement for general finance content"

        # Generate a time with jitter
        base_time = self.generate_random_time_in_window(window)
        suggested_time = self.add_time_jitter(base_time)

        return {
            "suggested_time": suggested_time,
            "window": f"{window[0]}-{window[1]} IST",
            "reason": reason,
            "note": "Time includes ±15-30 min randomization to avoid bot detection"
        }

    def get_next_available_slot(self, after: Optional[datetime] = None) -> datetime:
        """
        Get the next available posting slot with randomization.

        Args:
            after: Get slot after this time (defaults to now)

        Returns:
            Next available datetime with jitter
        """
        if after is None:
            after = datetime.now(self.IST)

        # Add minimum gap
        next_slot = after + timedelta(hours=self.MIN_GAP_HOURS)

        # Add random gap
        random_gap = random.uniform(0, self.MAX_GAP_HOURS - self.MIN_GAP_HOURS)
        next_slot = next_slot + timedelta(hours=random_gap)

        # Add jitter
        next_slot = self.add_time_jitter(next_slot)

        # If it's dead of night (1-5 AM), move to 5 AM same day
        if 1 <= next_slot.hour < 5:
            next_slot = next_slot.replace(hour=5, minute=0, second=0, microsecond=0)
            next_slot = self.add_time_jitter(next_slot)

        return next_slot
