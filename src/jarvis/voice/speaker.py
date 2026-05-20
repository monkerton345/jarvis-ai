"""
Jarvis TTS (Text-to-Speech) engine.
Primary: edge-tts (Microsoft Neural TTS — en-GB-RyanNeural sounds closest to Jarvis)
Fallback: pyttsx3 (offline, lower quality)
"""
import asyncio
import io
import logging
import os
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

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )

            # Stream audio bytes into memory first — avoids Windows file-lock
            # issue where edge-tts still holds the handle when pygame tries to open
            audio_chunks = []
            async for event in communicate.stream():
                if event[0] == "audio":
                    audio_chunks.append(event[1])

            if not audio_chunks:
                return

            audio_data = b"".join(audio_chunks)

            # Write to temp file with explicit flush+close so Windows fully
            # releases the handle before pygame (or the OS fallback) opens it
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(audio_data)
                    f.flush()
                    os.fsync(f.fileno())   # force OS buffer flush on Windows
                await self._play_audio(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            await asyncio.get_event_loop().run_in_executor(None, self._speak_pyttsx3, text)

    async def _play_audio(self, path: str):
        """
        Play audio file. Tries three methods in order:
          1. pygame / pygame-ce  (preferred — installed by requirements.txt)
          2. Windows Media Foundation via PowerShell  (Windows fallback, plays MP3)
          3. afplay / mpg123  (macOS / Linux fallback)
        """
        # -- Method 1: pygame (or pygame-ce drop-in) --------------------------
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
            return
        except Exception as e:
            logger.warning(f"pygame playback unavailable ({e}), trying system fallback")

        # -- Method 2 / 3: OS-level fallback ----------------------------------
        import subprocess, platform
        system = platform.system()
        try:
            if system == "Windows":
                # Use Windows Media Foundation — plays MP3/WAV/OGG natively
                ps_cmd = (
                    "$mp = [System.Windows.Media.MediaPlayer]::new(); "
                    f"$mp.Open([System.Uri]::new((Resolve-Path '{path}').Path)); "
                    "$mp.Play(); "
                    "Start-Sleep -Milliseconds 500; "
                    "while ($mp.NaturalDuration.HasTimeSpan -eq $false) { Start-Sleep -Milliseconds 50 }; "
                    "Start-Sleep -Seconds $mp.NaturalDuration.TimeSpan.TotalSeconds; "
                    "$mp.Close()"
                )
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ["powershell", "-NonInteractive", "-NoProfile", "-c", ps_cmd],
                        check=True, capture_output=True
                    )
                )
            elif system == "Darwin":
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: subprocess.run(["afplay", path], check=True)
                )
            else:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: subprocess.run(["mpg123", "-q", path], check=True)
                )
        except Exception as e2:
            logger.error(f"All audio playback methods failed: {e2}")

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
