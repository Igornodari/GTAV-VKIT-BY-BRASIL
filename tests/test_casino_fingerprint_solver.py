import cv2
import numpy as np
import pytest
from PIL import Image

from solvers import casinofingerprint
from solvers.casinofingerprint import find_shortest_solution

ROWS, COLS = 4, 2
STEP = {"s": (0, 1), "d": (1, 0), "w": (0, -1), "a": (-1, 0)}


def _apply_move(pos, key):
    """Mirror the exact wrap logic used by find_shortest_solution's BFS."""
    x, y = pos
    dx, dy = STEP[key]
    x, y = x + dx, y + dy
    if x == -1:
        x, y = COLS - 1, y - 1
    elif x == COLS:
        x, y = 0, y + 1
    y %= ROWS
    return (x, y)


def _simulate(moves):
    """Replay a move sequence, returning the cells flagged by 'return'."""
    pos = (0, 0)
    reached = set()
    for move in moves:
        if move == "tab":
            continue
        if move == "return":
            reached.add(pos)
            continue
        pos = _apply_move(pos, move)
    return reached


def test_ends_with_tab():
    moves = find_shortest_solution([(0, 0)])
    assert moves[-1] == "tab"


def test_visits_target_at_origin_with_no_movement():
    moves = find_shortest_solution([(0, 0)])
    assert _simulate(moves) == {(0, 0)}
    assert moves == ["return", "tab"]


def test_visits_adjacent_target_in_one_step():
    moves = find_shortest_solution([(1, 0)])
    assert _simulate(moves) == {(1, 0)}
    # shortest path to an orthogonal neighbour is a single move + return + tab
    assert len(moves) == 3


def test_visits_all_of_multiple_targets():
    targets = [(1, 0), (0, 2)]
    moves = find_shortest_solution(targets)
    assert _simulate(moves) == set(targets)


def test_wraps_around_grid_edges():
    # column wraps from x=-1 back to the last column, one row up
    targets = [(1, 3)]
    moves = find_shortest_solution(targets)
    assert _simulate(moves) == {(1, 3)}


def _noise_image(seed, size=(400, 300)):
    rng = np.random.default_rng(seed)
    return Image.fromarray(
        rng.integers(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)
    )


def test_is_in_finds_a_patch_of_the_same_screen():
    screen = _noise_image(seed=99)
    gray = cv2.cvtColor(np.array(screen), cv2.COLOR_BGR2GRAY)

    assert casinofingerprint.is_in(gray, screen.crop((50, 40, 150, 140))) is True


def test_is_in_rejects_an_unrelated_patch():
    gray = cv2.cvtColor(np.array(_noise_image(seed=99)), cv2.COLOR_BGR2GRAY)

    assert casinofingerprint.is_in(gray, _noise_image(seed=7, size=(100, 100))) is False


@pytest.fixture
def fingerprint_screen(monkeypatch):
    """Feed main() a blank frame and record the keys it plays."""
    keys = []

    class FakeImageGrab:
        @staticmethod
        def grab(bbox):
            return Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))

    class FakeKeyboard:
        @staticmethod
        def press_and_release(key):
            keys.append(key)

    monkeypatch.setattr(casinofingerprint, "ImageGrab", FakeImageGrab)
    monkeypatch.setattr(casinofingerprint, "keyboard", FakeKeyboard)
    monkeypatch.setattr(casinofingerprint.time, "sleep", lambda _: None)
    return keys


def test_main_plays_the_path_to_the_matching_prints(fingerprint_screen, monkeypatch):
    # only the top-left print, at (0, 0), matches
    matches = iter([True] + [False] * 7)
    monkeypatch.setattr(casinofingerprint, "is_in", lambda img, sub: next(matches))

    casinofingerprint.main((0, 0, 1920, 1080))

    assert fingerprint_screen == ["return", "tab"]


def test_main_bails_out_when_nothing_matches(fingerprint_screen, monkeypatch):
    monkeypatch.setattr(casinofingerprint, "is_in", lambda img, sub: False)

    casinofingerprint.main((0, 0, 1920, 1080))

    assert fingerprint_screen == []
