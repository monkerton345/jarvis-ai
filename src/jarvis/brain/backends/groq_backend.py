"""
Jarvis Groq Backend

Groq runs open-source models (Llama 3.1 70B, Mixtral 8x7B) at 300+ tokens/sec.
Free tier: 14,400 tokens/minute — more than enough for voice assistant use.
No GPU needed. Genuinely better output quality than running 7B models locally.

Get a free API key: https://console.groq.com (takes 30 seconds)

Models available on Groq:
  - llama-3.1-70b-versatile   (best quality, recommended)
  - llama-3.1-8b-instant      (fastest)
  - mixtral-8x7b-32768        (good for long context)
  - gemma2-9b-it              (Google's model, solid)
"""
import logging
from typing import Optional

logger = logging.getLogger("jarvis.brain.groq")

# Best models ranked by quality
GROQ_MODELS = {
    "best":    "llama-3.1-70b-versatile",
    "fast":    "llama-3.1-8b-instant",
    "long":    "mixtral-8x7b-32768",
    "default": "llama-3.3-70b-versatile",
}


class GroqBackend:
    """Groq cloud inference — fast, free, high quality."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ):
        if not api_key:
            raise ValueError(
                "Groq API key required.\n"
                "Get one free at: https://console.groq.com\n"
                "Then set: GROQ_API_KEY=your_key in .env"
            )
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None
        self._init()

    def _init(self):
        try:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
            logger.info(f"Groq backend ready: {self.model}")
        except ImportError:
            raise ImportError(
                "groq package not installed.\n"
                "Run: pip install groq"
            )

    def generate(self, messages: list[dict], system_prompt: str) -> str:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise

    @property
    def model_name(self) -> str:
        return f"groq/{self.model}"
