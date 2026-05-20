#!/usr/bin/env python3
"""
J.A.R.V.I.S. — Just A Rather Very Intelligent System
Launcher script.
"""
import sys
import os
import argparse
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def main():
    parser = argparse.ArgumentParser(
        description="J.A.R.V.I.S. — Just A Rather Very Intelligent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jarvis.py                  # Start with default config
  python jarvis.py --text           # Text-only mode (no microphone)
  python jarvis.py --model llama3   # Use specific Ollama model
  python jarvis.py --provider openai --model gpt-4o  # Use OpenAI
  python jarvis.py --debug          # Enable debug logging
        """,
    )
    parser.add_argument("--text", action="store_true", help="Text-only mode (no voice input)")
    parser.add_argument("--no-tts", action="store_true", help="Disable text-to-speech output")
    parser.add_argument("--provider", choices=["ollama", "openai", "anthropic"], help="LLM provider")
    parser.add_argument("--model", help="Model name (e.g. llama3, gpt-4o, claude-3-5-sonnet)")
    parser.add_argument("--voice", help="TTS voice (default: en-GB-RyanNeural)")
    parser.add_argument("--no-wake-word", action="store_true", help="Disable wake word detection")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--list-voices", action="store_true", help="List available TTS voices and exit")

    args = parser.parse_args()

    # Logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level, format="%(name)s: %(message)s")

    # Config
    from jarvis import load_config
    config = load_config()

    if args.provider:
        config.llm.provider = args.provider
    if args.model:
        config.llm.model = args.model
    if args.voice:
        config.audio.tts_voice = args.voice
    if args.text:
        config.audio.use_wake_word = False
    if args.no_wake_word:
        config.audio.use_wake_word = False
    if args.debug:
        config.debug_mode = True

    # List voices
    if args.list_voices:
        import asyncio
        from jarvis.voice.speaker import Speaker
        s = Speaker()
        voices = asyncio.run(s.list_voices())
        print("\nAvailable English TTS voices:")
        for v in sorted(voices):
            marker = " <-- current" if v == config.audio.tts_voice else ""
            print(f"  {v}{marker}")
        print()
        sys.exit(0)

    # Patch speaker if TTS disabled
    if args.no_tts:
        from jarvis.voice import speaker as speaker_mod
        class SilentSpeaker:
            def speak(self, text): pass
            async def speak_async(self, text): pass
        speaker_mod.Speaker = lambda **kwargs: SilentSpeaker()

    # Launch
    from jarvis import Jarvis
    try:
        j = Jarvis(config)
        j.start()
    except KeyboardInterrupt:
        print("\nGoodbye, sir.")
        sys.exit(0)
    except Exception as e:
        if args.debug:
            raise
        print(f"\nFatal error: {e}")
        print("Run with --debug for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
