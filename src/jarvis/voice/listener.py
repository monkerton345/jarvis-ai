"""
Jarvis STT (Speech-to-Text) engine.
Uses faster-whisper for local, offline, accurate transcription.
Falls back to SpeechRecognition + Google if whisper not available.
"""
import asyncio
import logging
import numpy as np
import queue
import threading
import time
from typing import Optional, Callable

logger = logging.getLogger("jarvis.listener")


class Listener:
    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_record_seconds: int = 30,
        sample_rate: int = 16000,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_record_seconds = max_record_seconds
        self.sample_rate = sample_rate

        self._model = None
        self._use_whisper = True
        self._audio_queue = queue.Queue()
        self._is_listening = False

        self._load_model()

    def _load_model(self):
        """Load the whisper model (lazy, on first use)."""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model '{self.model_size}' on {self.device}...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._use_whisper = True
            logger.info("Whisper model loaded.")
        except ImportError:
            logger.warning("faster-whisper not installed. Falling back to SpeechRecognition.")
            self._use_whisper = False
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self._use_whisper = False

    def listen_once(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Record audio until silence, then transcribe.
        Returns transcribed text or None on failure.
        """
        try:
            import sounddevice as sd

            frames = []
            silent_frames = 0
            speaking = False
            sample_size = int(self.sample_rate * 0.1)  # 100ms chunks
            silence_chunks = int(self.silence_duration / 0.1)
            max_chunks = int(self.max_record_seconds / 0.1)

            logger.debug("Listening...")

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=sample_size,
            ) as stream:
                start = time.time()
                while True:
                    if timeout and (time.time() - start) > timeout:
                        break
                    if len(frames) > max_chunks:
                        break

                    data, _ = stream.read(sample_size)
                    rms = float(np.sqrt(np.mean(data ** 2)))

                    if rms > self.silence_threshold:
                        speaking = True
                        silent_frames = 0
                        frames.append(data.copy())
                    elif speaking:
                        silent_frames += 1
                        frames.append(data.copy())
                        if silent_frames >= silence_chunks:
                            break
                    # If haven't started speaking yet, keep waiting

            if not frames or not speaking:
                return None

            audio = np.concatenate(frames, axis=0).flatten()
            return self._transcribe(audio)

        except Exception as e:
            logger.error(f"Listen error: {e}")
            return self._fallback_listen()

    def _transcribe(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe audio array to text using Whisper."""
        if self._use_whisper and self._model:
            try:
                segments, info = self._model.transcribe(
                    audio,
                    beam_size=5,
                    language="en",
                    vad_filter=True,
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                logger.debug(f"Transcribed: '{text}'")
                return text if text else None
            except Exception as e:
                logger.error(f"Whisper transcription error: {e}")

        return self._fallback_transcribe(audio)

    def _fallback_listen(self) -> Optional[str]:
        """Fallback using SpeechRecognition + Google STT."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                logger.debug("Listening (fallback)...")
                audio = r.listen(source, timeout=10, phrase_time_limit=30)
            text = r.recognize_google(audio)
            return text.strip() if text else None
        except Exception as e:
            logger.error(f"Fallback STT error: {e}")
            return None

    def _fallback_transcribe(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe using Google via SpeechRecognition."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            audio_bytes = (audio * 32767).astype(np.int16).tobytes()
            audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
            return r.recognize_google(audio_data)
        except Exception as e:
            logger.error(f"Fallback transcription error: {e}")
            return None

    def set_silence_threshold(self, value: float):
        self.silence_threshold = value

    @property
    def is_whisper_loaded(self) -> bool:
        return self._use_whisper and self._model is not None
