"""
Path helpers for VKit Toolbox.

Kept dependency-free so both `main.py` and the `core` package can import it
without creating a circular import.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()


def get_base_dir() -> Path:
    """Get the directory containing the actual .exe or script."""
    if sys.argv[0].endswith(".exe"):
        return Path(sys.argv[0]).parent.resolve()

    exe_path = Path(sys.executable).resolve()
    if "python" not in exe_path.name.lower() and "temp" not in str(exe_path).lower():
        return exe_path.parent

    return REPO_ROOT
