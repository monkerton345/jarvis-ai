"""
Jarvis Brain — LLM routing.

Provider priority (auto-fallback chain):
  1. llamacpp  — local GGUF model, fully offline, no API key
  2. groq      — free cloud, Llama 3.1 70B @ 300 tokens/sec
  3. openrouter — 100+ models including Claude, GPT-4o

No Ollama. No external software. Just Python.
"""
import logging
from typing import Optional
from .personality import JARVIS_SYSTEM_PROMPT

logger = logging.getLogger("jarvis.llm")


class ConversationHistory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._messages: list[dict] = []

    def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        if len(self._messages) > self.max_turns * 2:
            self._messages = self._messages[-(self.max_turns * 2):]

    def get(self) -> list[dict]:
        return list(self._messages)

    def inject(self, content: str):
        self._messages.append({"role": "system", "content": content})

    def clear(self):
        self._messages.clear()


class Brain:
    """
    Unified LLM interface for Jarvis.
    Supports llamacpp (local), groq (free cloud), openrouter (any model).
    """

    def __init__(
        self,
        provider: str = "llamacpp",
        # llamacpp
        model_path: str = "",
        n_gpu_layers: int = -1,
        n_ctx: int = 4096,
        # groq
        groq_api_key: str = "",
        groq_model: str = "llama-3.3-70b-versatile",
        # openrouter
        openrouter_api_key: str = "",
        openrouter_model: str = "meta-llama/llama-3.1-70b-instruct:free",
        # shared
        max_tokens: int = 512,
        temperature: float = 0.7,
        context_window: int = 20,
    ):
        self.provider = provider
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.history = ConversationHistory(max_turns=context_window)
        self._backend = None

        self._init(
            provider=provider,
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            groq_api_key=groq_api_key,
            groq_model=groq_model,
            openrouter_api_key=openrouter_api_key,
            openrouter_model=openrouter_model,
        )

    def _init(self, **kwargs):
        provider = kwargs["provider"]

        if provider == "llamacpp":
            self._init_llamacpp(**kwargs)
        elif provider == "groq":
            self._init_groq(**kwargs)
        elif provider == "openrouter":
            self._init_openrouter(**kwargs)
        else:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Choose: llamacpp, groq, openrouter"
            )

    def _init_llamacpp(self, model_path, n_gpu_layers, n_ctx, **_):
        from .backends.llamacpp import LlamaCppBackend
        from .model_manager import auto_select_model, download_model, DEFAULT_MODEL_ID

        # Auto-find model
        resolved_path = model_path
        if not resolved_path:
            resolved_path = auto_select_model()

        if not resolved_path:
            logger.warning("No model found locally. Downloading default model...")
            resolved_path = str(download_model(DEFAULT_MODEL_ID))

        self._backend = LlamaCppBackend(
            model_path=resolved_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        logger.info(f"Brain online: {self._backend.model_name} (local)")

    def _init_groq(self, groq_api_key, groq_model, **_):
        from .backends.groq_backend import GroqBackend
        self._backend = GroqBackend(
            api_key=groq_api_key,
            model=groq_model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        logger.info(f"Brain online: {self._backend.model_name} (Groq)")

    def _init_openrouter(self, openrouter_api_key, openrouter_model, **_):
        from .backends.openrouter import OpenRouterBackend
        self._backend = OpenRouterBackend(
            api_key=openrouter_api_key,
            model=openrouter_model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        logger.info(f"Brain online: {self._backend.model_name} (OpenRouter)")

    def think(self, user_input: str, extra_context: Optional[str] = None) -> str:
        """Process input and return Jarvis response."""
        if extra_context:
            self.history.inject(f"[Live Context]: {extra_context}")

        self.history.add("user", user_input)

        try:
            response = self._backend.generate(
                messages=self.history.get(),
                system_prompt=JARVIS_SYSTEM_PROMPT,
            )
            self.history.add("assistant", response)
            return response
        except Exception as e:
            logger.error(f"Brain error: {e}")
            return "I'm afraid I encountered a technical difficulty, sir. Please try again."

    def clear_history(self):
        self.history.clear()

    @property
    def backend_name(self) -> str:
        return self._backend.model_name if self._backend else "none"
