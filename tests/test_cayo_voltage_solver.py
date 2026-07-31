import numpy as np
import pytest
from PIL import Image

from solvers import cayovoltage


def _image_with(pattern, xs, ys):
    """Build a black frame where the pixels of `pattern` are lit at (xs, ys)."""
    img = np.zeros((1080, 1920), dtype=np.uint8)
    for bit, x, y in zip(pattern, xs, ys):
        if bit:
            img[y, x] = 255
    return img


@pytest.mark.parametrize("pattern,digit", sorted(cayovoltage.DIGITS_LOOKUP.items()))
def test_pixel_check_reads_every_seven_segment_digit(pattern, digit):
    xs = cayovoltage.target_number_length_0
    ys = cayovoltage.target_number_height
    img = _image_with(pattern, xs, ys)

    assert cayovoltage.pixel_check(xs, ys, img, cayovoltage.DIGITS_LOOKUP) == digit


@pytest.mark.parametrize("pattern,value", sorted(cayovoltage.RIGHT_SYMBOLS.items()))
def test_pixel_check_reads_right_hand_multiplier_symbols(pattern, value):
    xs = cayovoltage.right_symbol_length
    ys = cayovoltage.right_symbol_height_0
    img = _image_with(pattern, xs, ys)

    assert cayovoltage.pixel_check(xs, ys, img, cayovoltage.RIGHT_SYMBOLS) == value


def test_pixel_check_raises_on_unknown_segment_pattern():
    xs = cayovoltage.target_number_length_0
    ys = cayovoltage.target_number_height
    img = _image_with((0, 0, 0, 0, 0, 0, 0), xs, ys)

    with pytest.raises(KeyError):
        cayovoltage.pixel_check(xs, ys, img, cayovoltage.DIGITS_LOOKUP)


@pytest.fixture
def recorded_keys(monkeypatch):
    keys = []

    class FakeKeyboard:
        @staticmethod
        def press_and_release(key):
            keys.append(key)

    monkeypatch.setattr(cayovoltage, "keyboard", FakeKeyboard)
    monkeypatch.setattr(cayovoltage.time, "sleep", lambda _: None)
    return keys


def test_calculate_plays_the_identity_pairing(recorded_keys):
    left, right = [1, 2, 3], [1, 2, 10]
    # (1*1) + (2*2) + (3*10) = 35 -> pairs left[i] with right[i]
    cayovoltage.calculate(35, left, right)

    assert recorded_keys == cayovoltage.moves[(0, 0, 1, 1, 2, 2)]


def test_calculate_plays_a_crossed_pairing(recorded_keys):
    left, right = [1, 2, 3], [1, 2, 10]
    # (1*10) + (2*2) + (3*1) = 17 -> left[0]xright[2], left[1]xright[1], left[2]xright[0]
    cayovoltage.calculate(17, left, right)

    assert recorded_keys == cayovoltage.moves[(0, 2, 1, 1, 2, 0)]


def test_calculate_presses_nothing_when_no_pairing_matches(recorded_keys):
    cayovoltage.calculate(999, [1, 2, 3], [1, 2, 10])

    assert recorded_keys == []


def _screen_showing(target_digits, left_digits, right_values):
    """Render a 1080p frame of the voltage puzzle the solver can read back."""
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

    digit_pattern = {digit: pattern for pattern, digit in cayovoltage.DIGITS_LOOKUP.items()}
    symbol_pattern = {value: pattern for pattern, value in cayovoltage.RIGHT_SYMBOLS.items()}

    target_columns = [
        cayovoltage.target_number_length_0,
        cayovoltage.target_number_length_1,
        cayovoltage.target_number_length_2,
    ]
    for digit, xs in zip(target_digits, target_columns):
        for bit, x, y in zip(digit_pattern[digit], xs, cayovoltage.target_number_height):
            if bit:
                frame[y, x] = 255

    left_rows = [
        cayovoltage.left_number_height_0,
        cayovoltage.left_number_height_1,
        cayovoltage.left_number_height_2,
    ]
    for digit, ys in zip(left_digits, left_rows):
        for bit, x, y in zip(digit_pattern[digit], cayovoltage.left_number_length, ys):
            if bit:
                frame[y, x] = 255

    symbol_rows = [
        cayovoltage.right_symbol_height_0,
        cayovoltage.right_symbol_height_1,
        cayovoltage.right_symbol_height_2,
    ]
    for value, ys in zip(right_values, symbol_rows):
        for bit, x, y in zip(symbol_pattern[value], cayovoltage.right_symbol_length, ys):
            if bit:
                frame[y, x] = 255

    return Image.fromarray(frame)


@pytest.fixture
def screen(monkeypatch):
    """Let a test hand main() a rendered frame instead of a real screenshot."""
    holder = {}

    class FakeImageGrab:
        @staticmethod
        def grab(bbox):
            return holder["image"]

    monkeypatch.setattr(cayovoltage, "ImageGrab", FakeImageGrab)
    return holder


def test_main_reads_the_puzzle_and_plays_the_solution(screen, recorded_keys):
    screen["image"] = _screen_showing((0, 3, 5), (1, 2, 3), (1, 2, 10))

    cayovoltage.main((0, 0, 1920, 1080))

    assert recorded_keys == cayovoltage.moves[(0, 0, 1, 1, 2, 2)]


def test_main_gives_up_when_the_digits_are_unreadable(screen, recorded_keys):
    screen["image"] = Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))

    cayovoltage.main((0, 0, 1920, 1080))

    assert recorded_keys == []
