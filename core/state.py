"""
Shared runtime state for VKit Toolbox.

Holds objects that both `main.py` and the `core` modules need (debug flag,
shared thread pool) so that `core/managers.py` and `core/ui.py` don't have
to import from `main` at runtime just to avoid a circular import.
"""

from concurrent.futures import ThreadPoolExecutor


class RuntimeState:
    def __init__(self):
        self.debug = False
        self.thread_pool = ThreadPoolExecutor(
            max_workers=15, thread_name_prefix="vkit_worker"
        )


runtime = RuntimeState()
