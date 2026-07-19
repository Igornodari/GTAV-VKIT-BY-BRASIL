"""
Centralized logging for VKit Toolbox.

Exposes a single shared `console` (rich) plus a `logger` that always writes
to a rotating log file, independent of whether on-screen debug mode is
enabled. Other modules should import `console`/`logger` from here instead
of instantiating their own `rich.console.Console()`, so a user reporting a
bug has an actual log file to share.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console


def _get_base_dir() -> Path:
    """Same heuristic as main.get_base_dir(), kept local so this module has
    no dependency on main.py (would reintroduce a circular import)."""
    if sys.argv[0].endswith(".exe"):
        return Path(sys.argv[0]).parent.resolve()

    exe_path = Path(sys.executable).resolve()
    if "python" not in exe_path.name.lower() and "temp" not in str(exe_path).lower():
        return exe_path.parent

    return Path(__file__).parent.parent.resolve()


console = Console()

logger = logging.getLogger("vkit")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    _log_dir = _get_base_dir() / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)

    _handler = RotatingFileHandler(
        _log_dir / "vkit.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)
