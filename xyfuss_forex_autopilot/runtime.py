from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Callable


class PersistentTradingState:
    """Small crash-safe state store for submitted orders and emergency controls."""

    def __init__(self, path: str = "data/trading-state.json"):
        self.path = Path(path)
        self._lock = Lock()

    def load(self) -> dict:
        if not self.path.exists():
            return {"submitted_orders": {}, "emergency_stop": False}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {"submitted_orders": {}, "emergency_stop": False, "recovery_warning": "State file could not be read"}
        data.setdefault("submitted_orders", {})
        data.setdefault("emergency_stop", False)
        return data

    def save(self, state: dict) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self.path)

    def set_emergency_stop(self, active: bool) -> dict:
        state = self.load()
        state["emergency_stop"] = active
        self.save(state)
        return state

    def record_submission(self, client_order_id: str, result: dict) -> dict:
        state = self.load()
        state["submitted_orders"][client_order_id] = result
        self.save(state)
        return state


class HealthMonitor:
    def __init__(self, broker_connector: Callable[[], bool], interval_seconds: int = 30):
        self.broker_connector = broker_connector
        self.interval_seconds = interval_seconds
        self.failures = 0

    def check(self) -> dict:
        try:
            connected = bool(self.broker_connector())
        except Exception:
            connected = False
        self.failures = 0 if connected else self.failures + 1
        return {"healthy": connected, "consecutive_failures": self.failures, "fail_safe": not connected}


class RecoverableProcess:
    def __init__(self, operation: Callable[[], dict], max_attempts: int = 3):
        self.operation = operation
        self.max_attempts = max(1, max_attempts)

    def run(self) -> dict:
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return {"attempt": attempt, "result": self.operation(), "recovered": attempt > 1}
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        return {"attempt": self.max_attempts, "result": None, "recovered": False, "error": last_error}
