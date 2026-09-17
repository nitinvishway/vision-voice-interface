"""
Tray icon + global hotkey. This is the thing that actually stays resident:
everything else (camera, mediapipe, mic, vosk) only spins up once you
toggle the system on, and fully tears down when you toggle it off, so idle
memory use stays minimal.
"""

import logging
import threading

import keyboard as kb  # global hotkey listener
import pystray
from PIL import Image, ImageDraw

import config
from modules.gesture_engine import GestureEngine
from modules.voice_engine import VoiceEngine

log = logging.getLogger("tray_app")


def _make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return img


class TrayApp:
    def __init__(self):
        self._enabled = False
        self._gesture_engine = GestureEngine()
        self._voice_engine = VoiceEngine()
        self._icon = pystray.Icon(
            "hands_free_control",
            icon=_make_icon("gray"),
            title="Hands-Free Control (off)",
            menu=pystray.Menu(
                pystray.MenuItem("Toggle (Ctrl+Alt+G)", self._toggle),
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    def _toggle(self, icon=None, item=None):
        self._enabled = not self._enabled
        if self._enabled:
            self._gesture_engine.start()
            self._voice_engine.start()
            self._icon.icon = _make_icon("green")
            self._icon.title = "Hands-Free Control (on)"
            log.info("Enabled")
        else:
            self._gesture_engine.stop()
            self._voice_engine.stop()
            self._icon.icon = _make_icon("gray")
            self._icon.title = "Hands-Free Control (off)"
            log.info("Disabled")

    def _quit(self, icon, item):
        if self._enabled:
            self._toggle()
        self._icon.stop()

    def run(self):
        kb.add_hotkey(config.TOGGLE_HOTKEY, self._toggle)
        log.info("Global hotkey '%s' registered. Right-click tray icon to quit.",
                  config.TOGGLE_HOTKEY)
        self._icon.run()
