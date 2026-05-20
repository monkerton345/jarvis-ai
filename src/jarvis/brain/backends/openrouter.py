"""
Jarvis OpenRouter Backend

OpenRouter gives access to 100+ models through one API:
  - Claude 3.5 Sonnet (Anthropic)
  - GPT-4o (OpenAI)
  - Gemini 1.5 Pro (Google)
  - Many free models with no cost

Get a free API key: https://openrouter.ai (takes 60 seconds)
Free models: use model names ending in ':free'

Good free models on OpenRouter:
  - meta-llama/llama-3.1-70b-instruct:free
  - google/gemma-3-27b-it:free
  - mistralai/mistral-7b-instruct:free
  - deepseek/deepseek-chat:free

Premium models (pay per token):
  - anthropic/claude-3.5-sonnet
  - openai/gpt-4o
  - google/gemini-1.5-pro
"""
import logging

logger = logging.getLogger("jarvis.brain.openrouter")

RECOMMENDED_FREE  = "meta-llama/llama-3.1-70b-instruct:free"
RECOMMENDED_BEST  = "anthropic/claude-3.5-sonnet"


class OpenRouterBackend:
    """OpenRouter backend — access any frontier model with one API."""

    def __init__(
        self,
        api_key: str,
        model: str = RECOMMENDED_FREE,
        max_tokens: int = 512,
        temperature: float = 0.7,
        site_url: str = "https://github.com/monkerton345/jarvis-ai",
    ):
        if not api_key:
            raise ValueError(
                "OpenRouter API key required.\n"
                "Get one free at: https://openrouter.ai\n"
                "Then set: OPENROUTER_API_KEY=your_key in .env"
            )
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.site_url = site_url
        self._client = None
        self._init()

    def _init(self):
        try:
            import httpx  # noqa
            logger.info(f"OpenRouter backend ready: {self.model}")
        except ImportError:
            raise ImportError("httpx not installed. Run: pip install httpx")

    def generate(self, messages: list[dict], system_prompt: str) -> str:
        import httpx
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            r = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": self.site_url,
                    "X-Title": "J.A.R.V.I.S.",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": full_messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise

    @property
    def model_name(self) -> str:
        return f"openrouter/{self.model}"
