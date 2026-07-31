import numpy as np
import pytest
from PIL import Image

from solvers import cayofingerprint


@pytest.fixture
def parts():
    """Eight distinguishable grayscale "fingerprint pieces"."""
    rng = np.random.default_rng(seed=1312)
    return [rng.integers(0, 256, size=(60, 80), dtype=np.uint8) for _ in range(8)]


def test_index_finds_the_matching_part(parts):
    for expected in range(len(parts)):
        needle = parts[expected][10:50, 10:70].copy()
        assert cayofingerprint.index(needle, parts) == expected


def test_index_returns_minus_one_when_nothing_matches(parts):
    rng = np.random.default_rng(seed=7)
    needle = rng.integers(0, 256, size=(40, 60), dtype=np.uint8)

    assert cayofingerprint.index(needle, parts) == -1


def test_index_returns_minus_one_for_empty_part_list():
    rng = np.random.default_rng(seed=7)
    needle = rng.integers(0, 256, size=(40, 60), dtype=np.uint8)

    assert cayofingerprint.index(needle, []) == -1


@pytest.fixture
def solver_screen(monkeypatch):
    """Feed main() a blank 1080p frame and record the keys it plays."""
    keys = []

    class FakeImageGrab:
        @staticmethod
        def grab(bbox):
            return Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))

    class FakeKeyboard:
        @staticmethod
        def press_and_release(key):
            keys.append(key)

    monkeypatch.setattr(cayofingerprint, "ImageGrab", FakeImageGrab)
    monkeypatch.setattr(cayofingerprint, "keyboard", FakeKeyboard)
    monkeypatch.setattr(cayofingerprint.time, "sleep", lambda _: None)
    return keys


def test_main_plays_nothing_when_every_piece_is_already_in_place(
    solver_screen, monkeypatch
):
    rows = iter(range(8))
    monkeypatch.setattr(cayofingerprint, "index", lambda part, parts: next(rows))

    cayofingerprint.main((0, 0, 1920, 1080))

    assert solver_screen == []


def test_main_walks_each_piece_the_short_way_around(solver_screen, monkeypatch):
    # every piece sits one slot below where it belongs, including the wrap
    rows = iter((i + 1) % 8 for i in range(8))
    monkeypatch.setattr(cayofingerprint, "index", lambda part, parts: next(rows))

    cayofingerprint.main((0, 0, 1920, 1080))

    assert solver_screen == ["a", "s"] * 7 + ["a"]


def test_main_moves_right_when_that_is_the_shorter_direction(
    solver_screen, monkeypatch
):
    # only the first piece is misplaced, three slots above its target
    rows = iter([5, 1, 2, 3, 4, 5, 6, 7])
    monkeypatch.setattr(cayofingerprint, "index", lambda part, parts: next(rows))

    cayofingerprint.main((0, 0, 1920, 1080))

    assert solver_screen == ["d", "d", "d"]


def test_scan_and_target_regions_stay_aligned():
    assert len(cayofingerprint.scan) == len(cayofingerprint.targets) == 8
    # the left-hand scan strips are stacked 76px apart
    tops = [region[1] for region in cayofingerprint.scan]
    assert tops == [360 + 76 * i for i in range(8)]
