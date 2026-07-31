import pytest
from pynput import keyboard

import main
from core.state import runtime
from main import AppConfig, HotkeyHandler


class InlineExecutor:
    """Runs submitted work synchronously so tests stay deterministic."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


class FakeFocusManager:
    def __init__(self, *args, **kwargs):
        self.focused = True
        self.callbacks = []
        self.monitoring = False

    def register_focus_callback(self, callback):
        self.callbacks.append(callback)

    def start_monitoring(self):
        self.monitoring = True

    def is_gta_focused(self):
        return self.focused

    def force_refresh_focus_state(self):
        return self.focused


class FakeTool:
    def __init__(self):
        self.active = False
        self.toggles = 0

    def toggle(self):
        self.toggles += 1
        self.active = not self.active

    def stop(self):
        self.active = False


class FakeOverlayManager:
    def __init__(self):
        self.notifications = []
        self.show_full = False
        self.mode_toggles = 0

    def show_notification(self, title, message, color, duration=None):
        self.notifications.append((title, message, color))

    def toggle_mode(self):
        self.mode_toggles += 1
        self.show_full = not self.show_full


class FakeSoundManager:
    def __init__(self):
        self.calls = []

    def play_on(self):
        self.calls.append("on")

    def play_off(self):
        self.calls.append("off")

    def play_toggle(self):
        self.calls.append("toggle")


class FakeFirewallManager:
    def __init__(self):
        self.toggles = 0
        self.cleaned = False

    def toggle_rule(self, manager, sound_manager):
        self.toggles += 1

    def cleanup(self):
        self.cleaned = True
        return False


class FakeSolverManager:
    def __init__(self):
        self.ran = []

    def casino_fingerprint(self):
        self.ran.append("casino_fingerprint")

    def casino_keypad(self):
        self.ran.append("casino_keypad")

    def cayo_fingerprint(self):
        self.ran.append("cayo_fingerprint")

    def cayo_voltage(self):
        self.ran.append("cayo_voltage")


class FakeExploitManager:
    def __init__(self):
        self.ran = []

    def job_warp(self):
        self.ran.append("job_warp")


class FakeSettingsWindow:
    def __init__(self):
        self.toggle_requests = 0

    def request_toggle(self):
        self.toggle_requests += 1


HOTKEYS = {
    "autoclicker": "ctrl+k",
    "armor_snack_combo": "ctrl+shift+k",
    "toggle_overlay": "ctrl+f8",
    "toggle_nosave": "ctrl+f9",
    "open_settings": "ctrl+f7",
    "casino_keypad": "f6",
}


@pytest.fixture(autouse=True)
def inline_thread_pool(monkeypatch):
    monkeypatch.setattr(runtime, "thread_pool", InlineExecutor())


@pytest.fixture
def handler(monkeypatch):
    monkeypatch.setattr(main, "WindowFocusManager", FakeFocusManager)

    config = AppConfig(
        rule_name="rule",
        remote_ip="192.0.2.1",
        test_port=80,
        hotkeys=dict(HOTKEYS),
        require_game_focus=True,
        auto_stop_on_unfocus=True,
    )

    handler = HotkeyHandler(
        config=config,
        manager=FakeOverlayManager(),
        sound_manager=FakeSoundManager(),
        firewall_manager=FakeFirewallManager(),
        autoclicker=FakeTool(),
        snack_spammer=FakeTool(),
        anti_afk=FakeTool(),
        armor_snack_spammer=FakeTool(),
        solver_manager=FakeSolverManager(),
        exploit_manager=FakeExploitManager(),
        settings_window=FakeSettingsWindow(),
    )
    return handler


def _press(handler, *keys):
    for key in keys:
        handler.on_press(key)


def _release(handler, *keys):
    for key in keys:
        handler.on_release(key)


CTRL = keyboard.Key.ctrl_l
SHIFT = keyboard.Key.shift_l
K = keyboard.KeyCode.from_char("k")


def test_registers_focus_callback_and_starts_monitoring(handler):
    assert handler.focus_manager.monitoring is True
    assert handler.focus_manager.callbacks == [handler._on_focus_change]


def test_hotkey_triggers_its_action(handler):
    _press(handler, CTRL, K)
    assert handler.autoclicker.toggles == 1
    assert handler.manager.notifications[-1][0] == "AUTO CLICKER ⚡"


def test_longest_matching_combo_wins(handler):
    _press(handler, CTRL, SHIFT, K)
    assert handler.armor_snack_spammer.toggles == 1
    assert handler.autoclicker.toggles == 0


def test_action_does_not_repeat_while_keys_are_held(handler):
    _press(handler, CTRL, K, K, K)
    assert handler.autoclicker.toggles == 1


def test_action_can_fire_again_after_release(handler):
    _press(handler, CTRL, K)
    _release(handler, K)
    _press(handler, K)
    assert handler.autoclicker.toggles == 2


def test_nothing_fires_while_the_game_is_unfocused(handler):
    handler.focus_manager.focused = False
    _press(handler, CTRL, K)
    assert handler.autoclicker.toggles == 0


def test_hotkeys_still_work_when_focus_is_not_required(handler):
    handler.require_game_focus = False
    handler.focus_manager.focused = False
    _press(handler, CTRL, K)
    assert handler.autoclicker.toggles == 1


def test_update_hotkey_rebinds_at_runtime(handler):
    handler.update_hotkey("autoclicker", "f6+ctrl")

    assert handler.config.hotkeys["autoclicker"] == "f6+ctrl"
    assert handler.hotkeys["autoclicker"] == HotkeyHandler._parse_hotkey("ctrl+f6")
    assert handler.current_keys == set()


def test_toggle_overlay_action_switches_mode_and_plays_sound(handler):
    _press(handler, CTRL, keyboard.Key.f8)

    assert handler.manager.mode_toggles == 1
    assert handler.sound_manager.calls == ["toggle"]
    assert handler.manager.notifications[-1][0] == "OVERLAY MODE"


def test_toggle_nosave_action_delegates_to_the_firewall(handler):
    _press(handler, CTRL, keyboard.Key.f9)
    assert handler.firewall_manager.toggles == 1


def test_open_settings_action_schedules_the_panel(handler):
    _press(handler, CTRL, keyboard.Key.f7)
    assert handler.settings_window.toggle_requests == 1


def test_open_settings_action_is_a_noop_without_a_panel(handler):
    handler.settings_window = None
    _press(handler, CTRL, keyboard.Key.f7)  # must not raise


def test_solver_hotkey_runs_the_solver(handler):
    _press(handler, keyboard.Key.f6)
    assert handler.solver_manager.ran == ["casino_keypad"]


def test_solver_action_errors_are_contained(handler):
    def boom():
        raise RuntimeError("solver exploded")

    handler.solver_manager.casino_keypad = boom
    _press(handler, keyboard.Key.f6)  # must not raise


def test_losing_focus_stops_active_tools_and_notifies(handler):
    handler.autoclicker.active = True
    handler.anti_afk.active = True

    handler._on_focus_change(False)

    assert handler.autoclicker.active is False
    assert handler.anti_afk.active is False
    title, message, _ = handler.manager.notifications[-1]
    assert title == "AUTO-STOPPED"
    assert "Auto Clicker" in message and "Anti-AFK" in message


def test_losing_focus_with_no_active_tools_is_silent(handler):
    handler._on_focus_change(False)
    assert handler.manager.notifications == []


def test_regaining_focus_clears_pending_keys_and_restarts_listener(handler, monkeypatch):
    restarts = []
    monkeypatch.setattr(handler, "_restart_listener", lambda: restarts.append(True))
    handler.current_keys.add(CTRL)
    handler.triggered.add("autoclicker")

    handler._on_focus_change(True)

    assert handler.current_keys == set()
    assert handler.triggered == set()
    assert restarts == [True]


def test_cleanup_stops_running_tools_and_removes_the_rule():
    running, idle = FakeTool(), FakeTool()
    running.active = True
    firewall = FakeFirewallManager()

    main.cleanup(running, idle, idle, idle, firewall)

    assert running.active is False
    assert firewall.cleaned is True
