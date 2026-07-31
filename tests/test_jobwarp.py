import threading

import pytest

from exploits import jobwarp


class FakeKeyboard:
    def __init__(self):
        self.events = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))


class FakeManager:
    def __init__(self):
        self.notifications = []

    def show_notification(self, title, message, color, duration=None):
        self.notifications.append((title, message, color))


@pytest.fixture
def fake_keyboard(monkeypatch):
    fake = FakeKeyboard()
    monkeypatch.setattr(jobwarp, "keyboard", fake)
    monkeypatch.setattr(jobwarp.time, "sleep", lambda _: None)
    return fake


@pytest.fixture
def instant_countdown(monkeypatch):
    """Make the 40x1s countdown resolve immediately, keeping abort semantics."""
    monkeypatch.setattr(
        threading.Event, "wait", lambda self, timeout=None: self.is_set()
    )


@pytest.fixture(autouse=True)
def reset_module_state():
    """jobwarp keeps its run state in module globals."""
    yield
    jobwarp._running = False
    jobwarp._abort_event = None


def test_tap_key_presses_then_releases(fake_keyboard):
    jobwarp.tap_key("space")
    assert fake_keyboard.events == [("press", "space"), ("release", "space")]


def test_tap_key_swallows_backend_errors(monkeypatch):
    class Exploding:
        def press(self, key):
            raise RuntimeError("no keyboard backend")

        def release(self, key):
            raise RuntimeError("no keyboard backend")

    monkeypatch.setattr(jobwarp, "keyboard", Exploding())
    monkeypatch.setattr(jobwarp.time, "sleep", lambda _: None)

    jobwarp.tap_key("space")  # must not raise


def test_tap_combo_releases_in_reverse_order(fake_keyboard):
    jobwarp.tap_combo(["alt", "f4"])
    assert fake_keyboard.events == [
        ("press", "alt"),
        ("press", "f4"),
        ("release", "f4"),
        ("release", "alt"),
    ]


def test_main_runs_full_sequence_and_completes(fake_keyboard, instant_countdown):
    manager = FakeManager()
    jobwarp.main(manager=manager)

    keys = [key for action, key in fake_keyboard.events if action == "press"]
    assert keys[:4] == ["space", "enter", "alt", "f4"]
    assert keys[-1] == "esc"
    assert manager.notifications[-1][1] == "Job Warp Complete!"
    assert jobwarp._running is False


def test_main_without_manager_still_completes(fake_keyboard, instant_countdown):
    jobwarp.main()
    assert jobwarp._running is False


def test_call_while_running_signals_the_abort_event(fake_keyboard):
    jobwarp._running = True
    jobwarp._abort_event = threading.Event()

    manager = FakeManager()
    jobwarp.main(manager=manager)

    assert jobwarp._abort_event.is_set() is True
    assert manager.notifications == [
        ("JOB WARP", "Job Warp Cancelling...", "#f59e0b")
    ]
    assert fake_keyboard.events == []  # no new sequence was started


def test_aborted_countdown_presses_esc_and_reports_cancellation(
    fake_keyboard, monkeypatch
):
    # the countdown's very first wait reports "aborted"
    monkeypatch.setattr(threading.Event, "wait", lambda self, timeout=None: True)

    manager = FakeManager()
    jobwarp.main(manager=manager)

    assert ("press", "esc") in fake_keyboard.events
    assert manager.notifications[-1][1] == "Job Warp Cancelled"
    assert jobwarp._running is False


def test_main_reports_errors_without_raising(monkeypatch, instant_countdown):
    monkeypatch.setattr(jobwarp.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        jobwarp, "tap_key", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    manager = FakeManager()
    jobwarp.main(manager=manager)

    assert manager.notifications[-1][1] == "✗ Job Warp Error"
    assert jobwarp._running is False
