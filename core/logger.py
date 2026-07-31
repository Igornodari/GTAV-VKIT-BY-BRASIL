"""
Centralized logging for VKit Toolbox.

Exposes a single shared `console` (rich) plus a `logger` that always writes
to a rotating log file, independent of whether on-screen debug mode is
enabled. Other modules should import `console`/`logger` from here instead
of instantiating their own `rich.console.Console()`, so a user reporting a
bug has an actual log file to share.
"""

import logging
from logging.handlers import RotatingFileHandler

from rich.console import Console

from core.paths import get_base_dir
from core.state import runtime

console = Console()


def debug(message: str) -> None:
    """Print `message` to the console only while debug mode is on."""
    if runtime.debug:
        print(f"[DEBUG] {message}")


logger = logging.getLogger("vkit")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    _log_dir = get_base_dir() / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)

    _handler = RotatingFileHandler(
        _log_dir / "vkit.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)
