"""
Wake word detection for Jarvis.
Listens continuously for "Jarvis" or "Hey Jarvis" before activating.

Strategy:
1. openwakeword (free, local, good accuracy) — preferred
2. Keyword-in-STT (runs whisper/google continuously) — reliable fallback
3. Keyboard hotkey (always available) — manual fallback
"""
import asyncio
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("jarvis.wake_word")


class WakeWordDetector:
    def __init__(
        self,
        wake_words: list[str] = None,
        on_wake: Optional[Callable] = None,
        hotkey: str = "ctrl+shift+j",
    ):
        self.wake_words = [w.lower() for w in (wake_words or ["jarvis", "hey jarvis"])]
        self.on_wake = on_wake
        self.hotkey = hotkey
        self._running = False
        self._method = None
        self._quick_model = None
        self._detect_method()

    def _detect_method(self):
        """Determine best available wake word method."""
        try:
            import openwakeword  # noqa: F401
            self._method = "openwakeword"
            logger.info("Wake word: openwakeword")
        except ImportError:
            try:
                self._method = "continuous_stt"
                logger.info("Wake word: continuous STT (slower but functional)")
                import faster_whisper  # noqa: F401
            except ImportError:
                import keyboard  # noqa: F401
                self._method = "hotkey"
                logger.info(f"Wake word: hotkey ({self.hotkey})")

    def start(self, on_wake: Optional[Callable] = None):
        """Start listening for wake word in background."""
        if on_wake:
            self.on_wake = on_wake
        self._running = True

        if self._method == "openwakeword":
            t = threading.Thread(target=self._run_openwakeword, daemon=True)
        elif self._method == "hotkey":
            t = threading.Thread(target=self._run_hotkey, daemon=True)
        else:
            t = threading.Thread(target=self._run_continuous_stt, daemon=True)

        t.start()
        return t

    def stop(self):
        self._running = False

    def _run_openwakeword(self):
        """Use openwakeword for wake detection."""
        try:
            import openwakeword
            from openwakeword.model import Model
            import sounddevice as sd
            import numpy as np

            oww_model = Model(inference_framework="onnx")
            chunk_size = 1280

            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype=np.int16,
                blocksize=chunk_size,
            ) as stream:
                logger.info("Wake word detector active (openwakeword)")
                while self._running:
                    audio_chunk, _ = stream.read(chunk_size)
                    audio_flat = audio_chunk.flatten()
                    predictions = oww_model.predict(audio_flat)
                    for model_name, score in predictions.items():
                        if score > 0.5:
                            logger.info(f"Wake word detected (score={score:.2f})")
                            if self.on_wake:
                                self.on_wake()
                            time.sleep(1)  # Cooldown
        except Exception as e:
            logger.error(f"openwakeword error: {e}, falling back to hotkey")
            self._method = "hotkey"
            self._run_hotkey()

    def _run_hotkey(self):
        """Use keyboard hotkey to trigger wake."""
        try:
            import keyboard
            logger.info(f"Press {self.hotkey} to activate Jarvis")
            while self._running:
                if keyboard.is_pressed(self.hotkey):
                    if self.on_wake:
                        self.on_wake()
                    time.sleep(0.5)  # Debounce
                time.sleep(0.05)
        except Exception as e:
            logger.error(f"Hotkey error: {e}")

    def _run_continuous_stt(self):
        """
        Lightweight continuous listening — runs a cheap STT pass looking
        for the wake word in short audio snippets.
        """
        try:
            import sounddevice as sd
            import numpy as np

            sample_rate = 16000
            chunk_duration = 2.0  # seconds
            chunk_size = int(sample_rate * chunk_duration)
            silence_threshold = 0.005

            logger.info("Continuous STT wake word detector active")
            logger.info(f"Say one of: {self.wake_words}")

            while self._running:
                try:
                    audio_chunk, _ = sd.read(
                        chunk_size,
                        samplerate=sample_rate,
                        channels=1,
                        dtype="float32",
                    )
                    rms = float(np.sqrt(np.mean(audio_chunk ** 2)))
                    if rms < silence_threshold:
                        continue

                    text = self._quick_transcribe(audio_chunk.flatten(), sample_rate)
                    if text:
                        text_lower = text.lower()
                        for wake_word in self.wake_words:
                            if wake_word in text_lower:
                                logger.info(f"Wake word detected: '{text}'")
                                if self.on_wake:
                                    self.on_wake()
                                time.sleep(1)
                                break
                except Exception:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Continuous STT wake word error: {e}")

    def _quick_transcribe(self, audio: "np.ndarray", sample_rate: int) -> Optional[str]:
        """Fast transcription for wake word detection."""
        try:
            from faster_whisper import WhisperModel
            if self._quick_model is None:
                self._quick_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            segments, _ = self._quick_model.transcribe(audio, beam_size=1, language="en")
            return " ".join(s.text for s in segments).strip()
        except Exception:
            return None
