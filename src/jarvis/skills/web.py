"""
Web search and browser skill for Jarvis.
"""
import logging
import re
import webbrowser

logger = logging.getLogger("jarvis.skills.web")

SEARCH_KEYWORDS = [
    "search", "look up", "find", "google", "what is", "who is",
    "tell me about", "news", "latest", "open", "go to", "browse"
]


def handle(query: str) -> str | None:
    """Handle web-related queries."""
    q = query.lower()

    # URL detection
    url_match = re.search(r"(https?://[^\s]+|www\.[^\s]+)", query, re.IGNORECASE)
    if url_match or any(phrase in q for phrase in ["go to", "open ", "navigate to"]):
        url = url_match.group(0) if url_match else _extract_site(query)
        if url:
            return _open_url(url)

    if not any(kw in q for kw in SEARCH_KEYWORDS):
        return None

    return _search(query)


def _extract_site(query: str) -> str | None:
    """Try to extract a website name and build URL."""
    match = re.search(r"(?:open|go to|navigate to|browse to)\s+([a-zA-Z0-9\-\.]+)", query, re.IGNORECASE)
    if match:
        site = match.group(1).strip()
        if "." not in site:
            site = f"{site}.com"
        if not site.startswith("http"):
            site = f"https://{site}"
        return site
    return None


def _open_url(url: str) -> str:
    """Open a URL in the default browser."""
    if not url.startswith("http"):
        url = f"https://{url}"
    try:
        webbrowser.open(url)
        return f"Opening {url} in the browser now. Confirm to the user."
    except Exception as e:
        return f"Could not open URL: {e}"


def _search(query: str) -> str:
    """Perform a web search and open results."""
    try:
        # Extract the actual search terms
        search_term = _clean_search_query(query)
        search_url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
        webbrowser.open(search_url)
        return (
            f"Searching Google for '{search_term}'. Browser opened. "
            f"Inform the user that results are now open in their browser."
        )
    except Exception as e:
        return f"Search failed: {e}"


def _clean_search_query(query: str) -> str:
    """Strip command words from query to get the search term."""
    remove_phrases = [
        "search for", "search", "look up", "find", "google",
        "what is", "who is", "tell me about", "can you search for"
    ]
    result = query.lower()
    for phrase in remove_phrases:
        result = result.replace(phrase, "")
    return result.strip()
