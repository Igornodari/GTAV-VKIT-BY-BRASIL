"""Test-time stubs for the Windows-only modules VKit imports at module level.

The app itself only ever runs on Windows, but the pure logic (solvers, config
parsing, hotkey handling, tool state machines) is platform independent and
worth testing anywhere. Importing `core.managers` or `main` pulls in
`winsound`/`win32gui`/`win32process`, so on non-Windows hosts we register
minimal stand-ins *before* those imports happen. On Windows the real modules
import fine and nothing here takes effect.
"""

import ctypes
import sys
import types

if not hasattr(ctypes, "WINFUNCTYPE"):
    # WindowFocusManager builds its focus hook callback with WINFUNCTYPE at
    # construction time; the cdecl flavour is close enough to instantiate it.
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE


def _stub(name: str, **attrs) -> None:
    try:
        __import__(name)
        return
    except ImportError:
        pass

    module = types.ModuleType(name)
    for attr, value in attrs.items():
        setattr(module, attr, value)
    sys.modules[name] = module


_stub(
    "winsound",
    PlaySound=lambda *a, **kw: None,
    SND_FILENAME=0x00020000,
    SND_ASYNC=0x0001,
)
_stub(
    "win32gui",
    GetWindowText=lambda hwnd: "",
    GetForegroundWindow=lambda: 0,
    FindWindow=lambda *a: 0,
)
_stub("win32process", GetWindowThreadProcessId=lambda hwnd: (0, 0))
