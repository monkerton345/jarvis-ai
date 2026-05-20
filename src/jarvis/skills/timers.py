"""
Timer and reminder skill for Jarvis.
"""
import logging
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger("jarvis.skills.timers")

TIMER_KEYWORDS = [
    "timer", "remind", "alarm", "set a", "in ", "minutes", "seconds",
    "hours", "reminder", "alert", "notify", "don't forget"
]

_active_timers: dict[str, threading.Timer] = {}
_on_speak: Optional[Callable] = None


def set_speak_callback(fn: Callable):
    """Set the function to call when timer fires (Jarvis speaks the alert)."""
    global _on_speak
    _on_speak = fn


def handle(query: str) -> str | None:
    """Handle timer/reminder requests."""
    q = query.lower()
    if not any(kw in q for kw in TIMER_KEYWORDS):
        return None

    # Cancel timer
    if "cancel" in q or "stop" in q:
        return _cancel_timers(query)

    # List timers
    if "list" in q or "active" in q or "how many" in q:
        return _list_timers()

    # Parse duration
    duration, label = _parse_timer(query)
    if duration:
        return _set_timer(duration, label)

    return None


def _parse_timer(query: str) -> tuple[Optional[int], str]:
    """Parse duration in seconds from query. Returns (seconds, label)."""
    total_seconds = 0

    patterns = [
        (r"(\d+)\s*hour", 3600),
        (r"(\d+)\s*minute", 60),
        (r"(\d+)\s*second", 1),
        (r"(\d+)\s*min", 60),
        (r"(\d+)\s*sec", 1),
        (r"(\d+)\s*hr", 3600),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            total_seconds += int(match.group(1)) * multiplier

    # Extract label (what the timer is for)
    label_match = re.search(r"(?:for|remind me (?:to|about))\s+(.+?)(?:\s+in\s+|\s+after\s+|$)", query, re.IGNORECASE)
    label = label_match.group(1).strip() if label_match else "your timer"

    return (total_seconds if total_seconds > 0 else None, label)


def _set_timer(seconds: int, label: str) -> str:
    """Set a timer that calls back via Jarvis voice."""
    timer_id = f"timer_{len(_active_timers) + 1}"

    def _fire():
        message = f"Sir, {label}. Your timer has elapsed."
        logger.info(f"Timer fired: {label}")
        _active_timers.pop(timer_id, None)
        if _on_speak:
            _on_speak(message)
        else:
            print(f"\n[JARVIS ALERT] {message}\n")

    t = threading.Timer(seconds, _fire)
    t.daemon = True
    t.start()
    _active_timers[timer_id] = t

    # Format duration for response
    parts = []
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h: parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m: parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if s: parts.append(f"{s} second{'s' if s != 1 else ''}")
    duration_str = " and ".join(parts)

    fires_at = (datetime.now() + timedelta(seconds=seconds)).strftime("%I:%M %p")

    return (
        f"Timer set for {duration_str} (fires at {fires_at}) for: {label}. "
        f"Confirm this to the user in character."
    )


def _cancel_timers(query: str) -> str:
    """Cancel active timers."""
    if not _active_timers:
        return "No active timers to cancel. Inform the user."

    for timer_id, t in list(_active_timers.items()):
        t.cancel()
        _active_timers.pop(timer_id)

    return f"Cancelled {len(_active_timers)} timer(s). Confirm to user."


def _list_timers() -> str:
    if not _active_timers:
        return "No active timers. Inform the user."
    return f"{len(_active_timers)} active timer(s) running. Inform the user."
