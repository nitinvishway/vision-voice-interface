"""
Thin wrapper around pynput for all output actions: moving the cursor,
clicking, scrolling, and sending keyboard shortcuts. Kept in one place so
both the gesture engine and the voice engine call the same, tested paths.

pynput is used instead of pyautogui because it has no Pillow/pyscreeze
dependency chain, which keeps the resident memory footprint noticeably
smaller for a background/always-on tool.
"""

from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

try:
    import screen_brightness_control as sbc
    _HAS_BRIGHTNESS = True
except Exception:
    _HAS_BRIGHTNESS = False

_mouse = MouseController()
_keyboard = KeyboardController()


def get_screen_size():
    # pynput doesn't expose screen size directly; use ctypes on Windows.
    import ctypes
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


_SCREEN_W, _SCREEN_H = get_screen_size()


def move_cursor(norm_x: float, norm_y: float):
    """norm_x, norm_y are 0-1 floats from the gesture engine."""
    x = int(norm_x * _SCREEN_W)
    y = int(norm_y * _SCREEN_H)
    _mouse.position = (x, y)


def left_click():
    _mouse.click(Button.left, 1)


def double_click():
    _mouse.click(Button.left, 2)


def right_click():
    _mouse.click(Button.right, 1)


def scroll(dy: int):
    """Positive dy scrolls up, negative scrolls down (matches touchpad feel)."""
    _mouse.scroll(0, dy)


def browser_back():
    _keyboard.press(Key.alt)
    _keyboard.press(Key.left)
    _keyboard.release(Key.left)
    _keyboard.release(Key.alt)


def browser_forward():
    _keyboard.press(Key.alt)
    _keyboard.press(Key.right)
    _keyboard.release(Key.right)
    _keyboard.release(Key.alt)


def reload_page():
    _keyboard.press(Key.f5)
    _keyboard.release(Key.f5)


def volume_up():
    _keyboard.press(Key.media_volume_up)
    _keyboard.release(Key.media_volume_up)


def volume_down():
    _keyboard.press(Key.media_volume_down)
    _keyboard.release(Key.media_volume_down)


def volume_mute():
    _keyboard.press(Key.media_volume_mute)
    _keyboard.release(Key.media_volume_mute)


def brightness_up(step=10):
    if not _HAS_BRIGHTNESS:
        return
    try:
        current = sbc.get_brightness(display=0)[0]
        sbc.set_brightness(min(100, current + step))
    except Exception:
        pass


def brightness_down(step=10):
    if not _HAS_BRIGHTNESS:
        return
    try:
        current = sbc.get_brightness(display=0)[0]
        sbc.set_brightness(max(0, current - step))
    except Exception:
        pass


def type_text(text: str):
    _keyboard.type(text)


def press_key(key_name: str):
    """Press a named special key, e.g. 'enter', 'esc', 'tab'."""
    key = getattr(Key, key_name, None)
    if key is None:
        return
    _keyboard.press(key)
    _keyboard.release(key)


def select_all():
    with _keyboard.pressed(Key.ctrl):
        _keyboard.press('a')
        _keyboard.release('a')


def copy():
    with _keyboard.pressed(Key.ctrl):
        _keyboard.press('c')
        _keyboard.release('c')


def paste():
    with _keyboard.pressed(Key.ctrl):
        _keyboard.press('v')
        _keyboard.release('v')
