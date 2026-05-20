"""
Jarvis TTS (Text-to-Speech) engine.
Primary: edge-tts (Microsoft Neural TTS — en-GB-RyanNeural sounds closest to Jarvis)
Fallback: pyttsx3 (offline, lower quality)
"""
import asyncio
import io
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger("jarvis.speaker")


class Speaker:
    def __init__(self, voice: str = "en-GB-RyanNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self._engine = None
        self._use_edge = True
        self._init()

    def _init(self):
        try:
            import edge_tts  # noqa: F401
            self._use_edge = True
            logger.info(f"TTS: edge-tts initialized with voice '{self.voice}'")
        except ImportError:
            self._use_edge = False
            logger.warning("edge-tts not available, falling back to pyttsx3")
            self._init_pyttsx3()

    def _init_pyttsx3(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            # Try to find a British voice
            voices = self._engine.getProperty("voices")
            for v in voices:
                if "english" in v.name.lower() and ("uk" in v.id.lower() or "gb" in v.id.lower()):
                    self._engine.setProperty("voice", v.id)
                    break
            self._engine.setProperty("rate", 185)   # Slightly faster than default
            self._engine.setProperty("volume", 0.95)
            logger.info("TTS: pyttsx3 initialized")
        except Exception as e:
            logger.error(f"TTS init failed: {e}")

    async def speak_async(self, text: str):
        """Speak text asynchronously."""
        if not text or not text.strip():
            return

        if self._use_edge:
            await self._speak_edge(text)
        else:
            await asyncio.get_event_loop().run_in_executor(None, self._speak_pyttsx3, text)

    def speak(self, text: str):
        """Synchronous speak (blocks until done)."""
        if not text or not text.strip():
            return
        asyncio.run(self.speak_async(text))

    async def _speak_edge(self, text: str):
        """Use edge-tts for high-quality neural speech."""
        try:
            import edge_tts
            import pygame

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )

            # Stream to temp file, then play
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name

            await communicate.save(tmp_path)
            await self._play_audio(tmp_path)

            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            await asyncio.get_event_loop().run_in_executor(None, self._speak_pyttsx3, text)

    async def _play_audio(self, path: str):
        """Play audio file using pygame."""
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            # Fallback: try using system command
            import subprocess, platform
            system = platform.system()
            try:
                if system == "Windows":
                    subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"], check=True)
                elif system == "Darwin":
                    subprocess.run(["afplay", path], check=True)
                else:
                    subprocess.run(["mpg123", "-q", path], check=True)
            except Exception as e2:
                logger.error(f"Fallback playback also failed: {e2}")

    def _speak_pyttsx3(self, text: str):
        """pyttsx3 fallback."""
        try:
            if self._engine:
                self._engine.say(text)
                self._engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")

    async def list_voices(self) -> list[str]:
        """List available edge-tts voices (filtered to English)."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [v["ShortName"] for v in voices if v["Locale"].startswith("en")]
        except Exception:
            return []

    def set_voice(self, voice: str):
        self.voice = voice

    def set_rate(self, rate: str):
        """Rate like '+10%' or '-5%'."""
        self.rate = rate
