#!/usr/bin/env python3
"""
J.A.R.V.I.S. Setup Script

Run this once after cloning. It will:
  1. Check Python version
  2. Install all dependencies
  3. Let you choose your AI provider
  4. Download the AI model (if using local)
  5. Create your .env config
  6. Run a quick test

Usage:
    python setup_jarvis.py
    python setup_jarvis.py --provider groq
    python setup_jarvis.py --model qwen2.5-3b  (smaller, faster)
    python setup_jarvis.py --list-models
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def run(cmd: str, check: bool = True):
    return subprocess.run(cmd, shell=True, check=check)


def header(text: str):
    print(f"\n{'─'*55}")
    print(f"  {text}")
    print(f"{'─'*55}")


def check_python():
    header("Checking Python version")
    v = sys.version_info
    if v < (3, 10):
        print(f"  ✗ Python {v.major}.{v.minor} found. Python 3.10+ required.")
        print("    Download: https://python.org")
        sys.exit(1)
    print(f"  ✓ Python {v.major}.{v.minor}.{v.micro}")


def install_deps():
    header("Installing dependencies")
    run(f"{sys.executable} -m pip install -r requirements.txt --quiet")
    print("  ✓ Dependencies installed")


def choose_provider() -> str:
    header("Choose your AI engine")
    print("  [1] Local AI — Qwen 2.5 7B (no API key, runs offline)")
    print("      Downloads ~5GB model. Best for privacy. Needs 8GB RAM.")
    print()
    print("  [2] Groq — FREE cloud AI (Llama 3.1 70B)")
    print("      No download. 300+ tokens/sec. Free at console.groq.com")
    print("      RECOMMENDED if you want speed + quality for free.")
    print()
    print("  [3] OpenRouter — Access Claude 3.5, GPT-4o, and more")
    print("      Free + paid models. openrouter.ai")
    print()
    choice = input("  Your choice [1/2/3]: ").strip()
    if choice == "2":
        return "groq"
    elif choice == "3":
        return "openrouter"
    return "llamacpp"


def setup_local(model_id: str):
    header(f"Downloading AI model: {model_id}")
    sys.path.insert(0, str(ROOT / "src"))
    from jarvis.brain.model_manager import download_model, print_model_table
    print_model_table()
    path = download_model(model_id)
    print(f"\n  ✓ Model ready: {path}")
    return str(path)


def setup_groq() -> str:
    header("Groq Setup")
    print("  1. Go to https://console.groq.com")
    print("  2. Sign up (free, takes 30 seconds)")
    print("  3. Create an API key")
    print()
    key = input("  Paste your Groq API key: ").strip()
    if not key:
        print("  Skipping — you can add GROQ_API_KEY to .env later.")
    return key


def setup_openrouter() -> str:
    header("OpenRouter Setup")
    print("  1. Go to https://openrouter.ai")
    print("  2. Sign up and create an API key")
    print("  3. Free models available — no payment needed")
    print()
    key = input("  Paste your OpenRouter API key: ").strip()
    return key


def write_env(provider: str, model_path: str = "", groq_key: str = "",
              openrouter_key: str = "", model_id: str = "qwen2.5-7b"):
    header("Writing configuration")
    env_content = ENV_EXAMPLE.read_text()

    # Set provider
    env_content = env_content.replace("LLM_PROVIDER=llamacpp", f"LLM_PROVIDER={provider}")

    if provider == "llamacpp" and model_path:
        env_content = env_content.replace(
            "LLAMACPP_MODEL_ID=qwen2.5-7b",
            f"LLAMACPP_MODEL_ID={model_id}\n# LLAMACPP_MODEL_PATH={model_path}"
        )
    if groq_key:
        env_content = env_content.replace(
            "# GROQ_API_KEY=gsk_...", f"GROQ_API_KEY={groq_key}"
        )
    if openrouter_key:
        env_content = env_content.replace(
            "# OPENROUTER_API_KEY=sk-or-...", f"OPENROUTER_API_KEY={openrouter_key}"
        )

    ENV_FILE.write_text(env_content)
    print(f"  ✓ Config written to .env")


def run_test(provider: str):
    header("Running quick test")
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from jarvis import load_config, Jarvis
        config = load_config()
        print(f"  Provider:  {config.llm.provider}")
        print(f"  TTS voice: {config.audio.tts_voice}")
        print(f"  STT model: {config.audio.stt_model}")
        print()
        print("  ✓ Configuration loaded successfully")
        print()
        print("  Run Jarvis with:")
        print("    python jarvis.py --text    (text mode, no mic)")
        print("    python jarvis.py           (full voice mode)")
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        print("    Try: python jarvis.py --debug")


def main():
    parser = argparse.ArgumentParser(description="Set up J.A.R.V.I.S.")
    parser.add_argument("--provider", choices=["llamacpp", "groq", "openrouter"],
                        help="Skip prompt, use this provider")
    parser.add_argument("--model", default="qwen2.5-7b", help="Model ID for local AI")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    print("""
 ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
 ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
 ██║███████║██████╔╝██║   ██║██║███████╗
 ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
 ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
   Setup Wizard — J.A.R.V.I.S. v1.0
    """)

    if args.list_models:
        sys.path.insert(0, str(ROOT / "src"))
        from jarvis.brain.model_manager import print_model_table
        print_model_table()
        return

    check_python()
    install_deps()

    provider = args.provider or choose_provider()
    model_path = ""
    groq_key = ""
    openrouter_key = ""

    if provider == "llamacpp" and not args.skip_download:
        model_path = setup_local(args.model)
    elif provider == "groq":
        groq_key = setup_groq()
    elif provider == "openrouter":
        openrouter_key = setup_openrouter()

    write_env(provider, model_path, groq_key, openrouter_key, args.model)
    run_test(provider)

    print(f"""
{'═'*55}
  Setup complete, sir.
  
  Start Jarvis:
    python jarvis.py           — full voice + text mode
    python jarvis.py --text    — text only (no mic needed)
    python jarvis.py --help    — all options

  To build a Windows .exe:
    build_windows.bat
{'═'*55}
""")


if __name__ == "__main__":
    main()
