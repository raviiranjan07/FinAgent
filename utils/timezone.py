"""Timezone utilities for FinAgent - IST (Indian Standard Time) only."""

from datetime import datetime, timezone, timedelta


# IST = UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    """
    Get current time in IST (Indian Standard Time).

    Returns a NAIVE datetime (no timezone info) representing IST time.
    This ensures PostgreSQL stores the value as-is without UTC conversion.

    Returns:
        datetime: Current IST time as naive datetime
    """
    # Get current IST time, then strip timezone info so PostgreSQL stores it directly
    return datetime.now(IST).replace(tzinfo=None)


def to_ist(dt: datetime) -> datetime:
    """
    Convert a datetime to IST timezone.

    Args:
        dt: Datetime object (can be naive or aware)

    Returns:
        datetime: Datetime converted to IST timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is already IST, just add timezone
        return dt.replace(tzinfo=IST)
    else:
        # Convert from other timezone to IST
        return dt.astimezone(IST)
