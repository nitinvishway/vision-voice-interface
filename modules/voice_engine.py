"""
Offline voice command engine using Vosk's small English model (~40MB).
No internet required, low memory vs. cloud speech APIs. Handles short
commands (back, forward, reload, click, select all...) plus a "type <text>"
dictation mode.

The Vosk model is NOT bundled here (it's tens of MB) — download it once:
  https://alphacephei.com/vosk/models  ->  vosk-model-small-en-us-0.15
and unzip it to the path set in config.VOSK_MODEL_PATH.
"""

import json
import logging
import os
import queue
import threading

import sounddevice as sd
from vosk import Model, KaldiRecognizer

import config
from modules import cursor_control as cc

log = logging.getLogger("voice_engine")

# Command phrase -> action. Checked as substring matches against the
# recognized text, longest phrases first so "scroll down" wins over "down".
_COMMANDS = [
    ("double click", cc.double_click),
    ("right click", cc.right_click),
    ("left click", cc.left_click),
    ("click", cc.left_click),
    ("scroll up", lambda: cc.scroll(5)),
    ("scroll down", lambda: cc.scroll(-5)),
    ("go back", cc.browser_back),
    ("back", cc.browser_back),
    ("go forward", cc.browser_forward),
    ("forward", cc.browser_forward),
    ("reload", cc.reload_page),
    ("refresh", cc.reload_page),
    ("volume up", cc.volume_up),
    ("volume down", cc.volume_down),
    ("mute", cc.volume_mute),
    ("brightness up", cc.brightness_up),
    ("brightness down", cc.brightness_down),
    ("select all", cc.select_all),
    ("copy", cc.copy),
    ("paste", cc.paste),
    ("enter", lambda: cc.press_key("enter")),
    ("escape", lambda: cc.press_key("esc")),
    ("tab", lambda: cc.press_key("tab")),
]


class VoiceEngine:
    def __init__(self):
        self._running = False
        self._thread = None
        self._audio_q = queue.Queue()
        self._model = None
        self._stream = None

    def start(self):
        if self._running:
            return
        if not os.path.isdir(config.VOSK_MODEL_PATH):
            log.error(
                "Vosk model not found at %s. Download it from "
                "https://alphacephei.com/vosk/models and unzip it there.",
                config.VOSK_MODEL_PATH,
            )
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("Voice engine started")

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if self._thread:
            self._thread.join(timeout=2)
        log.info("Voice engine stopped")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            log.debug("Audio status: %s", status)
        self._audio_q.put(bytes(indata))

    def _run(self):
        self._model = Model(config.VOSK_MODEL_PATH)
        recognizer = KaldiRecognizer(self._model, config.VOICE_SAMPLE_RATE)

        self._stream = sd.RawInputStream(
            samplerate=config.VOICE_SAMPLE_RATE,
            blocksize=8000,
            device=config.MIC_DEVICE_INDEX,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
        )
        self._stream.start()

        while self._running:
            try:
                data = self._audio_q.get(timeout=0.5)
            except queue.Empty:
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip().lower()
                if text:
                    self._handle_text(text)

    def _handle_text(self, text: str):
        log.info("Heard: %s", text)

        if text.startswith("type "):
            cc.type_text(text[len("type "):])
            return

        for phrase, action in _COMMANDS:
            if phrase in text:
                action()
                return
