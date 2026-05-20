"""
Jarvis Model Manager

Handles downloading, caching, and selecting GGUF models from HuggingFace.
Models are stored in ~/.jarvis/models/ and reused across runs.
"""
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.model_manager")

MODELS_DIR = Path.home() / ".jarvis" / "models"

# Curated model list — tested, sorted by quality/size
# Format: (id, hf_repo, filename, size_gb, description)
AVAILABLE_MODELS = [
    {
        "id": "qwen2.5-7b",
        "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "file": "qwen2.5-7b-instruct-q5_k_m.gguf",
        "size_gb": 5.2,
        "description": "Qwen 2.5 7B — Best default. Beats Llama 3 8B on most benchmarks.",
        "recommended": True,
    },
    {
        "id": "llama3.1-8b",
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf",
        "size_gb": 5.5,
        "description": "Llama 3.1 8B — Meta's flagship small model. Excellent all-rounder.",
    },
    {
        "id": "qwen2.5-3b",
        "repo": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "file": "qwen2.5-3b-instruct-q8_0.gguf",
        "size_gb": 3.1,
        "description": "Qwen 2.5 3B — Fast, good quality. Great for low-RAM machines.",
    },
    {
        "id": "phi4-mini",
        "repo": "microsoft/Phi-4-mini-instruct-gguf",
        "file": "Phi-4-mini-instruct-Q5_K_M.gguf",
        "size_gb": 2.5,
        "description": "Microsoft Phi-4 Mini — Tiny but surprisingly capable. Best for weak hardware.",
    },
    {
        "id": "llama3.1-70b",
        "repo": "bartowski/Meta-Llama-3.1-70B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf",
        "size_gb": 40.0,
        "description": "Llama 3.1 70B — Top tier quality. Requires 48GB+ RAM. Use Groq for free cloud access instead.",
    },
]

DEFAULT_MODEL_ID = "qwen2.5-7b"


def get_model_path(model_id: str) -> Optional[Path]:
    """Return the local path for a model if it exists."""
    model = _find_model(model_id)
    if not model:
        return None
    path = MODELS_DIR / model["file"]
    return path if path.exists() else None


def download_model(model_id: str = DEFAULT_MODEL_ID, force: bool = False) -> Path:
    """
    Download a GGUF model from HuggingFace Hub.
    Returns the local path when complete.
    """
    model = _find_model(model_id)
    if not model:
        available = ", ".join(m["id"] for m in AVAILABLE_MODELS)
        raise ValueError(f"Unknown model '{model_id}'. Available: {available}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    local_path = MODELS_DIR / model["file"]

    if local_path.exists() and not force:
        logger.info(f"Model already cached: {local_path}")
        return local_path

    try:
        from huggingface_hub import hf_hub_download
        from tqdm import tqdm
    except ImportError:
        raise ImportError(
            "huggingface_hub not installed.\n"
            "Run: pip install huggingface-hub tqdm"
        )

    print(f"\nDownloading {model['id']} ({model['size_gb']:.1f} GB)...")
    print(f"  {model['description']}")
    print(f"  Source: huggingface.co/{model['repo']}")
    print(f"  Saving to: {local_path}\n")

    downloaded = hf_hub_download(
        repo_id=model["repo"],
        filename=model["file"],
        local_dir=str(MODELS_DIR),
        local_dir_use_symlinks=False,
    )

    final_path = Path(downloaded)
    print(f"\nModel downloaded: {final_path}")
    return final_path


def list_models(show_downloaded: bool = False) -> list[dict]:
    """List available models, optionally filtered to downloaded only."""
    result = []
    for m in AVAILABLE_MODELS:
        path = MODELS_DIR / m["file"]
        m_copy = {**m, "downloaded": path.exists(), "local_path": str(path)}
        if not show_downloaded or path.exists():
            result.append(m_copy)
    return result


def auto_select_model() -> Optional[str]:
    """
    Automatically select the best model already downloaded.
    Prefers higher quality if multiple are available.
    """
    for model in AVAILABLE_MODELS:
        path = MODELS_DIR / model["file"]
        if path.exists():
            return str(path)
    return None


def print_model_table():
    """Print a table of available models."""
    print("\nAvailable Jarvis Models:")
    print(f"{'ID':<18} {'Size':>6}  {'Downloaded':>10}  Description")
    print("-" * 80)
    for m in AVAILABLE_MODELS:
        path = MODELS_DIR / m["file"]
        downloaded = "✓" if path.exists() else "—"
        rec = " ★" if m.get("recommended") else ""
        print(f"{m['id']:<18} {m['size_gb']:>5.1f}GB  {downloaded:>10}  {m['description']}{rec}")
    print()


def _find_model(model_id: str) -> Optional[dict]:
    return next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
