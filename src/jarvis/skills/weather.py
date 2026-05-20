"""
Weather skill for Jarvis.
Uses wttr.in — no API key required.
"""
import logging
import re

logger = logging.getLogger("jarvis.skills.weather")

WEATHER_KEYWORDS = [
    "weather", "temperature", "forecast", "rain", "snow", "sunny",
    "humidity", "wind", "hot", "cold", "outside", "degrees"
]


def handle(query: str, default_location: str = "auto") -> str | None:
    """Return weather context if query is weather-related, else None."""
    q = query.lower()
    if not any(kw in q for kw in WEATHER_KEYWORDS):
        return None

    location = _extract_location(query) or default_location
    return _get_weather(location)


def _extract_location(query: str) -> str | None:
    """Try to extract a location from the query."""
    patterns = [
        r"weather (?:in|at|for) ([A-Za-z\s,]+?)(?:\?|$)",
        r"(?:in|at) ([A-Za-z\s]+?) (?:weather|forecast|temperature)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _get_weather(location: str) -> str:
    """Fetch weather from wttr.in."""
    try:
        import httpx

        # Use wttr.in JSON API
        url = f"https://wttr.in/{location}?format=j1"
        r = httpx.get(url, timeout=5, follow_redirects=True)
        r.raise_for_status()
        data = r.json()

        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        city = area["areaName"][0]["value"]
        country = area["country"][0]["value"]

        temp_f = current["temp_F"]
        temp_c = current["temp_C"]
        feels_f = current["FeelsLikeF"]
        desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        wind_mph = current["windspeedMiles"]
        wind_dir = current["winddir16Point"]

        # Today's high/low
        today = data["weather"][0]
        max_f = today["maxtempF"]
        min_f = today["mintempF"]

        return (
            f"Weather for {city}, {country}: {desc}. "
            f"Currently {temp_f}°F ({temp_c}°C), feels like {feels_f}°F. "
            f"High of {max_f}°F, low of {min_f}°F today. "
            f"Humidity {humidity}%, winds {wind_mph} mph from the {wind_dir}. "
            f"Use this data to answer the weather question naturally in character."
        )
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
        return (
            "Weather service is currently unavailable. "
            "Tell the user you're unable to retrieve weather data at the moment."
        )
