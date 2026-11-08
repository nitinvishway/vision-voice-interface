# Hands-Free Laptop Control 

Touchless control of your laptop using the built-in webcam (hand gestures)
and microphone (voice commands). No IR blaster is used — this laptop only
has an **IR camera** (for Windows Hello face login), not an IR transmitter,
so remote-control-style IR signaling isn't physically possible here without
an external USB IR blaster dongle.

## What it does

| Input | Action |
|---|---|
| Point with index finger | Move cursor |
| Pinch thumb + index | Left click / double click (if pinched twice quickly) |
| Pinch thumb + middle (clearly closer to middle than to index) | Right click |
| Index + middle fingers extended, drag **vertically** | Scroll up/down |
| Index + middle fingers extended, drag **horizontally** | Browser back / forward |
| Closed fist, hold ~0.6s | Reload page (F5) |
| Thumb extended alone, move up/down | Volume up / down |
| Voice: "back", "forward", "reload", "click", "scroll up/down", "select all", "copy", "paste", "volume up/down", "mute", "enter", "escape" | Same actions, hands-free |
| Voice: "type hello there" | Types "hello there" |
| `Ctrl+Alt+G` | Toggle everything on/off |

Toggling off fully stops the camera and mic threads, so idle memory use is
just the small tray-icon process.

## Setup

1. **Install Python 3.14** (or any 3.10+). As of mediapipe 1.0.x and vosk's cffi-based
   wheels, all dependencies here install cleanly on 3.14 — no need to fall back to an
   older interpreter.

2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

3. **Download the hand-tracking model** (required for gestures):
   ```
   mkdir models
   curl -L -o models\hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
   ```
   mediapipe 1.0+ moved to a "Tasks" API that no longer bundles this model
   inside the pip package, so it has to be fetched separately, once.

4. **Download the voice model** (only needed if you want voice commands):
   - Go to https://alphacephei.com/vosk/models
   - Download `vosk-model-small-en-us-0.15.zip` (~40MB)
   - Unzip it into the same `models/` folder from step 3, so you have:
     `hands-free-control/models/vosk-model-small-en-us-0.15/...`
   - If you skip this step, gestures still work; voice commands just log an
     error and stay disabled.

5. **Run it:**
   ```
   python main.py
   ```
   A gray tray icon appears. Press `Ctrl+Alt+G` (or right-click the icon →
   Toggle) to turn it green and start listening.

## Tuning

All thresholds live in `config.py` — no need to touch engine code:
- `CURSOR_SMOOTHING` — lower = smoother but laggier cursor.
- `PINCH_CLICK_THRESHOLD` / `PINCH_RIGHTCLICK_THRESHOLD` — how close
  fingers must get to register a click. Increase if clicks aren't
  triggering, decrease if they fire accidentally.
- `SWIPE_MIN_VELOCITY` — how fast an open-hand swipe must be for back/forward.
- `FIST_HOLD_SECONDS` — how long to hold a fist before reload fires.
- `FRAME_WIDTH` / `FRAME_HEIGHT` — lower resolution = less CPU/memory, at
  the cost of tracking precision in poor lighting.

## Memory footprint notes

- MediaPipe runs with `model_complexity=0` (its lightest hand-tracking
  model) and tracks only one hand.
- Camera capture is downscaled to 320×240 by default.
- `pynput` is used instead of `pyautogui`, avoiding Pillow/pyscreeze's
  extra overhead for mouse/keyboard control.
- Vosk's *small* model (~40MB on disk, modest RAM) is used instead of the
  full model (~1.8GB) — good enough for short commands, not for long
  free-form dictation accuracy.
- Everything shuts down when toggled off, so you only pay the cost while
  actively using it.

## Known limitations

- Gesture accuracy depends on lighting and camera angle — you'll likely
  need to nudge a threshold or two in `config.py` for your setup.
- Voice recognition is offline and lightweight, so it's tuned for short
  commands rather than accurate long dictation.
- This has not been tested on real hardware in this environment — treat
  the gesture thresholds as a starting point, not a final calibration.
