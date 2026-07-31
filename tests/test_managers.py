import ctypes
import subprocess
import types

import psutil
import pytest

from core import managers
from core.state import runtime


class InlineExecutor:
    """Runs submitted work synchronously so tests stay deterministic."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


class FakeOverlayManager:
    def __init__(self):
        self.status = None
        self.notifications = []

    def update_status(self, status):
        self.status = status

    def show_notification(self, title, message, color, duration=None):
        self.notifications.append((title, message, color))


class FakeSoundManager:
    def __init__(self):
        self.calls = []

    def play_on(self):
        self.calls.append("on")

    def play_off(self):
        self.calls.append("off")


class FakeProcess:
    def __init__(self, name, pid=1234):
        self.info = {"pid": pid, "name": name}
        self._name = name

    def name(self):
        return self._name


@pytest.fixture(autouse=True)
def inline_thread_pool(monkeypatch):
    monkeypatch.setattr(runtime, "thread_pool", InlineExecutor())


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(managers.time, "sleep", lambda _: None)


@pytest.fixture(autouse=True)
def no_window_flag(monkeypatch):
    # CREATE_NO_WINDOW only exists in subprocess on Windows
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)


@pytest.fixture
def run_calls(monkeypatch):
    """Capture every subprocess.run made by the managers, with a settable result."""
    calls = []
    result = types.SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return result

    monkeypatch.setattr(managers.subprocess, "run", fake_run)
    return calls, result


# ------------------------------------------------------------- GameDetector


def test_game_detector_returns_the_matching_process(monkeypatch):
    monkeypatch.setattr(
        managers.psutil,
        "process_iter",
        lambda attrs: [FakeProcess("explorer.exe"), FakeProcess("GTA5.exe")],
    )

    proc = managers.GameDetector().get_gta_process()
    assert proc.name() == "GTA5.exe"


def test_game_detector_skips_processes_that_vanish(monkeypatch):
    class VanishingProcess:
        @property
        def info(self):
            raise psutil.NoSuchProcess(pid=1)

    monkeypatch.setattr(
        managers.psutil,
        "process_iter",
        lambda attrs: [VanishingProcess(), FakeProcess("GTA5.exe")],
    )

    assert managers.GameDetector().get_gta_process().name() == "GTA5.exe"


def test_game_detector_times_out_when_game_never_starts(monkeypatch):
    monkeypatch.setattr(managers.psutil, "process_iter", lambda attrs: [])
    clock = iter([0.0, 0.0, 99.0])
    monkeypatch.setattr(managers.time, "time", lambda: next(clock))

    detector = managers.GameDetector(poll_interval=0, timeout=5)
    with pytest.raises(TimeoutError):
        detector.get_gta_process()


# ------------------------------------------------------- WindowFocusManager


@pytest.fixture
def focus_manager():
    return managers.WindowFocusManager(process_name="GTA5.exe")


def test_focus_manager_lowercases_the_process_name():
    assert managers.WindowFocusManager(process_name="GTA5.EXE").process_name == (
        "gta5.exe"
    )


@pytest.mark.parametrize(
    "process_name,title,expected",
    [
        ("gta5.exe", "anything", True),
        ("chrome.exe", "Grand Theft Auto V", True),
        ("chrome.exe", "ROCKSTAR GAMES Launcher", True),
        ("chrome.exe", "GitHub - Chrome", False),
        (None, "", False),
    ],
)
def test_check_is_gta(focus_manager, process_name, title, expected):
    assert focus_manager._check_is_gta(process_name, title) is expected


def test_get_window_info_caches_per_hwnd(focus_manager, monkeypatch):
    lookups = []

    monkeypatch.setattr(
        managers.win32gui,
        "GetWindowText",
        lambda hwnd: lookups.append(hwnd) or "Grand Theft Auto V",
    )
    monkeypatch.setattr(
        managers.win32process, "GetWindowThreadProcessId", lambda hwnd: (0, 42)
    )
    monkeypatch.setattr(managers.psutil, "Process", lambda pid: FakeProcess("GTA5.exe"))

    assert focus_manager._get_window_info(1) == ("gta5.exe", "Grand Theft Auto V")
    assert focus_manager._get_window_info(1) == ("gta5.exe", "Grand Theft Auto V")
    assert lookups == [1]  # second call served from cache


def test_get_window_info_tolerates_dead_processes(focus_manager, monkeypatch):
    monkeypatch.setattr(managers.win32gui, "GetWindowText", lambda hwnd: "Some window")
    monkeypatch.setattr(
        managers.win32process, "GetWindowThreadProcessId", lambda hwnd: (0, 42)
    )

    def boom(pid):
        raise psutil.NoSuchProcess(pid=pid)

    monkeypatch.setattr(managers.psutil, "Process", boom)

    assert focus_manager._get_window_info(7) == (None, "Some window")


def test_get_window_info_returns_blank_on_win32_failure(focus_manager, monkeypatch):
    def boom(hwnd):
        raise OSError("invalid window handle")

    monkeypatch.setattr(managers.win32gui, "GetWindowText", boom)

    assert focus_manager._get_window_info(7) == (None, "")


def test_focus_callbacks_only_fire_on_state_change(focus_manager, monkeypatch):
    monkeypatch.setattr(
        focus_manager, "_get_window_info", lambda hwnd: ("gta5.exe", "GTA V")
    )
    seen = []
    focus_manager.register_focus_callback(seen.append)

    focus_manager._on_window_focus_change(None, 0, 1, 0, 0, 0, 0)
    focus_manager._on_window_focus_change(None, 0, 1, 0, 0, 0, 0)

    assert seen == [True]
    assert focus_manager.is_gta_focused() is True


def test_focus_callback_errors_do_not_break_the_hook(focus_manager, monkeypatch):
    monkeypatch.setattr(
        focus_manager, "_get_window_info", lambda hwnd: ("gta5.exe", "GTA V")
    )

    def exploding_callback(is_focused):
        raise RuntimeError("callback blew up")

    focus_manager.register_focus_callback(exploding_callback)
    focus_manager._on_window_focus_change(None, 0, 1, 0, 0, 0, 0)

    assert focus_manager.is_gta_focused() is True


def test_hook_ignores_events_after_shutdown(focus_manager, monkeypatch):
    monkeypatch.setattr(
        focus_manager, "_get_window_info", lambda hwnd: ("gta5.exe", "GTA V")
    )
    focus_manager.stop_monitoring()
    focus_manager._on_window_focus_change(None, 0, 1, 0, 0, 0, 0)

    assert focus_manager.is_gta_focused() is False


def test_force_refresh_updates_state_and_notifies(focus_manager, monkeypatch):
    monkeypatch.setattr(managers.win32gui, "GetForegroundWindow", lambda: 5)
    monkeypatch.setattr(
        focus_manager, "_get_window_info", lambda hwnd: ("gta5.exe", "GTA V")
    )
    seen = []
    focus_manager.register_focus_callback(seen.append)

    assert focus_manager.force_refresh_focus_state() is True
    assert seen == [True]


def test_force_refresh_keeps_last_state_on_error(focus_manager, monkeypatch):
    def boom():
        raise OSError("no foreground window")

    monkeypatch.setattr(managers.win32gui, "GetForegroundWindow", boom)

    assert focus_manager.force_refresh_focus_state() is False


# ------------------------------------------------------------- SoundManager


def test_sound_manager_maps_existing_files_only(tmp_path):
    sounds_dir = tmp_path / "assets" / "sounds"
    sounds_dir.mkdir(parents=True)
    (sounds_dir / "on.wav").write_bytes(b"RIFF")

    manager = managers.SoundManager(tmp_path)

    assert manager.sounds["on"] == str(sounds_dir / "on.wav")
    assert manager.sounds["off"] is None
    assert manager.sounds["toggle"] is None


def test_sound_manager_creates_the_sounds_directory(tmp_path):
    managers.SoundManager(tmp_path)
    assert (tmp_path / "assets" / "sounds").is_dir()


def test_play_dispatches_only_known_and_present_sounds(tmp_path, monkeypatch):
    sounds_dir = tmp_path / "assets" / "sounds"
    sounds_dir.mkdir(parents=True)
    (sounds_dir / "on.wav").write_bytes(b"RIFF")

    played = []
    monkeypatch.setattr(
        managers.winsound, "PlaySound", lambda path, flags: played.append(path)
    )

    manager = managers.SoundManager(tmp_path)
    manager.play_on()
    manager.play_off()  # file missing - no-op
    manager.play("does-not-exist")

    assert played == [str(sounds_dir / "on.wav")]


def test_play_sound_swallows_backend_errors(monkeypatch):
    def boom(path, flags):
        raise RuntimeError("no audio device")

    monkeypatch.setattr(managers.winsound, "PlaySound", boom)
    managers.SoundManager._play_sound("whatever.wav")  # must not raise


# ---------------------------------------------------------- FirewallManager


@pytest.fixture
def firewall():
    return managers.FirewallManager("vkit_rule", "192.0.2.1", 80)


def test_rule_exists_reflects_powershell_exit_code(firewall, run_calls):
    calls, result = run_calls

    assert firewall.rule_exists() is True
    result.returncode = 1
    assert firewall.rule_exists() is False

    assert all(cmd[0] == "powershell.exe" for cmd in calls)
    assert "vkit_rule" in calls[0][-1]


def test_rule_exists_escapes_single_quotes_in_the_rule_name(run_calls):
    calls, _ = run_calls
    managers.FirewallManager("it's a rule", "192.0.2.1", 80).rule_exists()

    assert "it''s a rule" in calls[0][-1]


def test_test_ip_blocked_maps_connect_result(firewall, monkeypatch):
    class FakeSocket:
        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def settimeout(self, timeout):
            pass

        def connect_ex(self, address):
            return FakeSocket.result

    monkeypatch.setattr(managers.socket, "socket", FakeSocket)

    FakeSocket.result = 1
    assert firewall.test_ip_blocked() is True
    FakeSocket.result = 0
    assert firewall.test_ip_blocked() is False


def test_test_ip_blocked_treats_socket_errors_as_blocked(firewall, monkeypatch):
    def boom(*args):
        raise OSError("network unreachable")

    monkeypatch.setattr(managers.socket, "socket", boom)
    assert firewall.test_ip_blocked() is True


def test_add_rule_updates_overlay_and_plays_sound(firewall, run_calls, monkeypatch):
    calls, _ = run_calls
    monkeypatch.setattr(firewall, "test_ip_blocked", lambda: True)

    overlay, sound = FakeOverlayManager(), FakeSoundManager()
    firewall.add_rule(overlay, sound)

    assert any("advfirewall firewall add rule" in str(cmd) for cmd in calls)
    assert any("route add 192.0.2.1" in str(cmd) for cmd in calls)
    assert overlay.status == "ON"
    assert sound.calls == ["on"]


def test_add_rule_reports_failure_when_rule_is_missing(firewall, run_calls):
    _, result = run_calls
    result.returncode = 1  # rule_exists() -> False

    overlay, sound = FakeOverlayManager(), FakeSoundManager()
    firewall.add_rule(overlay, sound)

    assert overlay.status is None
    assert sound.calls == []


def test_delete_rule_clears_overlay_and_route(firewall, run_calls, monkeypatch):
    calls, result = run_calls
    result.returncode = 1  # rule_exists() -> False after deletion
    monkeypatch.setattr(firewall, "test_ip_blocked", lambda: False)

    overlay, sound = FakeOverlayManager(), FakeSoundManager()
    firewall.delete_rule(overlay, sound)

    assert any("advfirewall firewall delete rule" in str(cmd) for cmd in calls)
    assert any("route delete 192.0.2.1" in str(cmd) for cmd in calls)
    assert overlay.status == "OFF"
    assert sound.calls == ["off"]


def test_toggle_rule_deletes_when_present_and_adds_when_absent(firewall, monkeypatch):
    performed = []
    monkeypatch.setattr(firewall, "add_rule", lambda m, s: performed.append("add"))
    monkeypatch.setattr(
        firewall, "delete_rule", lambda m, s: performed.append("delete")
    )

    exists = iter([True, False])
    monkeypatch.setattr(firewall, "rule_exists", lambda: next(exists))

    firewall.toggle_rule(FakeOverlayManager(), FakeSoundManager())
    firewall.toggle_rule(FakeOverlayManager(), FakeSoundManager())

    assert performed == ["delete", "add"]


def test_cleanup_removes_a_leftover_rule(firewall, run_calls):
    calls, _ = run_calls

    assert firewall.cleanup() is True
    assert any("advfirewall firewall delete rule" in str(cmd) for cmd in calls)


def test_cleanup_is_a_noop_without_a_rule(firewall, run_calls):
    calls, result = run_calls
    result.returncode = 1

    assert firewall.cleanup() is False
    assert not any("advfirewall firewall delete rule" in str(cmd) for cmd in calls)


# ----------------------------------------------------------- ProcessManager


def test_is_admin_reflects_the_windows_api(monkeypatch):
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(shell32=types.SimpleNamespace(IsUserAnAdmin=lambda: 1)),
        raising=False,
    )
    assert managers.ProcessManager.is_admin() is True


def test_is_admin_is_false_when_the_api_is_unavailable(monkeypatch):
    class NoShell32:
        def __getattr__(self, name):
            raise AttributeError(name)

    monkeypatch.setattr(ctypes, "windll", NoShell32(), raising=False)
    assert managers.ProcessManager.is_admin() is False


def test_kill_process_notifies_on_success(run_calls):
    overlay = FakeOverlayManager()
    managers.ProcessManager.kill_process("GTA5.exe", overlay)

    assert overlay.notifications[0][0] == "PROCESS TERMINATED"


def test_kill_process_notifies_when_process_is_not_running(run_calls):
    _, result = run_calls
    result.returncode = 128

    overlay = FakeOverlayManager()
    managers.ProcessManager.kill_process("GTA5.exe", overlay)

    assert overlay.notifications[0][0] == "PROCESS NOT FOUND"


def test_kill_process_notifies_on_unexpected_errors(monkeypatch):
    def boom(cmd, **kwargs):
        raise OSError("taskkill missing")

    monkeypatch.setattr(managers.subprocess, "run", boom)

    overlay = FakeOverlayManager()
    managers.ProcessManager.kill_process("GTA5.exe", overlay)

    assert overlay.notifications[0][0] == "ERROR"


def test_run_as_admin_returns_immediately_when_already_elevated(monkeypatch, tmp_path):
    monkeypatch.setattr(managers.ProcessManager, "is_admin", staticmethod(lambda: True))
    managers.ProcessManager.run_as_admin(tmp_path)  # must not call sys.exit


def test_run_as_admin_elevates_and_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(
        managers.ProcessManager, "is_admin", staticmethod(lambda: False)
    )
    executed = []
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(
            shell32=types.SimpleNamespace(
                ShellExecuteW=lambda *args: executed.append(args)
            )
        ),
        raising=False,
    )

    with pytest.raises(SystemExit):
        managers.ProcessManager.run_as_admin(tmp_path)

    assert executed and executed[0][1] == "runas"
