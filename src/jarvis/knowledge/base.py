"""
Jarvis Knowledge Base — RAG (Retrieval Augmented Generation).

Jarvis can be "trained" on any content:
  - Local files (PDF, TXT, DOCX, MD, code)
  - Web pages / URLs
  - Plain text snippets
  - Entire folders of documents

Uses ChromaDB (local vector DB) + sentence-transformers for embeddings.
Everything runs 100% offline after setup.
"""
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.knowledge")

DEFAULT_DB_PATH = Path.home() / ".jarvis" / "knowledge"
EMBED_MODEL = "all-MiniLM-L6-v2"   # Small, fast, ~80MB, runs on CPU
CHUNK_SIZE  = 500                   # Characters per chunk
CHUNK_OVERLAP = 50


class KnowledgeBase:
    """
    Persistent vector knowledge base for Jarvis.
    Supports ingestion of documents, URLs, and text snippets.
    Queried automatically during every conversation turn.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._collection = None
        self._embedder   = None
        self._ready      = False
        self._init()

    def _init(self):
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = client.get_or_create_collection(
                name="jarvis_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            self._load_embedder()
            self._ready = True
            count = self._collection.count()
            logger.info(f"Knowledge base ready — {count} chunks indexed at {self.db_path}")
        except ImportError:
            logger.warning("chromadb not installed — knowledge base disabled. Run: pip install chromadb")
        except Exception as e:
            logger.error(f"Knowledge base init error: {e}")

    def _load_embedder(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(EMBED_MODEL)
            logger.info(f"Embedder loaded: {EMBED_MODEL}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Run: pip install sentence-transformers")
            self._embedder = None

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, text: str, n_results: int = 4) -> Optional[str]:
        """
        Search knowledge base and return relevant context string.
        Returns None if nothing relevant found or KB not ready.
        """
        if not self._ready or not self._embedder or not self._collection:
            return None
        if self._collection.count() == 0:
            return None
        try:
            embedding = self._embedder.encode(text).tolist()
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            docs      = results["documents"][0]
            metas     = results["metadatas"][0]
            distances = results["distances"][0]

            # Filter by relevance (cosine distance < 0.6 is relevant)
            relevant = [
                (doc, meta, dist)
                for doc, meta, dist in zip(docs, metas, distances)
                if dist < 0.6
            ]
            if not relevant:
                return None

            lines = []
            for doc, meta, dist in relevant:
                source = meta.get("source", "unknown")
                lines.append(f"[From: {source}]\n{doc}")

            return (
                "Relevant knowledge from your personal knowledge base:\n\n"
                + "\n\n".join(lines)
                + "\n\nUse this knowledge when answering, citing the source naturally."
            )
        except Exception as e:
            logger.error(f"Knowledge query error: {e}")
            return None

    # ── Ingest ────────────────────────────────────────────────────────────────

    def ingest_text(self, text: str, source: str = "manual") -> int:
        """Ingest a plain text string. Returns number of chunks added."""
        if not self._ready or not self._embedder:
            logger.error("Knowledge base not ready.")
            return 0
        chunks = self._chunk_text(text)
        return self._add_chunks(chunks, source=source)

    def ingest_file(self, path: str | Path) -> int:
        """Ingest a file (TXT, MD, PDF, DOCX, CSV, code files, etc.)."""
        path = Path(path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return 0
        text = self._read_file(path)
        if not text:
            logger.warning(f"Could not extract text from {path}")
            return 0
        return self.ingest_text(text, source=str(path.name))

    def ingest_url(self, url: str) -> int:
        """Fetch a URL and ingest its content."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            r = httpx.get(url, timeout=15, follow_redirects=True,
                          headers={"User-Agent": "Jarvis-Knowledge/1.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            import re
            text = re.sub(r"\s{2,}", " ", text).strip()
            return self.ingest_text(text, source=url)
        except Exception as e:
            logger.error(f"URL ingest error: {e}")
            return 0

    def ingest_folder(self, folder: str | Path, recursive: bool = True) -> int:
        """Ingest all readable files in a folder."""
        folder = Path(folder)
        pattern = "**/*" if recursive else "*"
        total = 0
        for f in folder.glob(pattern):
            if f.is_file() and f.suffix.lower() in READABLE_EXTENSIONS:
                n = self.ingest_file(f)
                logger.info(f"  Ingested {f.name}: {n} chunks")
                total += n
        return total

    # ── Management ────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        if not self._ready:
            return {"ready": False, "chunks": 0}
        return {
            "ready": True,
            "chunks": self._collection.count(),
            "db_path": str(self.db_path),
            "embed_model": EMBED_MODEL,
        }

    def clear(self):
        """Wipe all knowledge."""
        if self._collection:
            self._collection.delete(where={"source": {"$ne": ""}})
            logger.info("Knowledge base cleared.")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - CHUNK_OVERLAP
        return chunks

    def _add_chunks(self, chunks: list[str], source: str) -> int:
        """Embed and store chunks in ChromaDB."""
        if not chunks:
            return 0
        try:
            embeddings = self._embedder.encode(chunks).tolist()
            ids = [
                hashlib.md5(f"{source}:{i}:{c[:50]}".encode()).hexdigest()
                for i, c in enumerate(chunks)
            ]
            metas = [{"source": source, "added": datetime.now().isoformat()} for _ in chunks]
            self._collection.upsert(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metas,
            )
            return len(chunks)
        except Exception as e:
            logger.error(f"Chunk storage error: {e}")
            return 0

    def _read_file(self, path: Path) -> Optional[str]:
        """Extract text from various file formats."""
        suffix = path.suffix.lower()
        try:
            if suffix == ".pdf":
                return self._read_pdf(path)
            elif suffix == ".docx":
                return self._read_docx(path)
            elif suffix == ".csv":
                return path.read_text(encoding="utf-8", errors="ignore")
            else:
                # TXT, MD, code files, etc.
                return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"File read error ({path}): {e}")
            return None

    def _read_pdf(self, path: Path) -> Optional[str]:
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                return "\n".join(p.extract_text() for p in reader.pages if p.extract_text())
            except ImportError:
                logger.warning("Install pdfplumber or pypdf to read PDFs: pip install pdfplumber")
                return None

    def _read_docx(self, path: Path) -> Optional[str]:
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            logger.warning("Install python-docx to read DOCX: pip install python-docx")
            return None


READABLE_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml",
    ".py", ".js", ".ts", ".html", ".css", ".xml",
    ".pdf", ".docx",
    ".c", ".cpp", ".java", ".go", ".rs", ".rb", ".php", ".sh",
}
