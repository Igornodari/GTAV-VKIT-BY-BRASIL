"""
Core managers for VKit Toolbox.

This module contains the core management classes for window focus detection,
sound effects, firewall rules, and process operations.
"""

import ctypes
import socket
import subprocess
import sys
import threading
import time
import winsound
from pathlib import Path
from typing import Callable, Optional

import psutil
import win32gui
import win32process

from core.state import runtime
from core.logger import console

class GameDetector:
    def __init__(self, process_prefix: str = "GTA5", poll_interval: float = 0.5, timeout: Optional[float] = None):
        self.process_prefix = process_prefix
        self.poll_interval = poll_interval
        self.timeout = timeout

    def get_gta_process(self) -> Optional[psutil.Process]:
        start_time = time.time()
        console.print("Aguardando o GTA.", style="yellow")
        while True:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].startswith(self.process_prefix):
                        console.print(f"{proc.info['name']} detectado.", style="yellow")
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    console.print("Aguardando o GTA.", style="yellow")
                    pass
                
            
            # Check timeout
            if self.timeout and (time.time() - start_time > self.timeout):
                raise TimeoutError(f"GTA process '{self.process_prefix}' not detected within {self.timeout}s")
            
            time.sleep(self.poll_interval)
    
# ============================================================================
# WINDOW FOCUS MANAGEMENT
# ============================================================================

class WindowFocusManager:
    """Event-driven window focus detection with manual refresh capability."""

    EVENT_SYSTEM_FOREGROUND = 0x0003
    WINEVENT_OUTOFCONTEXT = 0x0000

    def __init__(self, process_name: Optional[str] = None):
        if process_name is None:
            process_name = GameDetector().get_gta_process().name()
        self.process_name = process_name.lower()
        self.gta_titles = frozenset(['grand theft auto v', 'gta5', 'rockstar games'])

        self._is_focused = False
        self._callbacks = []
        self._hook_id = None
        self._shutdown = threading.Event()

        # Unified cache with lock
        self._cache = {'hwnd': None, 'pid': None, 'process': None, 'title': None}
        self._cache_lock = threading.Lock()

        # Windows hook function
        self._hook_func = ctypes.WINFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
            ctypes.c_long, ctypes.c_long, ctypes.c_uint, ctypes.c_uint
        )(self._on_window_focus_change)

    def _get_window_info(self, hwnd) -> tuple[Optional[str], str]:
        """Get window process name and title with caching."""
        with self._cache_lock:
            if hwnd == self._cache['hwnd']:
                return self._cache['process'], self._cache['title']

            try:
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                try:
                    process = psutil.Process(pid).name().lower()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process = None

                self._cache.update({
                    'hwnd': hwnd, 'pid': pid,
                    'process': process, 'title': title
                })

                return process, title
            except Exception:
                return None, ""

    def _check_is_gta(self, process_name: Optional[str], title: str) -> bool:
        """Check if window belongs to GTA."""
        if process_name == self.process_name:
            return True
        if title:
            return any(gta in title.lower() for gta in self.gta_titles)
        return False

    def _on_window_focus_change(self, hook, event, hwnd, id_obj, id_child, thread, timestamp):
        """Windows hook callback - triggers on focus change."""
        try:
            if self._shutdown.is_set():
                return

            process_name, title = self._get_window_info(hwnd)
            is_gta = self._check_is_gta(process_name, title)

            # Only trigger callbacks on state change
            if is_gta != self._is_focused:
                self._is_focused = is_gta
                for callback in self._callbacks[:]:
                    runtime.thread_pool.submit(self._safe_callback, callback, is_gta)

        except Exception as e:
            if runtime.debug:
                print(f"[DEBUG] Erro no hook de foco: {e}")

    @staticmethod
    def _safe_callback(callback: Callable, is_focused: bool):
        """Execute callback with error handling."""
        try:
            callback(is_focused)
        except Exception as e:
            if runtime.debug:
                print(f"[DEBUG] Erro no callback de foco: {e}")

    def register_focus_callback(self, callback: Callable):
        """Register focus change callback."""
        self._callbacks.append(callback)

    def is_gta_focused(self) -> bool:
        """Get current focus state."""
        return self._is_focused

    def force_refresh_focus_state(self) -> bool:
        """Manually check and update focus state."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            process_name, title = self._get_window_info(hwnd)
            is_gta = self._check_is_gta(process_name, title)

            old_state = self._is_focused
            self._is_focused = is_gta

            if runtime.debug:
                print(f"[DEBUG] Atualização forçada: foco={is_gta} (era {old_state})")

            # Trigger callbacks if state changed
            if is_gta != old_state:
                for callback in self._callbacks[:]:
                    runtime.thread_pool.submit(self._safe_callback, callback, is_gta)

            return is_gta
        except Exception as e:
            if runtime.debug:
                print(f"[DEBUG] Erro na atualização forçada: {e}")
            return self._is_focused

    def start_monitoring(self):
        """Start event-driven monitoring."""
        def hook_thread():
            try:
                user32 = ctypes.windll.user32

                self._hook_id = user32.SetWinEventHook(
                    self.EVENT_SYSTEM_FOREGROUND, self.EVENT_SYSTEM_FOREGROUND,
                    0, self._hook_func, 0, 0, self.WINEVENT_OUTOFCONTEXT
                )

                if not self._hook_id:
                    raise RuntimeError("Falha ao configurar o hook de eventos do Windows")

                if runtime.debug:
                    print("[DEBUG] ✓ Hook de eventos do Windows instalado")

                # Check initial state
                try:
                    hwnd = win32gui.GetForegroundWindow()
                    self._on_window_focus_change(None, self.EVENT_SYSTEM_FOREGROUND, 
                                                hwnd, 0, 0, 0, 0)
                except Exception:
                    pass

                # Message loop
                msg = ctypes.wintypes.MSG()
                while not self._shutdown.is_set():
                    if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                    else:
                        self._shutdown.wait(0.1)

            except Exception as e:
                if runtime.debug:
                    print(f"[DEBUG] Erro na thread do hook: {e}")
            finally:
                if self._hook_id:
                    user32.UnhookWinEvent(self._hook_id)

        threading.Thread(target=hook_thread, daemon=True, name="focus_monitor").start()

    def stop_monitoring(self):
        """Stop monitoring."""
        self._shutdown.set()


# ============================================================================
# SOUND MANAGEMENT
# ============================================================================

class SoundManager:
    """Manages sound effects with async playback."""

    SOUND_FILES = {'on': 'on.wav', 'off': 'off.wav', 'toggle': 'toggle.wav'}

    def __init__(self, assets_dir: Path):
        self.sounds_dir = assets_dir / "assets" / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        self.sounds = {
            key: str(path) if (path := self.sounds_dir / filename).exists() else None
            for key, filename in self.SOUND_FILES.items()
        }

    def play(self, sound_type: str):
        """Play sound asynchronously."""
        if path := self.sounds.get(sound_type):
            runtime.thread_pool.submit(self._play_sound, path)

    @staticmethod
    def _play_sound(path: str):
        """Internal sound player."""
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    def play_on(self):
        self.play('on')

    def play_off(self):
        self.play('off')

    def play_toggle(self):
        self.play('toggle')


# ============================================================================
# FIREWALL MANAGEMENT
# ============================================================================

class FirewallManager:
    """Manages Windows firewall rules."""

    def __init__(self, rule_name: str, remote_ip: str, test_port: int):
        self.rule_name = rule_name
        self.remote_ip = remote_ip
        self.test_port = test_port

    def rule_exists(self) -> bool:
        """Check if the firewall rule exists without depending on Windows language."""
        rule_name = self.rule_name.strip().replace("'", "''")

        command = (
            f"$rule = Get-NetFirewallRule "
            f"-DisplayName '{rule_name}' "
            f"-ErrorAction SilentlyContinue; "
            f"if ($null -eq $rule) {{ exit 1 }} else {{ exit 0 }}"
        )

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            shell=False,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        return result.returncode == 0

    def test_ip_blocked(self, timeout: float = 2) -> bool:
        """Test if IP is blocked."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                return sock.connect_ex((self.remote_ip, self.test_port)) != 0
        except Exception:
            return True

    def add_rule(self, manager, sound_manager):
        """Add firewall blocking rule."""
        subprocess.run(
            f'netsh advfirewall firewall add rule name="{self.rule_name}" '
            f'dir=out action=block remoteip="{self.remote_ip}"',
            shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )

        time.sleep(0.5)
        if self.rule_exists():
            console.print("✓ MODO NO SAVE [bold green]ATIVADO[/bold green]", style="green")
            manager.update_status("ON")
            # Nota: cor literal (não importada) pra evitar import circular com
            # assets.ui, que já importa deste módulo. Mesmo valor de C_GREEN.
            manager.show_notification("MODO NOSAVE", "Proteção da sessão ativada", "#22C55E")
            sound_manager.play_on()

            if self.test_ip_blocked():
                console.print(
                    f"✓ Conexão com [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                    f"está [bold red]BLOQUEADA[/bold red]", style="green"
                )
        else:
            console.print("✗ Falha ao adicionar a regra de firewall", style="red")
        console.print()

    def delete_rule(self, manager, sound_manager):
        """Remove firewall blocking rule."""
        subprocess.run(
            f'netsh advfirewall firewall delete rule name="{self.rule_name}"',
            shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )

        time.sleep(0.5)
        if not self.rule_exists():
            console.print("✓ MODO NO SAVE [bold red]DESATIVADO[/bold red]", style="green")
            manager.update_status("OFF")
            manager.show_notification("MODO NOSAVE", "Proteção da sessão desativada", "#FF3B5C")
            sound_manager.play_off()

            if not self.test_ip_blocked():
                console.print(
                    f"✓ Conexão com [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                    f"está [bold green]ACESSÍVEL[/bold green]", style="green"
                )
        else:
            console.print("✗ Falha ao remover a regra de firewall", style="red")
        console.print()

    def toggle_rule(self, manager, sound_manager):
        """Toggle firewall rule."""
        if self.rule_exists():
            self.delete_rule(manager, sound_manager)
        else:
            self.add_rule(manager, sound_manager)

    def cleanup(self) -> bool:
        """Cleanup firewall rule on exit."""
        if self.rule_exists():
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{self.rule_name}"',
                shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        return False


# ============================================================================
# PROCESS MANAGEMENT
# ============================================================================

class ProcessManager:
    """Manages external process operations."""

    @staticmethod
    def is_admin() -> bool:
        """Check if running with admin privileges."""
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @staticmethod
    def run_as_admin(base_dir: Path):
        """Restart script with admin privileges."""
        if ProcessManager.is_admin():
            return

        current_dir = str(base_dir)
        executable = sys.executable

        if hasattr(sys, 'frozen') or "__compiled__" in globals():
            params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        else:
            params = f'"{sys.argv[0]}" ' + " ".join(f'"{arg}"' for arg in sys.argv[1:])

        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, current_dir, 1)
        except Exception as e:
            console.print(f"[red]Falha ao elevar privilégios: {e}[/red]")

        sys.exit()

    @staticmethod
    def kill_process(process_name: str, manager):
        """Kill a process by name."""
        try:
            result = subprocess.run(
                f'taskkill /F /IM {process_name}',
                shell=True, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                console.print(f"✓ Processo {process_name} [bold red]ENCERRADO[/bold red]", style="green")
                manager.show_notification(
                    "PROCESSO ENCERRADO",
                    f"{process_name} foi encerrado", "#FF3B5C"
                )
            else:
                console.print(f"✗ Processo {process_name} não encontrado ou já encerrado", style="yellow")
                manager.show_notification(
                    "PROCESSO NÃO ENCONTRADO",
                    f"{process_name} não está rodando", "#F59E0B"
                )
        except Exception as e:
            console.print(f"✗ Falha ao encerrar {process_name}: {e}", style="red")
            manager.show_notification("ERRO", f"Falha ao encerrar {process_name}", "#FF3B5C")
        console.print()