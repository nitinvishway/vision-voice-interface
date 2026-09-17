"""
Central configuration. Tweak these to tune sensitivity for your lighting,
webcam, and hand size instead of touching the engine code.
"""

# ---------------- Hotkey ----------------
TOGGLE_HOTKEY = "ctrl+alt+g"          # press to turn the whole system on/off

# ---------------- Camera ----------------
CAMERA_INDEX = 0
FRAME_WIDTH = 320                     # keep small -> big memory/CPU savings
FRAME_HEIGHT = 240
PROCESS_EVERY_N_FRAMES = 1            # set to 2 to halve CPU load further
MIRROR_PREVIEW = True

# MediaPipe Hand Landmarker settings.
# Model file is not bundled in the pip package -- download once with:
#   curl -L -o models/hand_landmarker.task ^
#     https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
HAND_LANDMARKER_MODEL_PATH = "models/hand_landmarker.task"
MP_MAX_NUM_HANDS = 1
MP_MIN_DETECTION_CONFIDENCE = 0.6
MP_MIN_TRACKING_CONFIDENCE = 0.5

# ---------------- Cursor ----------------
CURSOR_SMOOTHING = 0.35               # 0=very smooth/laggy, 1=raw/jittery
CURSOR_MARGIN = 0.08                  # ignore outer 8% of frame (dead zone)

# ---------------- Gesture thresholds (normalized 0-1 coords) ----------------
PINCH_CLICK_THRESHOLD = 0.045         # thumb-index distance to count as pinch
PINCH_RIGHTCLICK_THRESHOLD = 0.045    # thumb-middle distance
RIGHTCLICK_DISAMBIGUATION_MARGIN = 0.015  # thumb must be this much closer to
                                           # middle than to index to count as
                                           # a right-click (prevents left-click
                                           # pinches from also firing right-click)
DOUBLE_CLICK_WINDOW = 0.35            # seconds between pinches to count as double

SCROLL_SENSITIVITY = 1800             # multiplier on vertical delta -> scroll units
SCROLL_DEADZONE = 0.004

# Two-finger (index+middle) horizontal drag speed needed to register as a
# back/forward swipe rather than scroll. Also reused as the direction-
# dominance check: whichever of vx/vy is larger decides swipe vs scroll.
SWIPE_MIN_VELOCITY = 0.9              # normalized-units/sec
SWIPE_COOLDOWN = 0.8                  # seconds before another swipe can fire

FIST_HOLD_SECONDS = 0.6               # how long a fist must be held to reload
RELOAD_COOLDOWN = 2.0

VOLUME_GESTURE_COOLDOWN = 0.25        # min seconds between volume steps

# ---------------- Debug preview ----------------
# Shows a live window with the camera feed, hand landmarks, and the
# currently-detected gesture overlaid -- handy while tuning thresholds above.
# Leave off for normal background use (it costs extra CPU/memory and pops a
# visible window). Press 'q' in the preview window to close it.
SHOW_DEBUG_WINDOW = False
DEBUG_WINDOW_NAME = "Hands-Free Control - Debug Preview"

# ---------------- Voice ----------------
VOSK_MODEL_PATH = "models/vosk-model-small-en-us-0.15"  # download separately
MIC_DEVICE_INDEX = None               # None = system default mic
VOICE_SAMPLE_RATE = 16000

# ---------------- Logging ----------------
LOG_LEVEL = "INFO"
