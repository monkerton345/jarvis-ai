"""
Jarvis configuration — loads from .env, provides typed config.
No Ollama. Providers: llamacpp (local), groq (free cloud), openrouter.
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")


@dataclass
class AudioConfig:
    stt_model: str = "base.en"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    silence_threshold: float = 0.01
    silence_duration: float = 1.5
    max_record_seconds: int = 30
    sample_rate: int = 16000
    tts_voice: str = "en-GB-RyanNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"
    wake_words: list = field(default_factory=lambda: ["jarvis", "hey jarvis"])
    use_wake_word: bool = True


@dataclass
class LLMConfig:
    # Provider: "llamacpp" | "groq" | "openrouter"
    provider: str = "llamacpp"

    # llamacpp (local)
    model_path: str = ""            # Auto-downloads if empty
    model_id: str = "qwen2.5-7b"   # Which model to auto-download
    n_gpu_layers: int = -1          # -1 = all on GPU, 0 = CPU only
    n_ctx: int = 4096

    # Groq (free cloud — https://console.groq.com)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # OpenRouter (100+ models — https://openrouter.ai)
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-70b-instruct:free"

    max_tokens: int = 512
    temperature: float = 0.7
    context_window: int = 20


@dataclass
class JarvisConfig:
    user_title: str = "sir"
    user_name: str = ""
    assistant_name: str = "Jarvis"
    debug_mode: bool = False
    workspace_dir: Path = field(default_factory=lambda: Path.home() / ".jarvis")

    audio: AudioConfig = field(default_factory=AudioConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def load_config() -> JarvisConfig:
    config = JarvisConfig()

    # LLM
    config.llm.provider        = os.getenv("LLM_PROVIDER", "llamacpp")
    config.llm.model_path       = os.getenv("LLAMACPP_MODEL_PATH", "")
    config.llm.model_id         = os.getenv("LLAMACPP_MODEL_ID", "qwen2.5-7b")
    config.llm.n_gpu_layers     = int(os.getenv("GPU_LAYERS", "-1"))
    config.llm.n_ctx            = int(os.getenv("CONTEXT_SIZE", "4096"))
    config.llm.groq_api_key     = os.getenv("GROQ_API_KEY", "")
    config.llm.groq_model       = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    config.llm.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
    config.llm.openrouter_model  = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-70b-instruct:free")
    config.llm.max_tokens       = int(os.getenv("MAX_TOKENS", "512"))
    config.llm.temperature      = float(os.getenv("TEMPERATURE", "0.7"))

    # Audio
    config.audio.stt_model      = os.getenv("WHISPER_MODEL", "base.en")
    config.audio.stt_device     = os.getenv("WHISPER_DEVICE", "cpu")
    config.audio.tts_voice      = os.getenv("TTS_VOICE", "en-GB-RyanNeural")
    config.audio.use_wake_word  = os.getenv("USE_WAKE_WORD", "true").lower() == "true"

    # Identity
    config.user_title = os.getenv("USER_TITLE", "sir")
    config.user_name  = os.getenv("USER_NAME", "")
    config.debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    config.workspace_dir.mkdir(parents=True, exist_ok=True)
    return config
