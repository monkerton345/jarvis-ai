"""
Jarvis First-Run Wizard

Runs automatically when no config is detected.
Built into the .exe — zero external setup needed.
Guides the user to a working Jarvis in under 60 seconds.
"""
import os
import sys
import time
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    console = Console()
    RICH = True
except ImportError:
    console = None
    RICH = False


CONFIG_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "Jarvis"
CONFIG_FILE = CONFIG_DIR / "config.env"


def print_header():
    if RICH:
        console.print(Panel(
            Text("J.A.R.V.I.S. — First Run Setup", style="bold bright_cyan", justify="center"),
            border_style="cyan", padding=(1, 4)
        ))
        console.print()
    else:
        print("\n" + "=" * 55)
        print("   J.A.R.V.I.S. — First Run Setup")
        print("=" * 55 + "\n")


def _print(msg: str, style: str = ""):
    if RICH:
        console.print(f"  {msg}", style=style)
    else:
        print(f"  {msg}")


def _ask(prompt: str, default: str = "") -> str:
    if RICH:
        return Prompt.ask(f"  [bright_cyan]{prompt}[/]", default=default)
    else:
        val = input(f"  {prompt}{f' [{default}]' if default else ''}: ").strip()
        return val or default


def _confirm(prompt: str, default: bool = True) -> bool:
    if RICH:
        return Confirm.ask(f"  [bright_cyan]{prompt}[/]", default=default)
    else:
        val = input(f"  {prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        if not val:
            return default
        return val.startswith("y")


def _rule(title: str = ""):
    if RICH:
        console.print(Rule(title, style="cyan"))
    else:
        print(f"\n{'─' * 50}{f'  {title}' if title else ''}")


def needs_setup() -> bool:
    """Returns True if first-run setup is needed."""
    if not CONFIG_FILE.exists():
        return True
    content = CONFIG_FILE.read_text()
    # Config exists but has no real values set
    if "LLM_PROVIDER" not in content:
        return True
    return False


def run_wizard() -> dict:
    """
    Interactive first-run setup.
    Returns config dict ready to write to disk.
    """
    print_header()
    _print("Welcome, sir. Let's get you set up — this takes about 60 seconds.\n")

    _rule("Step 1 of 3 — Choose your AI engine")
    _print("")
    _print("[1] Groq (recommended) — FREE, fast, no download needed", "bright_white")
    _print("    Runs Llama 3.1 70B in the cloud at 300+ words/sec.", "grey54")
    _print("    Get a free key at: [link=https://console.groq.com]console.groq.com[/link]" if RICH else
           "    Get a free key at: console.groq.com", "grey54")
    _print("")
    _print("[2] Local AI — Fully offline, no API key", "bright_white")
    _print("    Downloads Qwen 2.5 7B model (~5GB). Runs on your machine.", "grey54")
    _print("    Needs 8GB+ RAM. First run takes 5-10 min to download.", "grey54")
    _print("")

    choice = _ask("Your choice [1/2]", default="1").strip()
    provider = "groq" if choice != "2" else "llamacpp"

    config = {
        "LLM_PROVIDER": provider,
        "LLAMACPP_MODEL_ID": "qwen2.5-7b",
        "GPU_LAYERS": "-1",
        "CONTEXT_SIZE": "4096",
        "GROQ_API_KEY": "",
        "GROQ_MODEL": "llama-3.3-70b-versatile",
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_MODEL": "meta-llama/llama-3.1-70b-instruct:free",
        "WHISPER_MODEL": "base.en",
        "WHISPER_DEVICE": "cpu",
        "TTS_VOICE": "en-GB-RyanNeural",
        "USE_WAKE_WORD": "true",
        "MAX_TOKENS": "512",
        "TEMPERATURE": "0.7",
        "USER_TITLE": "sir",
        "USER_NAME": "",
        "DEBUG": "false",
    }

    if provider == "groq":
        _rule("Step 2 of 3 — Groq API key")
        _print("")
        _print("1. Open:  https://console.groq.com", "bright_white")
        _print("2. Sign up (free, takes 30 seconds)", "bright_white")
        _print("3. Go to API Keys → Create key", "bright_white")
        _print("4. Paste it below", "bright_white")
        _print("")
        key = _ask("Groq API key (starts with gsk_)").strip()
        if key:
            config["GROQ_API_KEY"] = key
        else:
            _print("No key entered. You can add it to config later.", "yellow")
            _print(f"Config location: {CONFIG_FILE}", "grey54")

    else:
        _rule("Step 2 of 3 — Local model download")
        _print("")
        _print("The AI model will download automatically on first launch.", "grey54")
        _print("Model: Qwen 2.5 7B (~5GB) — better than Llama 3 8B", "grey54")
        _print("")
        gpu = _confirm("Do you have an NVIDIA GPU?", default=False)
        config["GPU_LAYERS"] = "-1" if gpu else "0"
        if gpu:
            _print("GPU acceleration enabled.", "green")
        else:
            _print("CPU mode enabled. Responses take 5-15 seconds each.", "yellow")
            _print("Tip: Use Groq instead for instant responses at no cost.", "grey54")

    _rule("Step 3 of 3 — Personal settings")
    _print("")
    name = _ask("What's your name? (Jarvis will use it)", default="").strip()
    if name:
        config["USER_NAME"] = name
        config["USER_TITLE"] = name

    _print("")
    return config


def save_config(config: dict):
    """Write config to AppData."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# J.A.R.V.I.S. Configuration — auto-generated\n",
        f"# Saved: {time.strftime('%Y-%m-%d %H:%M')}\n",
        "\n",
    ]
    for key, val in config.items():
        lines.append(f"{key}={val}\n")
    CONFIG_FILE.write_text("".join(lines))


def patch_dotenv_path():
    """
    Point python-dotenv at the AppData config file,
    so the rest of Jarvis loads it automatically.
    """
    os.environ["JARVIS_CONFIG"] = str(CONFIG_FILE)
    # Load vars into environment directly
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def ensure_ready():
    """
    Main entry point called from jarvis.py at startup.
    Runs the wizard if needed, then patches env.
    Returns True when ready to launch.
    """
    patch_dotenv_path()

    if needs_setup():
        try:
            config = run_wizard()
            save_config(config)
            patch_dotenv_path()

            _rule()
            _print("")
            _print("Setup complete!", "bold green")
            _print(f"Config saved to: {CONFIG_FILE}", "grey54")
            _print("")

            if config.get("LLM_PROVIDER") == "llamacpp":
                _print("Starting Jarvis — the AI model will download now (~5GB).", "yellow")
                _print("This happens once. Grab a coffee.", "grey54")
            else:
                _print("Starting Jarvis...", "bright_cyan")
            _print("")
            time.sleep(1.5)
        except KeyboardInterrupt:
            print("\n\nSetup cancelled. Run Jarvis again to complete setup.")
            sys.exit(0)

    return True
