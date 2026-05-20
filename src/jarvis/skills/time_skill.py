"""
Time and date skill for Jarvis.
"""
from datetime import datetime
import re


def handle(query: str) -> str | None:
    """Return time/date context string if query is time-related, else None."""
    q = query.lower()
    time_keywords = ["time", "date", "day", "today", "what's", "clock", "hour", "month", "year"]
    if not any(kw in q for kw in time_keywords):
        return None

    now = datetime.now()
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p").lstrip("0")

    return (
        f"Current date and time: {day_name}, {date_str} at {time_str}. "
        f"Use this when answering questions about time or date."
    )
