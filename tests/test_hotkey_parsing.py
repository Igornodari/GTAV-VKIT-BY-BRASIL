from pynput import keyboard

from main import HotkeyHandler


def test_parse_simple_combo():
    combo = HotkeyHandler._parse_hotkey("ctrl+f9")
    assert combo == frozenset({keyboard.Key.ctrl, keyboard.Key.f9})


def test_parse_multi_modifier_combo():
    combo = HotkeyHandler._parse_hotkey("ctrl+alt+shift+d")
    assert combo == frozenset(
        {
            keyboard.Key.ctrl,
            keyboard.Key.alt,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char("d"),
        }
    )


def test_parse_is_case_insensitive():
    assert HotkeyHandler._parse_hotkey("CTRL+K") == HotkeyHandler._parse_hotkey(
        "ctrl+k"
    )


def test_normalize_left_right_modifiers_are_unified():
    assert HotkeyHandler._normalize_key(keyboard.Key.ctrl_l) == keyboard.Key.ctrl
    assert HotkeyHandler._normalize_key(keyboard.Key.ctrl_r) == keyboard.Key.ctrl
    assert HotkeyHandler._normalize_key(keyboard.Key.alt_gr) == keyboard.Key.alt


def test_normalize_uppercase_char_key_is_lowercased():
    upper_d = keyboard.KeyCode.from_char("D")
    assert HotkeyHandler._normalize_key(upper_d) == keyboard.KeyCode.from_char("d")
