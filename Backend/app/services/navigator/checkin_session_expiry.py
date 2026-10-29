"""Helpers for calculating patient check-in session expiry."""

from datetime import datetime, timedelta


def calculate_session_expiry(scheduled_at: datetime, expiry_after_hours: int | None) -> datetime | None:
    """Return the configured expiry time, or None when no expiry is configured."""
    if not expiry_after_hours or expiry_after_hours <= 0:
        return None
    return scheduled_at + timedelta(hours=expiry_after_hours)
