import numpy as np
import pytest
from PIL import Image

from solvers import casinokeypad
from solvers.casinokeypad import calculate_key_sequence


def test_repeated_digit_only_presses_enter():
    moves = calculate_key_sequence([1, 1, 1, 1, 1, 1])
    assert moves == ["1", "return"] * 6


def test_max_swing_between_lowest_and_highest_digit():
    moves = calculate_key_sequence([5, 1, 5, 1, 5, 1])
    assert moves == [
        "s", "s", "s", "s", "return",
        "w", "w", "w", "w", "return",
        "s", "s", "s", "s", "return",
        "w", "w", "w", "w", "return",
        "s", "s", "s", "s", "return",
        "w", "w", "w", "w", "return",
    ]


def test_mixed_up_down_and_repeat_moves():
    moves = calculate_key_sequence([3, 2, 4, 4, 1, 5])
    assert moves == [
        "s", "s", "return",
        "w", "return",
        "s", "s", "return",
        "1", "return",
        "w", "w", "w", "return",
        "s", "s", "s", "s", "return",
    ]


CROP_LEFT, CROP_TOP = casinokeypad.tofind[0], casinokeypad.tofind[1]
CROP_WIDTH = casinokeypad.tofind[2] - CROP_LEFT
CROP_HEIGHT = casinokeypad.tofind[3] - CROP_TOP

# pixel check_ready() polls, in full-frame coordinates
READY_X, READY_Y = CROP_LEFT + 44, CROP_TOP + 92


def _blank_mask():
    return np.zeros((CROP_HEIGHT, CROP_WIDTH), dtype=np.uint8)


def _lit(mask, column, digit):
    """Light up the dot that dot_check() reads for `digit` in `column`."""
    y, x = casinokeypad.height[digit - 1], casinokeypad.length[column]
    mask[y - 20 : y + 20, x - 20 : x + 20] = 255
    return mask


@pytest.mark.parametrize("digit", [1, 2, 3, 4, 5])
def test_dot_check_reads_each_digit(digit):
    assert casinokeypad.dot_check(0, _lit(_blank_mask(), 0, digit)) == digit


def test_dot_check_rejects_an_empty_column():
    with pytest.raises(KeyError):
        casinokeypad.dot_check(0, _blank_mask())


def _frame_showing(digits, ready=True):
    """Render a 1080p keypad screen with a cyan dot per detected digit."""
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    for column, digit in enumerate(digits):
        y = CROP_TOP + casinokeypad.height[digit - 1]
        x = CROP_LEFT + casinokeypad.length[column]
        frame[y - 20 : y + 20, x - 20 : x + 20] = (0, 255, 255)  # cyan
    if ready:
        frame[READY_Y, READY_X] = (255, 255, 255)
    return Image.fromarray(frame)


@pytest.fixture
def keypad_screen(monkeypatch):
    """Serve rendered frames to the solver and record the keys it plays."""
    frames = {"queue": []}
    keys = []

    class FakeImageGrab:
        @staticmethod
        def grab(bbox):
            return frames["queue"].pop(0) if len(frames["queue"]) > 1 else frames["queue"][0]

    class FakeKeyboard:
        @staticmethod
        def press_and_release(key):
            keys.append(key)

    monkeypatch.setattr(casinokeypad, "ImageGrab", FakeImageGrab)
    monkeypatch.setattr(casinokeypad, "keyboard", FakeKeyboard)
    monkeypatch.setattr(casinokeypad.time, "sleep", lambda _: None)
    return frames, keys


def test_check_ready_waits_for_the_prompt(keypad_screen):
    frames, keys = keypad_screen
    frames["queue"] = [_frame_showing([1] * 6, ready=False), _frame_showing([1] * 6)]

    casinokeypad.check_ready((0, 0, 1920, 1080))

    assert keys == ["w"]  # one nudge while the keypad was not ready yet


def test_main_reads_the_keypad_and_plays_the_sequence(keypad_screen):
    frames, keys = keypad_screen
    frames["queue"] = [_frame_showing([1, 2, 3, 4, 5, 5])]

    casinokeypad.main((0, 0, 1920, 1080))

    assert keys == casinokeypad.calculate_key_sequence([1, 2, 3, 4, 5, 5])


def test_main_reports_an_unreadable_keypad(keypad_screen):
    frames, keys = keypad_screen
    frames["queue"] = [Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))]

    casinokeypad.main((0, 0, 1920, 1080))

    assert keys == []
