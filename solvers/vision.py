"""
Screen capture, image processing and keystroke helpers shared by the solvers.

Every solver grabs the game window, normalizes it to 1080p, converts it to
grayscale (sometimes thresholded to black & white) and finally replays a list
of keys with per-key delays - those steps live here instead of being copied
into each solver.
"""

import time
from typing import Iterable, Mapping, Optional, Sequence, Union

import cv2
import keyboard
import numpy as np
from PIL import Image, ImageGrab

REFERENCE_SIZE = (1920, 1080)

Delays = Union[float, Mapping[str, float]]


def grab_screen(bbox, crop: Optional[Sequence[int]] = None) -> Image.Image:
    """Capture `bbox`, normalize it to 1080p and optionally crop a region."""
    with ImageGrab.grab(bbox) as raw:
        screen = raw.resize(REFERENCE_SIZE)

    if crop is None:
        return screen

    with screen:
        return screen.crop(crop)


def to_gray(image, color_space: int = cv2.COLOR_RGB2GRAY) -> np.ndarray:
    """Convert a PIL image (or array) to a grayscale array."""
    return cv2.cvtColor(np.array(image), color_space)


def to_black_and_white(image, threshold: int = 100, color_space: int = cv2.COLOR_RGB2GRAY) -> np.ndarray:
    """Convert an image to a binary (black & white) array."""
    _, black_and_white = cv2.threshold(
        to_gray(image, color_space), threshold, 255, cv2.THRESH_BINARY
    )
    return black_and_white


def scaled_gray(image: Image.Image, scale: float) -> np.ndarray:
    """Resize an image by `scale` and return it as a grayscale array."""
    resized = image.resize((round(image.size[0] * scale), round(image.size[1] * scale)))
    with resized:
        return to_gray(resized, cv2.COLOR_BGR2GRAY)


def format_moves(moves: Iterable[str], literal: Sequence[str] = ("return", "tab")) -> str:
    """Render a solution as an arrow-separated, upper-cased sequence."""
    return " → ".join(key if key in literal else key.upper() for key in moves)


def play_keys(moves: Iterable[str], delays: Delays = 0.0) -> None:
    """Replay a solution, sleeping after each key.

    `delays` is either a single delay applied to every key, or a mapping of
    key -> delay (keys missing from the mapping are not waited on).
    """
    for key in moves:
        keyboard.press_and_release(key)
        delay = delays if isinstance(delays, (int, float)) else delays.get(key, 0.0)
        if delay:
            time.sleep(delay)
