"""
Internet skill for Jarvis.
- DuckDuckGo web search (no API key required)
- Web page reader + summarizer
- Wikipedia quick lookup
- Live news headlines
"""
import logging
import re
from typing import Optional

logger = logging.getLogger("jarvis.skills.internet")

SEARCH_TRIGGERS = [
    "search", "look up", "find", "google", "what is", "what are",
    "who is", "who are", "where is", "when did", "how do", "how does",
    "tell me about", "news", "latest", "current", "today", "read",
    "open", "fetch", "get me", "show me", "explain",
]

WIKI_TRIGGERS = ["wikipedia", "wiki ", "define ", "definition of", "who invented", "history of"]
NEWS_TRIGGERS  = ["news", "headlines", "latest news", "what's happening", "current events"]
URL_PATTERN    = re.compile(r"https?://[^\s]+|www\.[^\s]+")


def handle(query: str) -> Optional[str]:
    """Route internet queries. Returns context string for the LLM."""
    q = query.lower().strip()

    # Direct URL read
    url_match = URL_PATTERN.search(query)
    if url_match:
        return _read_page(url_match.group(0))

    # Wikipedia
    if any(t in q for t in WIKI_TRIGGERS):
        topic = _strip_triggers(q, WIKI_TRIGGERS + ["what is", "who is", "define"])
        return _wiki_lookup(topic)

    # News
    if any(t in q for t in NEWS_TRIGGERS):
        topic = _strip_triggers(q, NEWS_TRIGGERS + ["give me", "show me", "latest", "get me"])
        return _get_news(topic.strip() or "top news")

    # General search
    if any(t in q for t in SEARCH_TRIGGERS):
        topic = _strip_triggers(q, SEARCH_TRIGGERS + ["please", "can you", "could you"])
        return _web_search(topic.strip() or query)

    return None


# ── DuckDuckGo Search ─────────────────────────────────────────────────────────

def _web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo. No API key needed."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"• {r['title']}: {r['body']}")
        if not results:
            return f"No results found for '{query}'. Inform user."
        summary = "\n".join(results)
        return (
            f"Web search results for '{query}':\n{summary}\n\n"
            f"Use these results to answer the question naturally in Jarvis character. "
            f"Cite sources when relevant. Keep response concise and spoken-word friendly."
        )
    except ImportError:
        return _ddg_fallback(query)
    except Exception as e:
        logger.error(f"DDG search error: {e}")
        return f"Web search temporarily unavailable. Inform sir politely."


def _get_news(topic: str = "top news", max_results: int = 5) -> str:
    """Get live news headlines via DuckDuckGo News."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(topic, max_results=max_results):
                results.append(f"• {r['title']} ({r.get('source', 'unknown')}): {r.get('body', '')[:120]}")
        if not results:
            return f"No news found for '{topic}'."
        summary = "\n".join(results)
        return (
            f"Latest news on '{topic}':\n{summary}\n\n"
            f"Summarize these headlines naturally and concisely in Jarvis character."
        )
    except ImportError:
        return _ddg_fallback(f"news {topic}")
    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return "News service unavailable. Inform sir."


# ── Wikipedia ─────────────────────────────────────────────────────────────────

def _wiki_lookup(topic: str) -> str:
    """Fetch Wikipedia summary."""
    try:
        import httpx
        topic_clean = topic.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic_clean}"
        r = httpx.get(url, timeout=8, follow_redirects=True,
                      headers={"User-Agent": "Jarvis-AI/1.0"})
        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract", "")[:1200]
            title   = data.get("title", topic)
            return (
                f"Wikipedia — {title}:\n{extract}\n\n"
                f"Use this to answer the question naturally. Be concise."
            )
        elif r.status_code == 404:
            return _web_search(topic)  # Fall back to web search
        else:
            return _web_search(topic)
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        return _web_search(topic)


# ── Web Page Reader ───────────────────────────────────────────────────────────

def _read_page(url: str, max_chars: int = 2000) -> str:
    """Fetch and extract readable text from a URL."""
    try:
        import httpx
        from bs4 import BeautifulSoup

        if not url.startswith("http"):
            url = f"https://{url}"

        r = httpx.get(url, timeout=10, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; Jarvis/1.0)"})
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        # Get main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        text = main.get_text(separator=" ", strip=True) if main else soup.get_text()
        text = re.sub(r"\s{2,}", " ", text).strip()[:max_chars]

        return (
            f"Content from {url}:\n{text}\n\n"
            f"Summarize or answer based on this content. Stay in character."
        )
    except ImportError:
        return f"Page reading requires beautifulsoup4. Run: pip install beautifulsoup4"
    except Exception as e:
        logger.error(f"Page read error: {e}")
        return f"Unable to fetch that page, sir. Error: {str(e)[:80]}"


# ── Fallback ──────────────────────────────────────────────────────────────────

def _ddg_fallback(query: str) -> str:
    """Fallback when duckduckgo_search not installed."""
    import webbrowser
    search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
    webbrowser.open(search_url)
    return f"duckduckgo-search package not installed. Opened browser search for '{query}'. Inform user."


def _strip_triggers(text: str, triggers: list) -> str:
    """Remove trigger words from query to get the core topic."""
    result = text.lower()
    # Sort by length descending so longer phrases match first
    for t in sorted(triggers, key=len, reverse=True):
        result = result.replace(t, "")
    return result.strip(" ?,.")
