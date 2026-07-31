import io
import json

import pytest
from rich.console import Console

from core import ui as core_ui
from core.ui import HOTKEY_DESCRIPTIONS, UIManager, UpdateChecker


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def captured_console(monkeypatch):
    """Render rich output into a buffer instead of the terminal."""
    buffer = io.StringIO()
    monkeypatch.setattr(core_ui, "console", Console(file=buffer, width=100))
    return buffer


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("3.5.2", (3, 5, 2)),
        ("v3.5.2", (3, 5, 2)),
        ("v3.5.2-beta", (3, 5, 2)),
        ("not-a-version", (0, 0, 0)),
        (None, (0, 0, 0)),
    ],
)
def test_parse_version(raw, expected):
    assert UpdateChecker._parse_version(raw) == expected


def test_current_version_is_stored_without_the_v_prefix():
    assert UpdateChecker("v3.5.2").current_version == "3.5.2"


def test_check_for_updates_detects_a_newer_release(monkeypatch):
    monkeypatch.setattr(
        core_ui.urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse(
            {"tag_name": "v4.0.0", "html_url": "https://example.invalid/v4"}
        ),
    )

    checker = UpdateChecker("v3.5.2")
    assert checker.check_for_updates() is True
    assert checker.latest_version == "4.0.0"
    assert checker.download_url == "https://example.invalid/v4"


def test_check_for_updates_ignores_older_or_equal_releases(monkeypatch):
    monkeypatch.setattr(
        core_ui.urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse({"tag_name": "v3.5.2"}),
    )

    checker = UpdateChecker("v3.5.2")
    assert checker.check_for_updates() is False
    assert checker.update_available is False


def test_check_for_updates_falls_back_to_the_releases_page(monkeypatch):
    monkeypatch.setattr(
        core_ui.urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse({"tag_name": "v4.0.0"}),
    )

    checker = UpdateChecker("v3.5.2")
    checker.check_for_updates()
    assert checker.download_url == UpdateChecker.RELEASES_URL


def test_check_for_updates_survives_a_non_200_response(monkeypatch):
    monkeypatch.setattr(
        core_ui.urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse({}, status=503),
    )

    assert UpdateChecker("v3.5.2").check_for_updates() is False


def test_check_for_updates_survives_network_errors(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("no network")

    monkeypatch.setattr(core_ui.urllib.request, "urlopen", boom)

    assert UpdateChecker("v3.5.2").check_for_updates() is False


def test_update_notification_is_printed_only_when_an_update_exists(captured_console):
    checker = UpdateChecker("v3.5.2")
    checker.print_update_notification()
    assert captured_console.getvalue() == ""

    checker.update_available = True
    checker.latest_version = "4.0.0"
    checker.download_url = "https://example.invalid/v4"
    checker.print_update_notification()

    assert "NEW VERSION AVAILABLE" in captured_console.getvalue()


def test_format_hotkey_is_uppercased_and_spaced():
    assert UIManager._format_hotkey("ctrl+shift+ a") == "CTRL + SHIFT + A"


def test_print_hotkeys_lists_every_described_action(captured_console):
    hotkeys = {action: "ctrl+f9" for action, _ in HOTKEY_DESCRIPTIONS if action}

    UIManager.print_hotkeys(hotkeys)
    output = captured_console.getvalue()

    assert "CTRL + F9" in output
    assert "Alternar Autoclicker" in output


def test_print_hotkeys_leaves_unbound_actions_blank(captured_console):
    UIManager.print_hotkeys({})
    output = captured_console.getvalue()

    assert "CTRL" not in output
    assert "Atalhos" in output


def test_print_header_and_status_render(captured_console):
    UIManager.print_header("VKit - Toolbox", "v3.5.2")
    UIManager.print_status("ctrl+alt+shift+d")
    output = captured_console.getvalue()

    assert "VKit - Toolbox" in output
    assert "CTRL + ALT + SHIFT + D" in output
