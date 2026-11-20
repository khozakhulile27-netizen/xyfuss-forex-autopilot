from __future__ import annotations

import json
import secrets
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import threading
from typing import Callable

from xyfuss_forex_autopilot.auth import verify_password


class AutonomousScheduler:
    """Run autonomous cycles repeatedly without dying on one failed cycle."""

    def __init__(self, interval_seconds: int = 300, callback: Callable[[], object] | None = None):
        if int(interval_seconds) < 1:
            raise ValueError("interval_seconds must be at least one second.")
        self.interval_seconds = int(interval_seconds)
        self.callback = callback or (lambda: None)
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.cycles = 0
        self.last_result = None
        self.last_error = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return self

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                result = self.callback()
                with self._lock:
                    self.last_result = result
                    self.last_error = None
                    self.cycles += 1
            except Exception as exc:
                with self._lock:
                    self.last_error = type(exc).__name__
                    self.cycles += 1
            self._stop_event.wait(self.interval_seconds)

    def status(self) -> dict:
        with self._lock:
            return {
                "running": bool(self._thread and self._thread.is_alive()),
                "cycles": self.cycles,
                "last_error": self.last_error,
                "last_result": self.last_result,
            }

    def stop(self):
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=min(5.0, float(self.interval_seconds) + 0.5))

