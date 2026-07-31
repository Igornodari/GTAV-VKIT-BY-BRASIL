import sys
import threading
import types

import pytest

from tools import autoclicker as ac


class FakeSoundManager:
    def __init__(self):
        self.calls = []

    def play_on(self):
        self.calls.append("on")

    def play_off(self):
        self.calls.append("off")

    def play_toggle(self):
        self.calls.append("toggle")


class FakeMouseButton:
    left = "left"


class FakeMouseController:
    def __init__(self):
        self.events = []

    def press(self, button):
        self.events.append(("press", button))

    def release(self, button):
        self.events.append(("release", button))


class FakeMouseModule:
    Button = FakeMouseButton
    Controller = FakeMouseController


class FakeKeyboard:
    """Stand-in for the `keyboard` package used by the spammers."""

    def __init__(self, tab_held=True):
        self.tab_held = tab_held
        self.events = []
        self.pressed = threading.Event()

    def is_pressed(self, key):
        return key == "tab" and self.tab_held

    def press(self, key):
        self.events.append(("press", key))
        self.pressed.set()

    def release(self, key):
        self.events.append(("release", key))


@pytest.fixture
def sound():
    return FakeSoundManager()


@pytest.fixture
def fake_mouse(monkeypatch):
    """Force the pynput code path so the tests behave the same everywhere."""
    monkeypatch.setattr(ac, "PYDIRECTINPUT_AVAILABLE", False)
    monkeypatch.setattr(ac, "mouse", FakeMouseModule, raising=False)
    return FakeMouseModule


@pytest.fixture
def fake_keyboard(monkeypatch):
    fake = FakeKeyboard()
    monkeypatch.setattr(ac, "KEYBOARD_AVAILABLE", True)
    monkeypatch.setattr(ac, "keyboard", fake, raising=False)
    return fake


def _wait_for(predicate, timeout=2.0):
    step = 0.01
    waited = 0.0
    ticker = threading.Event()
    while waited < timeout:
        if predicate():
            return True
        ticker.wait(step)
        waited += step
    return False


# ---------------------------------------------------------------- AutoClicker


def test_autoclicker_starts_and_stops(sound, fake_mouse):
    clicker = ac.AutoClicker(sound)
    clicker.clicks_per_second = 1000

    clicker.start()
    assert clicker.active is True
    assert _wait_for(lambda: clicker.mouse_controller.events)

    clicker.stop()
    assert clicker.active is False
    assert clicker.thread.is_alive() is False
    assert sound.calls == ["on", "off"]


def test_autoclicker_click_presses_and_releases_left_button(sound, fake_mouse):
    clicker = ac.AutoClicker(sound)
    clicker._pynput_click()
    assert clicker.mouse_controller.events == [
        ("press", "left"),
        ("release", "left"),
    ]


def test_autoclicker_start_is_idempotent(sound, fake_mouse):
    clicker = ac.AutoClicker(sound)
    clicker.start()
    first_thread = clicker.thread
    clicker.start()
    assert clicker.thread is first_thread
    clicker.stop()
    assert sound.calls == ["on", "off"]


def test_autoclicker_stop_when_idle_does_nothing(sound, fake_mouse):
    clicker = ac.AutoClicker(sound)
    clicker.stop()
    assert clicker.active is False
    assert sound.calls == []


def test_autoclicker_toggle_flips_state(sound, fake_mouse):
    clicker = ac.AutoClicker(sound)
    clicker.toggle()
    assert clicker.active is True
    clicker.toggle()
    assert clicker.active is False


def test_autoclicker_loop_exits_on_click_error(sound, fake_mouse, monkeypatch):
    clicker = ac.AutoClicker(sound)
    monkeypatch.setattr(
        clicker, "_pynput_click", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    clicker.start()
    assert _wait_for(lambda: not clicker.thread.is_alive())
    clicker.stop()


# --------------------------------------------------------------- SnackSpammer


def test_snack_spammer_spams_c_while_tab_is_held(sound, fake_keyboard):
    spammer = ac.SnackSpammer(sound)
    spammer.spam_delay = 0.001

    spammer.start()
    assert fake_keyboard.pressed.wait(2.0)
    spammer.stop()

    assert ("press", "c") in fake_keyboard.events
    assert ("release", "c") in fake_keyboard.events
    assert spammer.active is False
    assert sound.calls == ["on", "off"]


def test_snack_spammer_does_not_press_when_tab_is_released(sound, fake_keyboard):
    fake_keyboard.tab_held = False
    spammer = ac.SnackSpammer(sound)
    spammer.spam_delay = 0.001

    spammer.start()
    assert not fake_keyboard.pressed.wait(0.1)
    spammer.stop()
    assert fake_keyboard.events == []


def test_snack_spammer_refuses_to_start_without_keyboard_module(sound, monkeypatch):
    monkeypatch.setattr(ac, "KEYBOARD_AVAILABLE", False)
    spammer = ac.SnackSpammer(sound)
    spammer.start()
    assert spammer.active is False
    assert spammer.thread is None
    assert sound.calls == []


# ---------------------------------------------------------- ArmorSnackSpammer


def test_armor_snack_spammer_alternates_v_and_c(sound, fake_keyboard):
    spammer = ac.ArmorSnackSpammer(sound)
    spammer.spam_delay = 0.001

    spammer.start()
    assert _wait_for(lambda: len(fake_keyboard.events) >= 4)
    spammer.stop()

    presses = [key for action, key in fake_keyboard.events if action == "press"]
    assert presses[:2] == ["v", "c"]


def test_armor_snack_tap_returns_false_when_stopping(sound, fake_keyboard):
    spammer = ac.ArmorSnackSpammer(sound)
    spammer.spam_delay = 0.001
    spammer.stop_event.set()

    assert spammer._tap("v") is False
    assert fake_keyboard.events == [("press", "v"), ("release", "v")]


def test_armor_snack_spammer_refuses_to_start_without_keyboard_module(
    sound, monkeypatch
):
    monkeypatch.setattr(ac, "KEYBOARD_AVAILABLE", False)
    spammer = ac.ArmorSnackSpammer(sound)
    spammer.start()
    assert spammer.active is False
    assert sound.calls == []


# -------------------------------------------------------------------- AntiAFK


def test_anti_afk_start_stop_cycle(sound, monkeypatch):
    afk = ac.AntiAFK(sound)
    # replace the key-holding loop: it only sleeps until asked to stop
    monkeypatch.setattr(afk, "_hold_keys", lambda: afk.stop_event.wait(5))

    afk.start()
    assert afk.active is True
    afk.stop()
    assert afk.active is False
    assert afk.thread.is_alive() is False
    assert sound.calls == ["on", "off"]


def test_anti_afk_toggle_is_symmetric(sound, monkeypatch):
    afk = ac.AntiAFK(sound)
    monkeypatch.setattr(afk, "_hold_keys", lambda: afk.stop_event.wait(5))

    afk.toggle()
    assert afk.active is True
    afk.toggle()
    assert afk.active is False


def test_anti_afk_stop_when_idle_does_nothing(sound):
    afk = ac.AntiAFK(sound)
    afk.stop()
    assert afk.active is False
    assert sound.calls == []


class ScriptedStopEvent:
    """Stop event whose waits follow a script, so the Anti-AFK loop runs a
    fixed number of iterations instead of sleeping for 20-30 real seconds."""

    def __init__(self, waits):
        self.waits = list(waits)
        self.stopped = False

    def is_set(self):
        return self.stopped

    def wait(self, timeout=None):
        result = self.waits.pop(0) if self.waits else True
        self.stopped = result
        return result

    def set(self):
        self.stopped = True

    def clear(self):
        self.stopped = False


class FakePDI:
    def __init__(self):
        self.events = []

    def keyDown(self, key):
        self.events.append(("down", key))

    def keyUp(self, key):
        self.events.append(("up", key))


def test_anti_afk_directinput_loop_alternates_and_releases(sound, monkeypatch):
    pdi = FakePDI()
    monkeypatch.setattr(ac, "PYDIRECTINPUT_AVAILABLE", True)
    monkeypatch.setitem(sys.modules, "pydirectinput", pdi)

    afk = ac.AntiAFK(sound)
    afk.stop_event = ScriptedStopEvent([False, True])
    afk._hold_keys()

    assert pdi.events[:2] == [("down", "s"), ("down", "d")]
    assert ("up", "d") in pdi.events and ("down", "a") in pdi.events
    assert pdi.events[-3:] == [("up", "s"), ("up", "d"), ("up", "a")]


def test_anti_afk_pynput_loop_alternates_and_releases(sound, monkeypatch):
    events = []

    class FakeController:
        def press(self, key):
            events.append(("press", key))

        def release(self, key):
            events.append(("release", key))

    fake_module = types.ModuleType("pynput.keyboard")
    fake_module.Controller = FakeController

    monkeypatch.setattr(ac, "PYDIRECTINPUT_AVAILABLE", False)
    monkeypatch.setattr(ac, "KEYBOARD_AVAILABLE", True)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", fake_module)

    afk = ac.AntiAFK(sound)
    afk.stop_event = ScriptedStopEvent([False, True])
    afk._hold_keys()

    assert events[:2] == [("press", "s"), ("press", "d")]
    assert ("release", "d") in events and ("press", "a") in events
    assert events[-3:] == [("release", "s"), ("release", "d"), ("release", "a")]


def test_anti_afk_reports_when_no_input_backend_exists(sound, monkeypatch):
    monkeypatch.setattr(ac, "PYDIRECTINPUT_AVAILABLE", False)
    monkeypatch.setattr(ac, "KEYBOARD_AVAILABLE", False)

    ac.AntiAFK(sound)._hold_keys()  # must not raise


def test_anti_afk_release_all_keys_uses_directinput_when_available(sound, monkeypatch):
    pdi = FakePDI()
    monkeypatch.setattr(ac, "PYDIRECTINPUT_AVAILABLE", True)
    monkeypatch.setitem(sys.modules, "pydirectinput", pdi)

    ac.AntiAFK(sound)._release_all_keys()
    assert pdi.events == [("up", "s"), ("up", "d"), ("up", "a")]
