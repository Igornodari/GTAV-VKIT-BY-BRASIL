from assets.settings_window import HotkeyCapture


def test_single_key_no_modifiers():
    cap = HotkeyCapture()
    assert cap.on_key_press("F5") == "f5"


def test_single_modifier_combo():
    cap = HotkeyCapture()
    assert cap.on_key_press("Control_L") is None
    assert cap.on_key_press("F9") == "ctrl+f9"


def test_multi_modifier_combo_is_ordered_ctrl_alt_shift():
    cap = HotkeyCapture()
    # feed them out of order - result must still be ctrl+alt+shift+d
    assert cap.on_key_press("Shift_L") is None
    assert cap.on_key_press("Alt_L") is None
    assert cap.on_key_press("Control_L") is None
    assert cap.on_key_press("d") == "ctrl+alt+shift+d"


def test_right_side_modifiers_normalize_same_as_left():
    cap = HotkeyCapture()
    assert cap.on_key_press("Control_R") is None
    assert cap.on_key_press("F9") == "ctrl+f9"


def test_named_keys():
    assert HotkeyCapture().on_key_press("space") == "space"
    assert HotkeyCapture().on_key_press("Return") == "enter"
    assert HotkeyCapture().on_key_press("Tab") == "tab"
    assert HotkeyCapture().on_key_press("Escape") == "esc"


def test_key_release_clears_modifier():
    cap = HotkeyCapture()
    cap.on_key_press("Control_L")
    cap.on_key_release("Control_L")
    # ctrl was released before the main key, so it should not be included
    assert cap.on_key_press("k") == "k"


def test_reset_clears_all_held_modifiers():
    cap = HotkeyCapture()
    cap.on_key_press("Control_L")
    cap.on_key_press("Shift_L")
    cap.reset()
    assert cap.on_key_press("q") == "q"
