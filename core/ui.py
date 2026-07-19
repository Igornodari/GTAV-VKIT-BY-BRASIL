"""
UI management for VKit Toolbox.

This module contains UI-related classes including the main UI manager
and update checker functionality.
"""

import json
import urllib.request
from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.state import runtime
from core.logger import console


# ============================================================================
# HOTKEY DESCRIPTIONS
# ============================================================================

# Single source of truth for the hotkey reference table - shared by the
# console table (UIManager.print_hotkeys) and the in-game settings panel
# (assets/settings_window.py). (None, None) rows render as blank separators.
HOTKEY_DESCRIPTIONS = [
    ("toggle_overlay", "Alternar overlay (Cheio ↔ Mini)"),
    ("toggle_nosave", "Alternar NOSAVE (LIGADO ↔ DESLIGADO)"),
    ("debug_toggle", "🐛 Alternar Modo Debug"),
    ("open_settings", "🛠️ Abrir painel de atalhos"),
    (None, None),
    ("autoclicker", "⚡ Alternar Autoclicker Rápido (50 CPS)"),
    ("snack_spammer", "🍔 Alternar Snack Spammer (Segure TAB)"),
    ("armor_snack_combo", "🎽 Usar Colete + Comida (combo rápido)"),
    ("anti_afk", "🎮 Alternar Anti-AFK (S+A ↔ S+D)"),
    ("kill_gta", "💀 Encerrar Processo do GTA5 (Instantâneo)"),
    (None, None),
    ("job_warp", "🚀 Exploit Job Warp (Alternar)"),
    (None, None),
    ("casino_fingerprint", "Solver de Fingerprint do Cassino"),
    ("casino_keypad", "Solver do Teclado do Cassino"),
    ("cayo_fingerprint", "Solver de Fingerprint do Cayo Perico"),
    ("cayo_voltage", "Solver de Voltagem do Cayo Perico"),
]


# ============================================================================
# UPDATE CHECKER
# ============================================================================

class UpdateChecker:
    """Checks for updates from GitHub releases."""

    REPO_OWNER = "ItsCEED"
    REPO_NAME = "vkit-toolbox"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    RELEASES_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"

    def __init__(self, current_version: str):
        self.current_version = current_version.lstrip('v')
        self.latest_version = None
        self.update_available = False
        self.download_url = None

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """Parse version string to tuple."""
        try:
            clean_version = version_str.lstrip('v').split('-')[0]
            return tuple(int(p) for p in clean_version.split('.'))
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def check_for_updates(self, timeout: int = 3) -> bool:
        """Check if newer version is available."""
        try:
            req = urllib.request.Request(
                self.API_URL,
                headers={'User-Agent': f'{self.REPO_NAME}/{self.current_version}'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))

                    self.latest_version = data.get('tag_name', '').lstrip('v')
                    self.download_url = data.get('html_url', self.RELEASES_URL)

                    current = self._parse_version(self.current_version)
                    latest = self._parse_version(self.latest_version)

                    self.update_available = latest > current
                    return self.update_available

        except Exception as e:
            if runtime.debug:
                print(f"[DEBUG] Falha ao verificar atualização: {e}")
            return False

        return False

    def print_update_notification(self):
        """Print update notification if available."""
        if self.update_available:
            update_panel = Panel(
                f"[bold yellow]🔔 NOVA VERSÃO DISPONÍVEL![/bold yellow]\n\n"
                f"Versão atual:        [cyan]v{self.current_version}[/cyan]\n"
                f"Versão mais recente: [green]v{self.latest_version}[/green]\n\n"
                f"[dim]Baixe em:[/dim] [link={self.download_url}]{self.download_url}[/link]",
                title="✨ [bold]Verificador de Atualizações[/bold]",
                border_style="yellow", box=box.DOUBLE,
                width=70, padding=(1, 2)
            )
            console.print(update_panel)
            console.print()


# ============================================================================
# UI MANAGEMENT
# ============================================================================

class UIManager:
    """Manages UI display and formatting."""

    @staticmethod
    def print_header(app_title: str, version: str):
        """Print application header."""
        console.clear()
        console.print()

        title = Text()
        title.append(app_title, style="bold cyan")
        title.append(" | ", style="white")
        title.append(version, style="dim yellow")

        console.print(Panel(
            Align.center(title), box=box.DOUBLE,
            border_style="bright_cyan", padding=(0, 2)
        ))
        console.print()

    @staticmethod
    def _format_hotkey(hotkey_str: str) -> str:
        """Format hotkey string for display."""
        return ' + '.join(p.strip().upper() for p in hotkey_str.split('+'))

    @staticmethod
    def print_hotkeys(hotkeys: dict):
        """Print hotkeys table."""
        hotkeys_table = Table(
            title="🎮  [bold]Atalhos[/bold]",
            box=box.ROUNDED, border_style="magenta",
            show_header=True, header_style="bold magenta", width=70
        )
        hotkeys_table.add_column("Atalho", style="bold magenta", width=25)
        hotkeys_table.add_column("Ação", style="white", width=38)

        for action, description in HOTKEY_DESCRIPTIONS:
            if action is None:
                hotkeys_table.add_row("", "")
                continue

            hotkey = hotkeys.get(action, "")
            hotkeys_table.add_row(
                UIManager._format_hotkey(hotkey) if hotkey else "",
                description
            )

        console.print(hotkeys_table)
        console.print()

    @staticmethod
    def print_status(debug_hotkey: str):
        """Print running status."""
        console.print(Panel(
            "[bold green]●[/bold green] Script rodando... "
            "Pressione [bold red]CTRL+C[/bold red] pra sair\n"
            f"[dim]Pressione {UIManager._format_hotkey(debug_hotkey)} "
            "pra alternar o modo debug[/dim]",
            box=box.HEAVY, border_style="bright_green",
            width=70, padding=(0, 2)
        ))
        console.print()
