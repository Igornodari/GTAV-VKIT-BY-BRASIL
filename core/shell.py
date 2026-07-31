"""
Subprocess helpers for VKit Toolbox.

Every external command the app runs (netsh, route, taskkill, powershell)
must stay invisible to the user, so they all share the same
`CREATE_NO_WINDOW` invocation.
"""

import subprocess

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_hidden(command, shell: bool = True, text: bool = False) -> subprocess.CompletedProcess:
    """Run a command without popping up a console window."""
    return subprocess.run(
        command,
        shell=shell,
        capture_output=True,
        text=text,
        creationflags=CREATE_NO_WINDOW,
    )
