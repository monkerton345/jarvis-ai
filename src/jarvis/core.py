"""
Jarvis core engine.
Orchestrates: voice input -> skill routing -> LLM -> voice output
"""
import asyncio
import logging
import random
import re
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

logger = logging.getLogger("jarvis.core")


class Jarvis:
    def __init__(self, config: JarvisConfig):
        self.config = config
        self.ui = JarvisUI(debug=config.debug_mode)

        self._mode = "voice"
        self._running = False
        self._listening = False
        self._wake_lock = threading.Lock()

        # ── Voice ──────────────────────────────────────────────────────────
        self.ui.status("Initializing speech synthesis...")
        self.speaker = Speaker(
            voice=config.audio.tts_voice,
            rate=config.audio.tts_rate,
            pitch=config.audio.tts_pitch,
        )

        self.ui.status("Loading AI engine...")
        self.brain = Brain(
            provider=config.llm.provider,
            model_path=config.llm.model_path,
            n_gpu_layers=config.llm.n_gpu_layers,
            n_ctx=config.llm.n_ctx,
            groq_api_key=config.llm.groq_api_key,
            groq_model=config.llm.groq_model,
            openrouter_api_key=config.llm.openrouter_api_key,
            openrouter_model=config.llm.openrouter_model,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            context_window=config.llm.context_window,
        )
        self.ui.status(f"AI engine: {self.brain.backend_name}", icon="✓")

        self.ui.status("Initializing speech recognition...")
        self.listener = Listener(
            model_size=config.audio.stt_model,
            device=config.audio.stt_device,
            compute_type=config.audio.stt_compute_type,
            silence_threshold=config.audio.silence_threshold,
            silence_duration=config.audio.silence_duration,
            max_record_seconds=config.audio.max_record_seconds,
        )

        # ── Knowledge Base ─────────────────────────────────────────────────
        self.ui.status("Loading knowledge base...")
        try:
            from .knowledge.base import KnowledgeBase
            self.kb = KnowledgeBase(db_path=config.workspace_dir / "knowledge")
            stats = self.kb.stats()
            if stats["ready"]:
                self.ui.status(f"Knowledge base online — {stats['chunks']} chunks indexed.", icon="✓")
            else:
                self.ui.warn("Knowledge base offline (install chromadb + sentence-transformers to enable)")
        except Exception as e:
            logger.warning(f"Knowledge base unavailable: {e}")
            self.kb = None

        # ── Timer callback ─────────────────────────────────────────────────
        from .skills import timers
        timers.set_speak_callback(self._speak_sync)

        self.ui.status("Jarvis initialized.", icon="✓")

    def start(self):
        """Start Jarvis."""
        self.ui.print_banner()
        self._running = True

        startup = random.choice(STARTUP_LINES)
        self.ui.jarvis_response(startup)
        self._speak_sync(startup)

        if self._mode == "voice" and self.config.audio.use_wake_word:
            self._start_wake_word_detector()
            self.ui.status("Listening for wake word. Say 'Jarvis' or press Ctrl+Shift+J.")
            self._text_loop()
        else:
            self._text_loop()

    def _start_wake_word_detector(self):
        self._wake_detector = WakeWordDetector(
            wake_words=self.config.audio.wake_words,
            hotkey="ctrl+shift+j",
        )
        self._wake_detector.start(on_wake=self._on_wake_word)

    def _on_wake_word(self):
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
        """Main text input loop."""
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
        """Core pipeline: skills -> knowledge -> LLM -> speak."""
        logger.debug(f"Processing: '{user_input}'")

        # Gather context from all sources in parallel
        contexts = []

        # 1. Built-in skills
        skill_ctx = self._route_skills(user_input)
        if skill_ctx:
            contexts.append(skill_ctx)

        # 2. Internet
        internet_ctx = self._route_internet(user_input)
        if internet_ctx:
            contexts.append(internet_ctx)
            research_ctx = self._ingest_research_if_requested(user_input, internet_ctx)
            if research_ctx:
                contexts.append(research_ctx)

        # 3. Knowledge base (RAG)
        if self.kb:
            kb_ctx = self.kb.query(user_input)
            if kb_ctx:
                contexts.append(kb_ctx)

        combined_context = "\n\n---\n\n".join(contexts) if contexts else None

        self.ui.show_thinking()
        response = self.brain.think(user_input, extra_context=combined_context)

        self.ui.jarvis_response(response)
        self._speak_sync(response)

    def _ingest_research_if_requested(self, query: str, internet_ctx: str) -> Optional[str]:
        """
        If the user asked Jarvis to research a topic, persist the fetched
        internet context into the knowledge base for future retrieval.
        """
        if not self.kb or not internet_ctx:
            return None

        q = query.lower()
        triggers = ["research", "research this", "research that", "look into", "investigate"]
        if not any(t in q for t in triggers):
            return None

        topic = re.sub(r"\s+", " ", query).strip()[:120]
        chunks = self.kb.ingest_text(internet_ctx, source=f"research:{topic}")
        if chunks <= 0:
            return "Research completed, but knowledge storage was unavailable. Inform sir politely."
        return (
            f"Research complete and stored in long-term knowledge: {chunks} chunks "
            f"under source 'research:{topic}'. Confirm this to the user in character."
        )

    def _route_skills(self, query: str) -> Optional[str]:
        from .skills import time_skill, weather, system, web, timers, file_ops
        from .knowledge.ingest import handle_ingest_command

        skill_funcs = [
            time_skill.handle,
            lambda q: weather.handle(q, default_location="auto"),
            system.handle,
            web.handle,
            timers.handle,
            file_ops.handle,
            lambda q: handle_ingest_command(q, self.kb) if self.kb else None,
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

    def _route_internet(self, query: str) -> Optional[str]:
        """Route to internet skills if query needs live data."""
        try:
            from .skills.internet import handle as internet_handle
            return internet_handle(query)
        except Exception as e:
            logger.warning(f"Internet skill error: {e}")
            return None

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

        if cmd in ("kb stats", "knowledge stats", "knowledge base stats"):
            if self.kb:
                stats = self.kb.stats()
                self.ui.status(f"Knowledge base: {stats.get('chunks', 0)} chunks indexed.")
            else:
                self.ui.warn("Knowledge base not available.")
            return True

        if cmd == "kb clear":
            if self.kb:
                self.kb.clear()
                self.ui.success("Knowledge base cleared.")
            return True

        return False

    def _speak_sync(self, text: str):
        if not text:
            return
        self.ui.show_speaking()
        try:
            self.speaker.speak(text)
        except Exception as e:
            logger.error(f"Speech error: {e}")

    def _shutdown(self):
        self._running = False
        shutdown_line = random.choice(SHUTDOWN_LINES)
        self.ui.jarvis_response(shutdown_line)
        self._speak_sync(shutdown_line)
        if hasattr(self, "_wake_detector"):
            self._wake_detector.stop()
        sys.exit(0)
