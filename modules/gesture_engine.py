"""
Webcam-based gesture engine. Maps one hand's landmarks to touchpad-like
actions: move, click, double-click, right-click, scroll, back/forward
(two-finger horizontal drag), fist-hold reload, thumb-up/down volume.

Runs as its own thread; call start() / stop(). Designed to be lean:
- single hand tracked (MP_MAX_NUM_HANDS = 1)
- small capture resolution

Uses mediapipe's Tasks API (HandLandmarker). mediapipe 1.0+ removed the old
mp.solutions.hands API entirely, so this needs the hand_landmarker.task
model file downloaded separately -- see README for the download step.
"""

import math
import os
import time
import threading
import logging

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarksConnections,
    RunningMode,
    drawing_styles,
    drawing_utils,
)

import config
from modules import cursor_control as cc

log = logging.getLogger("gesture_engine")

# MediaPipe landmark indices we care about
THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP = 4, 8, 12, 16, 20
THUMB_IP, INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP = 3, 6, 10, 14, 18
WRIST = 0


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _finger_extended(landmarks, tip_idx, pip_idx):
    # A finger is "extended" if its tip is meaningfully above (smaller y than)
    # its pip joint, in image-normalized coordinates.
    return landmarks[tip_idx].y < landmarks[pip_idx].y - 0.02


def _thumb_extended(landmarks):
    # Thumb moves sideways rather than up/down; compare x distance from wrist
    # relative to the palm's general orientation instead of y.
    return abs(landmarks[THUMB_TIP].x - landmarks[WRIST].x) > \
        abs(landmarks[THUMB_IP].x - landmarks[WRIST].x) + 0.02


class GestureEngine:
    def __init__(self):
        self._running = False
        self._thread = None

        self._landmarker = None
        self._cap = None
        self._video_timestamp_ms = 0

        # State for smoothing / debouncing
        self._smoothed_xy = None
        self._last_pinch_time = 0.0
        self._pinch_active = False
        self._rightclick_active = False
        self._twofinger_prev_x = None
        self._twofinger_prev_y = None
        self._twofinger_prev_t = None
        self._last_swipe_time = 0.0
        self._fist_start_time = None
        self._last_reload_time = 0.0
        self._last_volume_time = 0.0
        self._thumb_prev_y = None
        self._debug_label = "No hand detected"

    # ---------------- lifecycle ----------------

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("Gesture engine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        log.info("Gesture engine stopped")

    # ---------------- main loop ----------------

    def _run(self):
        if not os.path.isfile(config.HAND_LANDMARKER_MODEL_PATH):
            log.error(
                "Hand landmarker model not found at %s. Download it with:\n"
                "  curl -L -o %s "
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                "hand_landmarker/float16/latest/hand_landmarker.task",
                config.HAND_LANDMARKER_MODEL_PATH, config.HAND_LANDMARKER_MODEL_PATH,
            )
            self._running = False
            return

        self._cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=config.HAND_LANDMARKER_MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_hands=config.MP_MAX_NUM_HANDS,
            min_hand_detection_confidence=config.MP_MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MP_MIN_TRACKING_CONFIDENCE,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

        frame_count = 0
        try:
            while self._running:
                ok, frame = self._cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame_count += 1
                if frame_count % config.PROCESS_EVERY_N_FRAMES != 0:
                    continue

                if config.MIRROR_PREVIEW:
                    frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                # detect_for_video requires strictly increasing timestamps;
                # a simple counter is more robust than wall-clock time here
                # since two frames could otherwise land on the same millisecond.
                self._video_timestamp_ms += 1
                result = self._landmarker.detect_for_video(
                    mp_image, self._video_timestamp_ms
                )

                if result.hand_landmarks:
                    landmarks = result.hand_landmarks[0]
                    self._process_landmarks(landmarks)
                else:
                    self._reset_transient_state()

                if config.SHOW_DEBUG_WINDOW:
                    if not self._draw_debug_frame(frame,
                                                    result.hand_landmarks[0]
                                                    if result.hand_landmarks else None):
                        break  # 'q' pressed in preview window
        finally:
            if self._cap:
                self._cap.release()
            if self._landmarker:
                self._landmarker.close()
            if config.SHOW_DEBUG_WINDOW:
                cv2.destroyWindow(config.DEBUG_WINDOW_NAME)

    def _reset_transient_state(self):
        self._pinch_active = False
        self._rightclick_active = False
        self._twofinger_prev_x = None
        self._twofinger_prev_y = None
        self._twofinger_prev_t = None
        self._fist_start_time = None
        self._thumb_prev_y = None
        self._debug_label = "No hand detected"

    # ---------------- debug preview ----------------

    def _draw_debug_frame(self, frame, landmarks):
        """Draws landmarks + the current gesture label onto frame and shows
        it in a window. Returns False if the user pressed 'q' to close it."""
        if landmarks is not None:
            drawing_utils.draw_landmarks(
                frame,
                landmarks,
                HandLandmarksConnections.HAND_CONNECTIONS,
                drawing_styles.get_default_hand_landmarks_style(),
                drawing_styles.get_default_hand_connections_style(),
            )

        cv2.putText(frame, self._debug_label, (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Press 'q' to close preview", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        cv2.imshow(config.DEBUG_WINDOW_NAME, frame)
        return cv2.waitKey(1) & 0xFF != ord('q')

    # ---------------- gesture classification ----------------

    def _process_landmarks(self, lm):
        now = time.time()

        index_ext = _finger_extended(lm, INDEX_TIP, INDEX_PIP)
        middle_ext = _finger_extended(lm, MIDDLE_TIP, MIDDLE_PIP)
        ring_ext = _finger_extended(lm, RING_TIP, RING_PIP)
        pinky_ext = _finger_extended(lm, PINKY_TIP, PINKY_PIP)
        thumb_ext = _thumb_extended(lm)

        pinch_index_dist = _dist(lm[THUMB_TIP], lm[INDEX_TIP])
        pinch_middle_dist = _dist(lm[THUMB_TIP], lm[MIDDLE_TIP])

        num_extended = sum([index_ext, middle_ext, ring_ext, pinky_ext])

        # ---- Fist hold -> reload ----
        if num_extended == 0 and not thumb_ext:
            if self._fist_start_time is None:
                self._fist_start_time = now
            hold_time = now - self._fist_start_time
            self._debug_label = f"Fist held {hold_time:.1f}s (reload at {config.FIST_HOLD_SECONDS}s)"
            if hold_time >= config.FIST_HOLD_SECONDS and \
                    (now - self._last_reload_time) >= config.RELOAD_COOLDOWN:
                cc.reload_page()
                self._last_reload_time = now
                self._fist_start_time = None
                self._debug_label = "Reload triggered"
            return
        else:
            self._fist_start_time = None

        # ---- Two-finger gesture (index + middle extended, ring/pinky curled):
        #      horizontal drag -> back/forward, vertical drag -> scroll.
        #      Whichever direction dominates each movement wins, like a
        #      touchpad's scroll vs. edge-swipe distinction. ----
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            avg_x = (lm[INDEX_TIP].x + lm[MIDDLE_TIP].x) / 2
            avg_y = (lm[INDEX_TIP].y + lm[MIDDLE_TIP].y) / 2
            self._debug_label = "Two-finger mode (drag L/R = back/forward, up/down = scroll)"

            if self._twofinger_prev_x is not None:
                dt = max(now - self._twofinger_prev_t, 1e-3)
                dx = avg_x - self._twofinger_prev_x
                dy = avg_y - self._twofinger_prev_y
                vx, vy = dx / dt, dy / dt

                if abs(vx) > abs(vy) and abs(vx) > config.SWIPE_MIN_VELOCITY and \
                        (now - self._last_swipe_time) >= config.SWIPE_COOLDOWN:
                    if vx > 0:
                        cc.browser_forward()
                        self._debug_label = "Two-finger swipe -> Forward"
                    else:
                        cc.browser_back()
                        self._debug_label = "Two-finger swipe -> Back"
                    self._last_swipe_time = now
                elif abs(dy) > config.SCROLL_DEADZONE:
                    cc.scroll(int(-dy * config.SCROLL_SENSITIVITY))
                    self._debug_label = "Scrolling " + ("up" if dy < 0 else "down")

            self._twofinger_prev_x, self._twofinger_prev_y = avg_x, avg_y
            self._twofinger_prev_t = now
            return
        else:
            self._twofinger_prev_x = None
            self._twofinger_prev_y = None
            self._twofinger_prev_t = None

        # ---- Thumb up/down -> volume (thumb extended alone) ----
        if thumb_ext and not index_ext and not middle_ext and not ring_ext and not pinky_ext:
            thumb_y = lm[THUMB_TIP].y
            self._debug_label = "Thumb mode (move up/down for volume)"
            if self._thumb_prev_y is not None:
                delta = thumb_y - self._thumb_prev_y
                if (now - self._last_volume_time) >= config.VOLUME_GESTURE_COOLDOWN:
                    if delta < -0.015:
                        cc.volume_up()
                        self._last_volume_time = now
                        self._debug_label = "Volume up"
                    elif delta > 0.015:
                        cc.volume_down()
                        self._last_volume_time = now
                        self._debug_label = "Volume down"
            self._thumb_prev_y = thumb_y
            return
        else:
            self._thumb_prev_y = None

        # ---- Pointing (index only) -> cursor move / pinch clicks ----
        if index_ext and not middle_ext:
            self._update_cursor(lm[INDEX_TIP].x, lm[INDEX_TIP].y)
            self._debug_label = "Pointing (move cursor)"

            is_left_pinch = pinch_index_dist < config.PINCH_CLICK_THRESHOLD
            # Only count as a right-click pinch if the thumb is clearly
            # closer to the middle finger than to the index finger -- during
            # a normal left-click pinch the thumb often brushes near the
            # middle finger too, so a plain distance threshold alone
            # misfires. The margin plus "not also a left pinch" check fixes
            # that false-trigger.
            is_right_pinch = (
                pinch_middle_dist < config.PINCH_RIGHTCLICK_THRESHOLD
                and pinch_middle_dist + config.RIGHTCLICK_DISAMBIGUATION_MARGIN < pinch_index_dist
                and not is_left_pinch
            )

            if is_right_pinch:
                if not self._rightclick_active:
                    cc.right_click()
                    self._rightclick_active = True
                    self._debug_label = "Right click"
            else:
                self._rightclick_active = False

            if is_left_pinch:
                if not self._pinch_active:
                    if (now - self._last_pinch_time) <= config.DOUBLE_CLICK_WINDOW:
                        cc.double_click()
                        self._debug_label = "Double click"
                    else:
                        cc.left_click()
                        self._debug_label = "Left click"
                    self._last_pinch_time = now
                    self._pinch_active = True
            else:
                self._pinch_active = False
        else:
            self._debug_label = "Hand detected (no gesture matched)"

    def _update_cursor(self, x, y):
        margin = config.CURSOR_MARGIN
        x = min(max((x - margin) / (1 - 2 * margin), 0.0), 1.0)
        y = min(max((y - margin) / (1 - 2 * margin), 0.0), 1.0)

        if self._smoothed_xy is None:
            self._smoothed_xy = (x, y)
        else:
            sx, sy = self._smoothed_xy
            a = config.CURSOR_SMOOTHING
            self._smoothed_xy = (sx + (x - sx) * a, sy + (y - sy) * a)

        cc.move_cursor(*self._smoothed_xy)
