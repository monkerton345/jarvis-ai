"""
Jarvis core engine.
Orchestrates: voice input -> skill routing -> LLM -> voice output
"""
import asyncio
import logging
import random
import sys
import threading
from typing import Optional

from .config import JarvisConfig
from .voice.listener import Listener
from .voice.speaker import Speaker
from .voice.wake_word import WakeWordDetector
from .brain.llm import Brain
from .brain.personality import STARTUP_LINES, WAKE_RESPONSES, SHUTDOWN_LINES, NOT_UNDERSTOOD_LINES
from .ui.terminal import JarvisUI
from . import skills

logger = logging.getLogger("jarvis.core")


class Jarvis:
    def __init__(self, config: JarvisConfig):
        self.config = config
        self.ui = JarvisUI(debug=config.debug_mode)

        self._mode = "voice"  # "voice" or "text"
        self._running = False
        self._listening = False
        self._wake_lock = threading.Lock()

        # Initialize subsystems
        self.ui.status("Initializing speech synthesis...")
        self.speaker = Speaker(
            voice=config.audio.tts_voice,
            rate=config.audio.tts_rate,
            pitch=config.audio.tts_pitch,
        )

        self.ui.status("Loading language model...")
        self.brain = Brain(
            provider=config.llm.provider,
            model=config.llm.model,
            ollama_host=config.llm.ollama_host,
            openai_api_key=config.llm.openai_api_key,
            anthropic_api_key=config.llm.anthropic_api_key,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            context_window=config.llm.context_window,
        )

        self.ui.status("Initializing speech recognition...")
        self.listener = Listener(
            model_size=config.audio.stt_model,
            device=config.audio.stt_device,
            compute_type=config.audio.stt_compute_type,
            silence_threshold=config.audio.silence_threshold,
            silence_duration=config.audio.silence_duration,
            max_record_seconds=config.audio.max_record_seconds,
        )

        # Set timer callback so alerts are spoken
        from .skills import timers
        timers.set_speak_callback(self._speak_sync)

        self.ui.status("Jarvis initialized.", icon="✓")

    def start(self):
        """Start Jarvis — shows banner, speaks startup line, enters main loop."""
        self.ui.print_banner()
        self._running = True

        # Startup greeting
        startup = random.choice(STARTUP_LINES)
        self.ui.jarvis_response(startup)
        self._speak_sync(startup)

        if self._mode == "voice" and self.config.audio.use_wake_word:
            self._start_wake_word_detector()
            self.ui.status("Listening for wake word. Say 'Jarvis' to activate.")
            self._text_loop()  # Also allow text input
        else:
            self._text_loop()

    def _start_wake_word_detector(self):
        """Launch wake word detector in background."""
        self._wake_detector = WakeWordDetector(
            wake_words=self.config.audio.wake_words,
            hotkey="ctrl+shift+j",
        )
        self._wake_detector.start(on_wake=self._on_wake_word)

    def _on_wake_word(self):
        """Called when wake word is detected."""
        with self._wake_lock:
            if self._listening:
                return
            self._listening = True

        wake_resp = random.choice(WAKE_RESPONSES)
        self.ui.jarvis_response(wake_resp)
        self._speak_sync(wake_resp)

        self.ui.show_listening()
        text = self.listener.listen_once(timeout=10)

        self._listening = False

        if not text:
            not_heard = random.choice(NOT_UNDERSTOOD_LINES)
            self.ui.jarvis_response(not_heard)
            self._speak_sync(not_heard)
            return

        self._process(text)

    def _text_loop(self):
        """Main text input loop (always available, even in voice mode)."""
        while self._running:
            try:
                user_input = self.ui.user_input_prompt()
                if not user_input:
                    continue
                if self._handle_command(user_input):
                    continue
                self._process(user_input)
            except KeyboardInterrupt:
                self._shutdown()
                break
            except EOFError:
                self._shutdown()
                break

    def _process(self, user_input: str):
        """Core processing pipeline: route -> LLM -> speak."""
        logger.debug(f"Processing: '{user_input}'")

        # Check for skill routing first
        context = self._route_skills(user_input)

        # Think
        self.ui.show_thinking()
        response = self.brain.think(user_input, extra_context=context)

        # Respond
        self.ui.jarvis_response(response)
        self._speak_sync(response)

    def _route_skills(self, query: str) -> Optional[str]:
        """Run all skills and collect any relevant context."""
        from .skills import time_skill, weather, system, web, timers

        skill_funcs = [
            time_skill.handle,
            lambda q: weather.handle(q, default_location="auto"),
            system.handle,
            web.handle,
            timers.handle,
        ]

        contexts = []
        for fn in skill_funcs:
            try:
                result = fn(query)
                if result:
                    contexts.append(result)
            except Exception as e:
                logger.warning(f"Skill error: {e}")

        return "\n".join(contexts) if contexts else None

    def _handle_command(self, text: str) -> bool:
        """Handle special commands. Returns True if handled."""
        cmd = text.lower().strip()

        if cmd in ("exit", "quit", "goodbye", "bye", "shutdown"):
            self._shutdown()
            return True

        if cmd == "clear":
            self.brain.clear_history()
            self.ui.success("Conversation history cleared.")
            return True

        if cmd == "help":
            self.ui.print_help()
            return True

        if cmd in ("mode voice", "voice mode", "voice on"):
            self._mode = "voice"
            self.ui.success("Voice mode activated.")
            return True

        if cmd in ("mode text", "text mode", "voice off"):
            self._mode = "text"
            self.ui.success("Text mode activated.")
            return True

        return False

    def _speak_sync(self, text: str):
        """Speak text (blocks until done)."""
        if not text:
            return
        self.ui.show_speaking()
        try:
            self.speaker.speak(text)
        except Exception as e:
            logger.error(f"Speech error: {e}")

    def _shutdown(self):
        """Graceful shutdown."""
        self._running = False
        shutdown_line = random.choice(SHUTDOWN_LINES)
        self.ui.jarvis_response(shutdown_line)
        self._speak_sync(shutdown_line)
        if hasattr(self, "_wake_detector"):
            self._wake_detector.stop()
        sys.exit(0)
