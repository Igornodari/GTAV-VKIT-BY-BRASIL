import random
import time

from core.logger import console
from tools.base import ToggleableTool

try:
    import pydirectinput
    pydirectinput.PAUSE = 0.001
    PYDIRECTINPUT_AVAILABLE = True
except ImportError:
    PYDIRECTINPUT_AVAILABLE = False
    from pynput import mouse


try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


def _key_backend():
    """Return (press, release) callables for the best available backend."""
    if PYDIRECTINPUT_AVAILABLE:
        import pydirectinput as pdi
        return pdi.keyDown, pdi.keyUp

    if KEYBOARD_AVAILABLE:
        from pynput.keyboard import Controller
        kbd = Controller()
        return kbd.press, kbd.release

    return None


class KeyboardTool(ToggleableTool):
    """Tool that needs the `keyboard` module to do anything useful."""

    def __init__(self, sound_manager) -> None:
        super().__init__(sound_manager)
        if not KEYBOARD_AVAILABLE:
            console.print(
                f"[yellow]⚠[/yellow] keyboard module not available for {self.name}",
                style="dim",
            )

    def _can_start(self) -> bool:
        if not KEYBOARD_AVAILABLE:
            console.print(
                f"[red]✗[/red] keyboard module required for {self.name}", style="red"
            )
            return False
        return True


class AutoClicker(ToggleableTool):
    name = "AutoClicker"

    def __init__(self, sound_manager) -> None:
        super().__init__(sound_manager)
        self.clicks_per_second = 70
        self.use_directinput = PYDIRECTINPUT_AVAILABLE

        if not self.use_directinput:
            self.mouse_controller = mouse.Controller()

    def _directinput_click(self) -> None:
        """DirectInput click without moving mouse"""
        pydirectinput.mouseDown(button="left")
        time.sleep(0.02)
        pydirectinput.mouseUp(button="left")

    def _pynput_click(self) -> None:
        """Pynput click without moving mouse"""
        self.mouse_controller.press(mouse.Button.left)
        time.sleep(0.02)
        self.mouse_controller.release(mouse.Button.left)

    def run(self) -> None:
        mode = "DirectInput" if self.use_directinput else "Standard"
        console.print(f"⚡ Autoclicker [bold green]STARTED[/bold green] ({self.clicks_per_second} CPS - {mode})", style="green")

        click_count = 0
        delay = 1.0 / self.clicks_per_second

        while self._running():
            try:
                if self.use_directinput:
                    self._directinput_click()
                else:
                    self._pynput_click()

                click_count += 1

                # Interruptible sleep
                if self.stop_event.wait(timeout=delay):
                    break

            except Exception as exc:
                console.print(f"✗ Autoclicker error: {exc}", style="red")
                break

        console.print(f"⚡ Autoclicker [bold red]STOPPED[/bold red] ([cyan]{click_count}[/cyan] clicks)", style="green")
        console.print()


class TabHeldSpammer(KeyboardTool):
    """Spams a rotation of keys for as long as TAB is held down."""

    #: Keys tapped in order, one per loop iteration.
    keys: tuple = ()
    started_message = ""
    stopped_message = ""

    def __init__(self, sound_manager) -> None:
        super().__init__(sound_manager)
        self.spam_delay = 0.05  # 50ms between presses

    def _tap(self, key: str) -> bool:
        """Press+release one key, sleeping between. Returns False if a stop
        was requested during the sleeps (caller should bail out)."""
        keyboard.press(key)
        if self.stop_event.wait(timeout=self.spam_delay):
            keyboard.release(key)
            return False
        keyboard.release(key)
        return not self.stop_event.wait(timeout=self.spam_delay)

    def run(self) -> None:
        console.print(self.started_message, style="green")

        press_count = 0

        while self._running():
            try:
                if keyboard.is_pressed('tab'):
                    if not self._tap(self.keys[press_count % len(self.keys)]):
                        break
                    press_count += 1
                else:
                    # Interruptible sleep while TAB is not pressed
                    if self.stop_event.wait(timeout=0.1):
                        break

            except Exception as exc:
                console.print(f"✗ {self.name} error: {exc}", style="red")
                break

        console.print(self.stopped_message.format(count=press_count), style="green")
        console.print()


class SnackSpammer(TabHeldSpammer):
    name = "SnackSpammer"
    keys = ('c',)
    started_message = "🍔 Snack Spammer [bold green]STARTED[/bold green] (Hold TAB to spam 'C')"
    stopped_message = "🍔 Snack Spammer [bold red]STOPPED[/bold red] ([cyan]{count}[/cyan] presses)"


class ArmorSnackSpammer(TabHeldSpammer):
    """Toggleable combo: while active and TAB is held, alternately spams
    'v' (colete) and 'c' (comida) so both use-bars fill on their own -
    no more manually mashing V/C while holding TAB."""

    name = "Colete + Comida"
    keys = ('v', 'c')
    started_message = "🎽 Colete + Comida [bold green]STARTED[/bold green] (Hold TAB to spam 'V'/'C')"
    stopped_message = "🎽 Colete + Comida [bold red]STOPPED[/bold red] ([cyan]{count}[/cyan] presses)"


class AntiAFK(ToggleableTool):
    """Anti-AFK system - alternates S+A and S+D every 20-30 seconds"""

    name = "Anti-AFK"

    def _release_all_keys(self):
        """Force release all keys - cleanup helper"""
        try:
            backend = _key_backend()
            if backend is None:
                return

            _, release = backend
            for key in ('s', 'd', 'a'):
                release(key)
            console.print("✓ Released all Anti-AFK keys", style="dim")
        except Exception as e:
            console.print(f"⚠ Key release error: {e}", style="yellow")

    def run(self) -> None:
        """Main anti-AFK loop - alternates between S+A and S+D"""
        try:
            backend = _key_backend()
            if backend is None:
                console.print("[red]✗[/red] No keyboard library available", style="red")
                return

            press, release = backend

            # Start with S+D
            press('s')
            press('d')
            console.print("✓ Anti-AFK: Starting with S+D", style="green")

            use_sd = True

            while not self.stop_event.is_set():
                # Random wait between 20-30 seconds
                wait_time = random.uniform(20, 30)
                console.print(f"⏳ Anti-AFK: Next switch in {wait_time:.1f}s", style="dim")

                if self.stop_event.wait(wait_time):
                    console.print("🛑 Anti-AFK: Stop signal received", style="yellow")
                    break

                # Switch combo
                if use_sd:
                    release('d')
                    press('a')
                    console.print("◉ Anti-AFK: Switched to S+A", style="cyan")
                else:
                    release('a')
                    press('d')
                    console.print("◉ Anti-AFK: Switched to S+D", style="cyan")
                use_sd = not use_sd

            console.print("🔓 Releasing keys...", style="dim")
            self._release_all_keys()

        except Exception as e:
            console.print(f"[red]✗[/red] Anti-AFK error: {e}", style="red")
            self._release_all_keys()

    def start(self) -> None:
        if self.active:
            return

        super().start()
        console.print("✓ Anti-AFK [bold green]ENABLED[/bold green] (Alternating S+D ↔ S+A)", style="green")
        console.print()

    def stop(self) -> None:
        if not self.active:
            return

        console.print("⏹ Stopping Anti-AFK...", style="yellow")
        console.print("⏹ Waiting for thread...", style="yellow")
        super().stop()
        console.print("✓ Anti-AFK [bold red]DISABLED[/bold red]", style="green")
        console.print()

    def on_join_timeout(self) -> None:
        super().on_join_timeout()
        # Force release keys even if the thread is stuck
        self._release_all_keys()
