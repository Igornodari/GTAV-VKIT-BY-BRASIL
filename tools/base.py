"""
Shared plumbing for the toggleable background tools.

Every tool (autoclicker, snack spammers, anti-AFK) runs the same lifecycle:
a daemon thread driven by an `active` flag plus a `stop_event` used for
interruptible sleeps, with start/stop playing the on/off sounds.
"""

import threading
from typing import Optional

from core.logger import console


class ToggleableTool:
    """Base class for tools that run a loop on a background daemon thread."""

    #: Human readable name used in the "module required" error message.
    name = "Tool"
    #: When set, `start()` refuses to run unless the dependency is available.
    requires_keyboard = False
    #: Seconds to wait for the worker thread to exit on stop.
    join_timeout = 1.0

    def __init__(self, sound_manager) -> None:
        self.sound_manager = sound_manager
        self.active = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def run(self) -> None:
        """Tool loop - must poll `self.stop_event` so stop() is instant."""
        raise NotImplementedError

    def _can_start(self) -> bool:
        """Hook for dependency checks; return False to abort `start()`."""
        return True

    def start(self) -> None:
        if not self._can_start():
            return

        if self.active:
            return

        self.active = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        self.sound_manager.play_on()

    def stop(self) -> None:
        if not self.active:
            return

        self.active = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=self.join_timeout)
            if self.thread.is_alive():
                self.on_join_timeout()
        self.sound_manager.play_off()

    def on_join_timeout(self) -> None:
        """Called when the worker thread outlives `join_timeout`."""
        console.print(
            f"⚠ {self.name} thread still alive after {self.join_timeout}s, forcing cleanup",
            style="yellow",
        )

    def toggle(self) -> None:
        if self.active:
            self.stop()
        else:
            self.start()

    def _running(self) -> bool:
        return self.active and not self.stop_event.is_set()
