"""
Shared runtime state for VKit Toolbox.

Holds objects that both `main.py` and the `core` modules need (debug flag,
shared thread pool) so that `core/managers.py` and `core/ui.py` don't have
to import from `main` at runtime just to avoid a circular import.
"""

import functools
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from core.logger import logger


class RuntimeState:
    def __init__(self):
        self.debug = False
        self.thread_pool = ThreadPoolExecutor(
            max_workers=15, thread_name_prefix="vkit_worker"
        )

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit work to the shared pool, guaranteeing exceptions are logged.

        A plain ``ThreadPoolExecutor.submit`` stores any exception on the
        returned Future; if nobody ever calls ``future.result()`` (which is
        the case everywhere in this app - work is fire-and-forget), the error
        vanishes without a trace. Wrapping the callable makes every background
        failure land in the log file regardless of debug mode.
        """

        @functools.wraps(fn)
        def _guarded(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception:
                logger.exception(
                    "Unhandled exception in background task %s",
                    getattr(fn, "__qualname__", repr(fn)),
                )
                if self.debug:
                    raise
                return None

        return self.thread_pool.submit(_guarded, *args, **kwargs)


runtime = RuntimeState()
