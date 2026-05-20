"""
LLM brain for Jarvis.
Supports: Ollama (local), OpenAI, Anthropic.
Manages conversation history for context-aware responses.
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
        # Keep within window (preserve system context)
        if len(self._messages) > self.max_turns * 2:
            self._messages = self._messages[-(self.max_turns * 2):]

    def get_messages(self, system_prompt: str) -> list[dict]:
        return [{"role": "system", "content": system_prompt}] + self._messages

    def clear(self):
        self._messages.clear()

    def inject(self, content: str):
        """Inject a system-level context note (e.g. tool result)."""
        self._messages.append({"role": "system", "content": content})


class Brain:
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3",
        ollama_host: str = "http://localhost:11434",
        openai_api_key: str = "",
        anthropic_api_key: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
        context_window: int = 20,
    ):
        self.provider = provider
        self.model = model
        self.ollama_host = ollama_host
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.history = ConversationHistory(max_turns=context_window)
        self._client = None
        self._init()

    def _init(self):
        """Initialize the LLM client."""
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "anthropic":
            self._init_anthropic()
        else:
            self._check_ollama()

    def _init_openai(self):
        try:
            import openai
            self._client = openai.OpenAI(api_key=self.openai_api_key)
            logger.info(f"LLM: OpenAI / {self.model}")
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            raise

    def _init_anthropic(self):
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            logger.info(f"LLM: Anthropic / {self.model}")
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            raise

    def _check_ollama(self):
        try:
            import httpx
            r = httpx.get(f"{self.ollama_host}/api/tags", timeout=3)
            models = [m["name"] for m in r.json().get("models", [])]
            if models:
                logger.info(f"LLM: Ollama / {self.model} (available: {', '.join(models[:3])}...)")
            else:
                logger.warning("Ollama running but no models pulled. Run: ollama pull llama3")
        except Exception as e:
            logger.error(
                f"Ollama not reachable at {self.ollama_host}. "
                f"Install from https://ollama.ai and run 'ollama serve'. Error: {e}"
            )

    def think(self, user_input: str, extra_context: Optional[str] = None) -> str:
        """
        Process user input and return Jarvis response.
        Maintains conversation history automatically.
        """
        if extra_context:
            self.history.inject(f"[Context]: {extra_context}")

        self.history.add("user", user_input)
        messages = self.history.get_messages(JARVIS_SYSTEM_PROMPT)

        try:
            if self.provider == "openai":
                response = self._think_openai(messages)
            elif self.provider == "anthropic":
                response = self._think_anthropic(messages)
            else:
                response = self._think_ollama(messages)

            self.history.add("assistant", response)
            return response

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "I'm afraid I encountered a technical difficulty, sir. Please try again."

    def _think_ollama(self, messages: list[dict]) -> str:
        """Generate response via Ollama."""
        try:
            import httpx
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            }
            r = httpx.post(
                f"{self.ollama_host}/api/chat",
                json=payload,
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")

    def _think_openai(self, messages: list[dict]) -> str:
        """Generate response via OpenAI."""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()

    def _think_anthropic(self, messages: list[dict]) -> str:
        """Generate response via Anthropic Claude."""
        # Extract system message
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        chat_messages = [m for m in messages if m["role"] != "system"]
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=chat_messages,
        )
        return response.content[0].text.strip()

    def clear_history(self):
        self.history.clear()
        logger.info("Conversation history cleared.")
