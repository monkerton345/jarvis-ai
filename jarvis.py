#!/usr/bin/env python3
"""
J.A.R.V.I.S. — Just A Rather Very Intelligent System
Main launcher.

First run:  wizard appears, config saved to AppData, Jarvis starts.
Every run after:  double-click and go.
"""
import sys
import os
import argparse
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))


def main():
    parser = argparse.ArgumentParser(
        description="J.A.R.V.I.S.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jarvis.py                  Start Jarvis (setup wizard on first run)
  python jarvis.py --text           Text-only mode (no mic)
  python jarvis.py --no-tts         Disable voice output
  python jarvis.py --provider groq  Override AI provider
  python jarvis.py --reset          Re-run the setup wizard
  python jarvis.py --models         List available local models
  python jarvis.py --debug          Verbose logging
        """,
    )
    parser.add_argument("--text",        action="store_true", help="Text-only mode")
    parser.add_argument("--no-tts",      action="store_true", help="Disable text-to-speech")
    parser.add_argument("--provider",    choices=["llamacpp", "groq", "openrouter"])
    parser.add_argument("--model",       help="Model path or ID override")
    parser.add_argument("--voice",       help="TTS voice override")
    parser.add_argument("--no-wake-word",action="store_true")
    parser.add_argument("--reset",       action="store_true", help="Re-run first-run setup wizard")
    parser.add_argument("--models",      action="store_true", help="List available local AI models")
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--debug",       action="store_true")
    args = parser.parse_args()

    # ── First-run / reset ─────────────────────────────────────────────────────
    from jarvis.ui.first_run import CONFIG_FILE, ensure_ready

    if args.reset and CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        print("Config cleared. Running setup wizard...\n")

    ensure_ready()   # Runs wizard if needed, loads config into env

    # ── Logging ───────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(name)s: %(message)s",
    )

    # ── Model list ────────────────────────────────────────────────────────────
    if args.models:
        from jarvis.brain.model_manager import print_model_table
        print_model_table()
        sys.exit(0)

    # ── Load config ───────────────────────────────────────────────────────────
    from jarvis import load_config
    config = load_config()

    # ── CLI overrides ─────────────────────────────────────────────────────────
    if args.provider:  config.llm.provider = args.provider
    if args.voice:     config.audio.tts_voice = args.voice
    if args.text or args.no_wake_word:
        config.audio.use_wake_word = False
    if args.debug:     config.debug_mode = True
    if args.model:
        # Could be a path or a model ID
        if os.path.exists(args.model):
            config.llm.model_path = args.model
        else:
            config.llm.model_id = args.model

    # ── List voices ───────────────────────────────────────────────────────────
    if args.list_voices:
        import asyncio
        from jarvis.voice.speaker import Speaker
        voices = asyncio.run(Speaker().list_voices())
        for v in sorted(voices):
            marker = " <-- current" if v == config.audio.tts_voice else ""
            print(f"  {v}{marker}")
        sys.exit(0)

    # ── Disable TTS ───────────────────────────────────────────────────────────
    if args.no_tts:
        from jarvis.voice import speaker as sm
        class _Silent:
            def speak(self, t): pass
            async def speak_async(self, t): pass
            async def list_voices(self): return []
        sm.Speaker = lambda **kw: _Silent()

    # ── Launch ────────────────────────────────────────────────────────────────
    from jarvis import Jarvis
    try:
        j = Jarvis(config)
        j.start()
    except KeyboardInterrupt:
        print("\nGoodbye, sir.")
    except Exception as e:
        if args.debug:
            raise
        print(f"\nError: {e}")
        print("Run with --debug for details, or --reset to redo setup.")
        input("\nPress Enter to exit.")
        sys.exit(1)


if __name__ == "__main__":
    main()
