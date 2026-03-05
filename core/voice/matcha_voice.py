"""
MATCHA Voice v2 — Full voice I/O
Uses faster-whisper for STT (faster, lighter than original whisper)
Uses pyttsx3 as TTS fallback (works offline, no install needed)
Wake word: "Hey MATCHA"
"""

import os
import sys
import threading
import queue
import tempfile
import platform
import time

PLATFORM = platform.system()


class MatchaVoice:
    WAKE_WORD = "hey matcha"

    def __init__(self, on_input_callback=None):
        self.on_input = on_input_callback or (lambda x: print(f"[Voice] {x}"))
        self.listening = False
        self.active = False
        self._audio_queue = queue.Queue()
        self._stt = None
        self._tts = None
        self._init_tts()
        self._init_stt()

    def _init_stt(self):
        """Try faster-whisper first, then standard whisper, then SpeechRecognition."""
        # Try faster-whisper
        try:
            from faster_whisper import WhisperModel
            self._stt = WhisperModel("tiny", device="cpu", compute_type="int8")
            self._stt_type = "faster_whisper"
            print("[MATCHA Voice] STT: faster-whisper (tiny) ready.")
            return
        except ImportError:
            pass

        # Try openai-whisper
        try:
            import whisper
            self._stt = whisper.load_model("tiny")
            self._stt_type = "whisper"
            print("[MATCHA Voice] STT: Whisper (tiny) ready.")
            return
        except ImportError:
            pass

        # Try SpeechRecognition (Google, needs internet)
        try:
            import speech_recognition as sr
            self._stt = sr.Recognizer()
            self._stt_type = "sr"
            print("[MATCHA Voice] STT: SpeechRecognition ready (requires internet).")
            return
        except ImportError:
            pass

        print("[MATCHA Voice] No STT available. Voice input disabled.")
        self._stt_type = None

    def _init_tts(self):
        """Try pyttsx3 (offline), then gTTS (online)."""
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            # Configure Jarvis-like voice
            voices = self._tts.getProperty("voices")
            # Prefer male voice
            for voice in voices:
                if any(x in voice.name.lower() for x in ["male", "david", "daniel", "james", "alex"]):
                    self._tts.setProperty("voice", voice.id)
                    break
            self._tts.setProperty("rate", 175)    # Speed — calm, not rushed
            self._tts.setProperty("volume", 0.9)
            self._tts_type = "pyttsx3"
            print("[MATCHA Voice] TTS: pyttsx3 ready.")
            return
        except Exception:
            pass

        self._tts_type = "print"
        print("[MATCHA Voice] TTS: Text output only (install pyttsx3 for voice).")

    def speak(self, text: str):
        """MATCHA speaks. Calm, clear, Jarvis-like."""
        if not text:
            return

        print(f"[MATCHA] {text}")

        if self._tts_type == "pyttsx3":
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception as e:
                print(f"[MATCHA Voice] TTS error: {e}")

        elif self._tts_type == "gtts":
            try:
                from gtts import gTTS
                import pygame
                tts = gTTS(text=text, lang="en", slow=False)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    tts.save(f.name)
                    tmp = f.name
                pygame.mixer.init()
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                os.unlink(tmp)
            except Exception as e:
                print(f"[MATCHA Voice] gTTS error: {e}")

    def listen_once(self, duration: float = 5.0) -> str:
        """Record and transcribe one utterance."""
        if not self._stt_type:
            return ""

        if self._stt_type in ("faster_whisper", "whisper"):
            return self._listen_whisper(duration)
        elif self._stt_type == "sr":
            return self._listen_sr()
        return ""

    def _listen_whisper(self, duration: float) -> str:
        """Record audio and transcribe with Whisper."""
        try:
            import sounddevice as sd
            import numpy as np
            import scipy.io.wavfile as wav

            sample_rate = 16000
            print("[MATCHA Voice] Listening...")
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            wav.write(tmp, sample_rate, audio)

            if self._stt_type == "faster_whisper":
                segments, _ = self._stt.transcribe(tmp, language="en")
                text = " ".join(s.text for s in segments).strip()
            else:
                result = self._stt.transcribe(tmp)
                text = result["text"].strip()

            os.unlink(tmp)
            return text

        except Exception as e:
            print(f"[MATCHA Voice] Listen error: {e}")
            return ""

    def _listen_sr(self) -> str:
        """Listen using SpeechRecognition (Google STT)."""
        try:
            import speech_recognition as sr
            r = self._stt
            with sr.Microphone() as source:
                print("[MATCHA Voice] Listening...")
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
            return r.recognize_google(audio)
        except Exception as e:
            print(f"[MATCHA Voice] SR error: {e}")
            return ""

    def start_wake_word_detection(self):
        """Continuously listen for 'Hey MATCHA'."""
        self.listening = True
        thread = threading.Thread(target=self._wake_loop, daemon=True)
        thread.start()
        print(f"[MATCHA Voice] Wake word active — say '{self.WAKE_WORD}'")

    def _wake_loop(self):
        while self.listening:
            text = self.listen_once(duration=3)
            if text and self.WAKE_WORD in text.lower():
                self.speak("Ready.")
                command = self.listen_once(duration=6)
                if command:
                    self.on_input(command)
            time.sleep(0.1)

    def stop(self):
        self.listening = False
