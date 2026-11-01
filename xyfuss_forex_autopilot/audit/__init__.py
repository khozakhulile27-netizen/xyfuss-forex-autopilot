from __future__ import annotations

import threading
import time
from typing import Callable


class AutonomousScheduler:
    """Runs a periodic autonomous cycle in a background thread."""

    def __init__(self, interval_seconds: int = 300, callback: Callable[[], None] | None = None):
        self.interval_seconds = interval_seconds
        self.callback = callback or (lambda: None)
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return self

    def _run_loop(self):
        while not self._stop_event.is_set():
            self.callback()
            time.sleep(self.interval_seconds)

    def stop(self):
        self._stop_event.set()
