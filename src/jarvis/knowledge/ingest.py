"""
Jarvis knowledge ingestion CLI + helper.
Run standalone: python -m jarvis.knowledge.ingest <path_or_url>
Or invoked by Jarvis when user says "learn about / train on / remember this".
"""
import sys
import argparse
import logging
from pathlib import Path

logger = logging.getLogger("jarvis.ingest")


INGEST_TRIGGERS = [
    "learn about", "train on", "remember this", "memorize", "ingest",
    "read and remember", "add to your knowledge", "study", "know about",
    "add this to memory", "save this", "remember that",
]


def handle_ingest_command(query: str, kb) -> str | None:
    """Called from Jarvis core when user wants to teach Jarvis something."""
    q = query.lower().strip()
    if not any(t in q for t in INGEST_TRIGGERS):
        return None

    # Extract URL or file path from query
    import re
    url_match = re.search(r"https?://[^\s]+|www\.[^\s]+", query)
    path_match = re.search(r"[A-Za-z]:\\[^\s]+|/[^\s]+\.\w+", query)

    if url_match:
        url = url_match.group(0)
        n = kb.ingest_url(url)
        return f"Ingested URL '{url}': {n} chunks indexed. Confirm in character."

    if path_match:
        path = Path(path_match.group(0))
        if path.is_dir():
            n = kb.ingest_folder(path)
        else:
            n = kb.ingest_file(path)
        return f"Ingested '{path.name}': {n} chunks. Confirm in character."

    # No URL or path — ingest the rest of the query as raw text
    text_to_remember = query
    for t in INGEST_TRIGGERS:
        text_to_remember = text_to_remember.lower().replace(t, "")
    text_to_remember = text_to_remember.strip(" :.,")
    if len(text_to_remember) > 10:
        n = kb.ingest_text(text_to_remember, source="conversation")
        return f"Noted and stored to knowledge base: {n} chunks. Confirm in character."

    return None


def main():
    parser = argparse.ArgumentParser(description="Ingest content into Jarvis knowledge base")
    parser.add_argument("source", nargs="*", help="File path, folder, or URL to ingest")
    parser.add_argument("--text", help="Ingest raw text string")
    parser.add_argument("--clear", action="store_true", help="Clear the entire knowledge base")
    parser.add_argument("--stats", action="store_true", help="Show knowledge base statistics")
    parser.add_argument("--db", help="Path to knowledge base (default: ~/.jarvis/knowledge)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from jarvis.knowledge.base import KnowledgeBase

    kb = KnowledgeBase(db_path=args.db)

    if args.stats:
        stats = kb.stats()
        print(f"\nKnowledge Base Stats:")
        print(f"  Ready:    {stats['ready']}")
        print(f"  Chunks:   {stats.get('chunks', 0)}")
        print(f"  Location: {stats.get('db_path', 'N/A')}")
        print(f"  Model:    {stats.get('embed_model', 'N/A')}")
        return

    if args.clear:
        confirm = input("Clear all knowledge? This cannot be undone. [y/N] ")
        if confirm.lower() == "y":
            kb.clear()
            print("Knowledge base cleared.")
        return

    if args.text:
        n = kb.ingest_text(args.text, source="manual")
        print(f"Ingested text: {n} chunks added.")
        return

    total = 0
    for source in args.source:
        if source.startswith("http"):
            print(f"Fetching URL: {source}")
            n = kb.ingest_url(source)
        elif Path(source).is_dir():
            print(f"Scanning folder: {source}")
            n = kb.ingest_folder(source)
        else:
            print(f"Reading file: {source}")
            n = kb.ingest_file(source)
        print(f"  → {n} chunks indexed.")
        total += n

    print(f"\nTotal: {total} chunks added to knowledge base.")


if __name__ == "__main__":
    main()
