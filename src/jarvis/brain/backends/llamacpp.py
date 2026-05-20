"""
Jarvis Custom Inference Engine — llama-cpp-python

Runs GGUF models directly. No Ollama. No external software.
Just Python + a model file.

Supports:
- CPU inference (any machine)
- GPU acceleration (CUDA/Metal auto-detected)
- Streaming
- Full context management
"""
import logging
import os
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger("jarvis.brain.llamacpp")


class LlamaCppBackend:
    """
    Direct GGUF inference via llama-cpp-python.
    The core of Jarvis's custom AI engine.
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,      # -1 = offload all layers to GPU (auto)
        n_threads: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        verbose: bool = False,
    ):
        self.model_path = str(model_path)
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads or max(1, os.cpu_count() - 2)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm = None
        self._load(verbose)

    def _load(self, verbose: bool = False):
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed.\n"
                "CPU-only:  pip install llama-cpp-python\n"
                "With CUDA: pip install llama-cpp-python --extra-index-url "
                "https://abetlen.github.io/llama-cpp-python/whl/cu121"
            )

        if not Path(self.model_path).exists():
            raise FileNotFoundError(
                f"Model not found: {self.model_path}\n"
                f"Run setup: python setup_jarvis.py"
            )

        logger.info(f"Loading model: {Path(self.model_path).name}")
        logger.info(f"GPU layers: {self.n_gpu_layers}, Threads: {self.n_threads}, Context: {self.n_ctx}")

        self._llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            n_threads=self.n_threads,
            verbose=verbose,
            chat_format="chatml",       # Works with Llama 3, Qwen, Mistral
        )
        logger.info(f"Model loaded: {Path(self.model_path).name}")

    def generate(self, messages: list[dict], system_prompt: str) -> str:
        """Generate a response from a list of chat messages."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = self._llm.create_chat_completion(
                messages=full_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=["<|eot_id|>", "<|end|>", "</s>"],
                repeat_penalty=1.1,
                top_p=0.9,
                top_k=40,
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise

    def generate_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Stream tokens as they're generated."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            stream = self._llm.create_chat_completion(
                messages=full_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    yield token
        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

    @property
    def model_name(self) -> str:
        return Path(self.model_path).stem

    def get_info(self) -> dict:
        return {
            "model": self.model_name,
            "context": self.n_ctx,
            "gpu_layers": self.n_gpu_layers,
            "threads": self.n_threads,
        }
