"""
Jarvis configuration management.
Loads from .env file and provides typed config access.
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")


@dataclass
class AudioConfig:
    # Speech recognition
    stt_model: str = "base.en"         # faster-whisper model: tiny.en, base.en, small.en, medium.en
    stt_device: str = "cpu"            # "cpu" or "cuda"
    stt_compute_type: str = "int8"     # "int8", "float16", "float32"
    silence_threshold: float = 0.01    # RMS silence cutoff
    silence_duration: float = 1.5      # seconds of silence before processing
    max_record_seconds: int = 30       # max recording length

    # Text to speech
    tts_voice: str = "en-GB-RyanNeural"  # Edge TTS voice — closest to Jarvis
    tts_rate: str = "+0%"                # Speed adjustment
    tts_pitch: str = "+0Hz"              # Pitch adjustment

    # Wake word
    wake_words: list = field(default_factory=lambda: ["jarvis", "hey jarvis", "j.a.r.v.i.s"])
    use_wake_word: bool = True


@dataclass
class LLMConfig:
    # Provider: "ollama" | "openai" | "anthropic"
    provider: str = "ollama"
    model: str = "llama3"              # ollama: llama3, mistral, etc. | openai: gpt-4o, gpt-4o-mini
    ollama_host: str = "http://localhost:11434"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    max_tokens: int = 500              # Keep responses concise for voice
    temperature: float = 0.7
    context_window: int = 20           # Number of conversation turns to keep


@dataclass
class JarvisConfig:
    # Identity
    user_title: str = "sir"            # How Jarvis addresses the user
    user_name: str = ""                # Optional: user's actual name
    assistant_name: str = "Jarvis"

    # Behavior
    verbose_mode: bool = False
    debug_mode: bool = False
    auto_open_browser: bool = True

    # Paths
    workspace_dir: Path = field(default_factory=lambda: Path.home() / ".jarvis")
    log_file: str = "jarvis.log"

    audio: AudioConfig = field(default_factory=AudioConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def load_config() -> JarvisConfig:
    """Load configuration from environment variables."""
    config = JarvisConfig()

    # LLM settings
    config.llm.provider = os.getenv("LLM_PROVIDER", "ollama")
    config.llm.model = os.getenv("LLM_MODEL", "llama3")
    config.llm.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    config.llm.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    config.llm.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Audio settings
    config.audio.stt_model = os.getenv("WHISPER_MODEL", "base.en")
    config.audio.stt_device = os.getenv("WHISPER_DEVICE", "cpu")
    config.audio.tts_voice = os.getenv("TTS_VOICE", "en-GB-RyanNeural")
    config.audio.use_wake_word = os.getenv("USE_WAKE_WORD", "true").lower() == "true"

    # Identity
    config.user_title = os.getenv("USER_TITLE", "sir")
    config.user_name = os.getenv("USER_NAME", "")
    config.debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    # Create workspace dir
    config.workspace_dir.mkdir(parents=True, exist_ok=True)

    return config
