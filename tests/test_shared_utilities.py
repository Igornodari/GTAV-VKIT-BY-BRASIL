import threading

from core.ui import format_hotkey
from solvers import vision
from tools.base import ToggleableTool


def test_format_hotkey_uppercases_and_spaces_parts():
    assert format_hotkey("ctrl+shift+a") == "CTRL + SHIFT + A"


def test_format_hotkey_uses_placeholder_when_unset():
    assert format_hotkey("") == ""
    assert format_hotkey("", empty="—") == "—"


def test_format_moves_keeps_literal_keys_lowercase():
    assert vision.format_moves(["s", "d", "return", "tab"]) == "S → D → return → tab"
    assert vision.format_moves(["return"], literal=()) == "RETURN"


def test_play_keys_uses_per_key_delays(monkeypatch):
    pressed, slept = [], []
    monkeypatch.setattr(vision.keyboard, "press_and_release", pressed.append)
    monkeypatch.setattr(vision.time, "sleep", slept.append)

    vision.play_keys(["s", "return", "w"], {"s": 0.025, "return": 1.95})

    assert pressed == ["s", "return", "w"]
    assert slept == [0.025, 1.95]


def test_play_keys_uses_uniform_delay(monkeypatch):
    slept = []
    monkeypatch.setattr(vision.keyboard, "press_and_release", lambda key: None)
    monkeypatch.setattr(vision.time, "sleep", slept.append)

    vision.play_keys(["a", "b"], 0.03)

    assert slept == [0.03, 0.03]


class _SoundSpy:
    def __init__(self):
        self.events = []

    def play_on(self):
        self.events.append("on")

    def play_off(self):
        self.events.append("off")


class _CountingTool(ToggleableTool):
    name = "Counting"

    def __init__(self, sound_manager):
        super().__init__(sound_manager)
        self.started = threading.Event()

    def run(self):
        self.started.set()
        while self._running():
            if self.stop_event.wait(timeout=5):
                break


def test_toggle_starts_and_stops_worker_thread():
    sounds = _SoundSpy()
    tool = _CountingTool(sounds)

    tool.toggle()
    assert tool.started.wait(timeout=2)
    assert tool.active

    tool.toggle()
    assert not tool.active
    assert not tool.thread.is_alive()
    assert sounds.events == ["on", "off"]


def test_stop_is_a_noop_when_inactive():
    sounds = _SoundSpy()
    tool = _CountingTool(sounds)

    tool.stop()

    assert sounds.events == []
    assert tool.thread is None
