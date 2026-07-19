"""
In-game settings panel for VKit Toolbox.

Lets the user view every configured hotkey and rebind it live, without
closing the game or restarting the app.
"""

import tkinter as tk
from pathlib import Path
from typing import Optional

from assets.ui import (
    C_BG_DARK,
    C_BG_DARKEST,
    C_BG_LIGHTER,
    C_BG_MEDIUM,
    C_GTA_CYAN,
    C_GTA_ORANGE,
    C_RED_BRIGHT,
    C_TEXT_GREY,
    C_TEXT_WHITE,
    FONT_BODY,
    FONT_HEADER,
    FONT_SMALL,
)
from core.logger import console
from core.ui import HOTKEY_DESCRIPTIONS

MODIFIER_KEYSYMS = {
    "Control_L": "ctrl",
    "Control_R": "ctrl",
    "Alt_L": "alt",
    "Alt_R": "alt",
    "Shift_L": "shift",
    "Shift_R": "shift",
}

FUNCTION_KEYSYMS = {f"F{i}": f"f{i}" for i in range(1, 13)}

NAMED_KEYSYMS = {
    "space": "space",
    "Return": "enter",
    "Tab": "tab",
    "Escape": "esc",
}

MODIFIER_ORDER = ("ctrl", "alt", "shift")


class HotkeyCapture:
    """Pure (Tk-free) helper that turns a stream of Tk keysyms into a hotkey
    string like "ctrl+alt+f9", matching the format HotkeyHandler._parse_hotkey
    already expects. Testable without a real Tk window."""

    def __init__(self):
        self.held_modifiers: set[str] = set()

    def on_key_press(self, keysym: str) -> Optional[str]:
        """Feed a keysym from a KeyPress event. Returns the finished combo
        string once a non-modifier key is pressed, otherwise None (still
        waiting on more modifiers)."""
        modifier = MODIFIER_KEYSYMS.get(keysym)
        if modifier:
            self.held_modifiers.add(modifier)
            return None

        main_key = (
            FUNCTION_KEYSYMS.get(keysym)
            or NAMED_KEYSYMS.get(keysym)
            or keysym.lower()
        )
        ordered_modifiers = [m for m in MODIFIER_ORDER if m in self.held_modifiers]
        return "+".join(ordered_modifiers + [main_key])

    def on_key_release(self, keysym: str) -> None:
        """Feed a keysym from a KeyRelease event."""
        modifier = MODIFIER_KEYSYMS.get(keysym)
        if modifier:
            self.held_modifiers.discard(modifier)

    def reset(self) -> None:
        self.held_modifiers.clear()


class SettingsWindow(tk.Toplevel):
    """Borderless HUD-style panel listing every hotkey, with a live rebind
    flow. Hidden by default; toggled via the 'open_settings' hotkey."""

    WIDTH = 480

    def __init__(self, root: tk.Tk, config, config_path: Path):
        super().__init__(root)
        self.config = config
        self.config_path = config_path
        self.hotkey_handler = None  # attached later via attach_hotkey_handler

        self._capture: Optional[HotkeyCapture] = None
        self._capturing_action: Optional[str] = None
        self._row_widgets: dict[str, dict] = {}
        self._drag_offset = (0, 0)

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=C_BG_DARK)

        self._build_ui()
        self.withdraw()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        header = tk.Frame(self, bg=C_BG_DARKEST, height=36)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="⚙  VKIT — ATALHOS",
            bg=C_BG_DARKEST,
            fg=C_GTA_CYAN,
            font=FONT_HEADER,
            anchor="w",
        )
        title.pack(side="left", padx=12)

        close_btn = tk.Label(
            header, text="✕", bg=C_BG_DARKEST, fg=C_TEXT_GREY,
            font=FONT_HEADER, cursor="hand2"
        )
        close_btn.pack(side="right", padx=12)
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=C_RED_BRIGHT))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=C_TEXT_GREY))

        for widget in (header, title):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

        body = tk.Frame(self, bg=C_BG_DARK)
        body.pack(fill="both", expand=True)

        for action, description in HOTKEY_DESCRIPTIONS:
            if action is None:
                continue
            self._build_row(body, action, description)

        self.warning_label = tk.Label(
            self, text="", bg=C_BG_DARK, fg=C_GTA_ORANGE,
            font=FONT_SMALL, wraplength=self.WIDTH - 24, justify="left",
        )
        self.warning_label.pack(fill="x", padx=12, pady=(0, 10))

    def _build_row(self, parent, action: str, description: str):
        row = tk.Frame(parent, bg=C_BG_DARK)
        row.pack(fill="x", padx=12, pady=4)

        desc_label = tk.Label(
            row, text=description, bg=C_BG_DARK, fg=C_TEXT_WHITE,
            font=FONT_BODY, anchor="w", width=32,
        )
        desc_label.pack(side="left")

        combo_label = tk.Label(
            row,
            text=self._format_combo(self.config.hotkeys.get(action, "")),
            bg=C_BG_MEDIUM, fg=C_GTA_CYAN, font=FONT_SMALL, width=16,
        )
        combo_label.pack(side="left", padx=6)

        change_btn = tk.Button(
            row, text="Alterar", command=lambda a=action: self._start_capture(a),
            bg=C_BG_LIGHTER, fg=C_TEXT_WHITE, activebackground=C_GTA_CYAN,
            relief="flat", font=FONT_SMALL, cursor="hand2", padx=8,
        )
        change_btn.pack(side="right")

        self._row_widgets[action] = {"combo_label": combo_label, "button": change_btn}

    @staticmethod
    def _format_combo(hotkey_str: str) -> str:
        if not hotkey_str:
            return "—"
        return " + ".join(p.strip().upper() for p in hotkey_str.split("+"))

    # ------------------------------------------------------------------
    # Dragging (no OS title bar to drag by)
    # ------------------------------------------------------------------

    def _start_drag(self, event):
        self._drag_offset = (event.x, event.y)

    def _on_drag(self, event):
        x = self.winfo_pointerx() - self._drag_offset[0]
        y = self.winfo_pointery() - self._drag_offset[1]
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Show / hide - safe entry point for the hotkey (worker-thread) callback
    # ------------------------------------------------------------------

    def attach_hotkey_handler(self, hotkey_handler) -> None:
        self.hotkey_handler = hotkey_handler

    def request_toggle(self) -> None:
        """Safe to call from any thread - marshals the actual Tk work onto
        the main/mainloop thread, same pattern as WindowFocusManager."""
        self.after(0, self._toggle_on_main_thread)

    def _toggle_on_main_thread(self):
        if self.winfo_viewable():
            self.hide()
        else:
            self.show()

    def show(self):
        self._cancel_capture()
        self._refresh_all_labels()
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

    def hide(self):
        self._cancel_capture()
        self.withdraw()

    def _refresh_all_labels(self):
        for action, widgets in self._row_widgets.items():
            widgets["combo_label"].config(
                text=self._format_combo(self.config.hotkeys.get(action, ""))
            )

    # ------------------------------------------------------------------
    # Rebind flow
    # ------------------------------------------------------------------

    def _start_capture(self, action: str):
        self._cancel_capture()

        self._capturing_action = action
        self._capture = HotkeyCapture()
        self.warning_label.config(text="")
        self._row_widgets[action]["combo_label"].config(
            text="Pressione uma tecla...", fg=C_GTA_ORANGE
        )

        self.bind_all("<KeyPress>", self._on_capture_press)
        self.bind_all("<KeyRelease>", self._on_capture_release)

    def _cancel_capture(self):
        if self._capturing_action is None:
            return

        self.unbind_all("<KeyPress>")
        self.unbind_all("<KeyRelease>")

        action = self._capturing_action
        self._capturing_action = None
        self._capture = None
        self._row_widgets[action]["combo_label"].config(
            text=self._format_combo(self.config.hotkeys.get(action, "")),
            fg=C_GTA_CYAN,
        )

    def _on_capture_press(self, event):
        if not self._capturing_action or not self._capture:
            return

        combo = self._capture.on_key_press(event.keysym)
        if combo is None:
            return  # still waiting - only modifiers held so far

        self._finish_capture(combo)

    def _on_capture_release(self, event):
        if not self._capturing_action or not self._capture:
            return
        self._capture.on_key_release(event.keysym)

    def _finish_capture(self, combo: str):
        action = self._capturing_action

        collision = next(
            (
                other
                for other, hk in self.config.hotkeys.items()
                if other != action and hk == combo
            ),
            None,
        )

        self.unbind_all("<KeyPress>")
        self.unbind_all("<KeyRelease>")
        self._capturing_action = None
        self._capture = None

        if collision:
            self.warning_label.config(
                text=(
                    f"'{self._format_combo(combo)}' já está em uso por outra "
                    "ação. Escolha outra combinação."
                )
            )
            self._row_widgets[action]["combo_label"].config(
                text=self._format_combo(self.config.hotkeys.get(action, "")),
                fg=C_GTA_CYAN,
            )
            return

        self.config.hotkeys[action] = combo
        self.config.save(self.config_path)
        if self.hotkey_handler:
            self.hotkey_handler.update_hotkey(action, combo)

        self._row_widgets[action]["combo_label"].config(
            text=self._format_combo(combo), fg=C_GTA_CYAN
        )
        console.print(
            f"✓ Atalho '{action}' alterado para "
            f"[bold cyan]{self._format_combo(combo)}[/bold cyan]",
            style="green",
        )
