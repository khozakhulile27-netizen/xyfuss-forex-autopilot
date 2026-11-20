from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from threading import RLock
from typing import Callable


class PersistentTradingState:
    """Crash-safe state store for orders, equity baselines, and emergency controls.

    A missing state file means a first run. An unreadable or invalid existing
    file is treated as unsafe and activates the emergency stop.
    """

    def __init__(self, path: str = "data/trading-state.json"):
        self.path = Path(path)
        self._lock = RLock()

    @staticmethod
    def _empty_state() -> dict:
        return {
            "submitted_orders": {},
            "emergency_stop": False,
            "risk": {},
        }

    def load(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return self._empty_state()
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict):
                    raise ValueError("Trading state must be a JSON object.")
                submitted = data.get("submitted_orders", {})
                risk = data.get("risk", {})
                if not isinstance(submitted, dict) or not isinstance(risk, dict):
                    raise ValueError("Trading state contains invalid fields.")
                if not isinstance(data.get("emergency_stop", False), bool):
                    raise ValueError("Emergency-stop state must be boolean.")
                data.setdefault("submitted_orders", {})
                data.setdefault("emergency_stop", False)
                data.setdefault("risk", {})
                return data
            except (json.JSONDecodeError, OSError, ValueError, TypeError):
                return {
                    "submitted_orders": {},
                    "emergency_stop": True,
                    "risk": {},
                    "recovery_warning": "Trading state is unreadable or invalid; manual review is required.",
                }

    def save(self, state: dict) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self.path)

    def set_emergency_stop(self, active: bool) -> dict:
        with self._lock:
            state = self.load()
            state["emergency_stop"] = bool(active)
            self.save(state)
            return state

    def record_equity(self, equity: float, observed_at: datetime | None = None) -> dict:
        """Persist daily starting equity and high-water mark; return loss amounts."""
        value = float(equity)
        if not isfinite(value) or value <= 0:
            raise ValueError("Account equity must be a finite positive number.")
        moment = observed_at or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware.")
        day = moment.astimezone(timezone.utc).date().isoformat()

        with self._lock:
            state = self.load()
            if state.get("recovery_warning"):
                state["emergency_stop"] = True
                self.save(state)
                raise RuntimeError(state["recovery_warning"])

            risk = state.setdefault("risk", {})
            if not risk:
                risk.update({
                    "day": day,
                    "day_start_equity": value,
                    "peak_equity": value,
                    "last_equity": value,
                })
            else:
                if risk.get("day") != day:
                    # Carry the last observed equity forward as the day boundary
                    # baseline so a gap while the process was offline is not hidden.
                    risk["day_start_equity"] = float(risk.get("last_equity", value))
                    risk["day"] = day
                peak = float(risk.get("peak_equity", value))
                risk["peak_equity"] = max(peak, value)
                risk["last_equity"] = value

            daily_start = float(risk["day_start_equity"])
            peak_equity = float(risk["peak_equity"])
            daily_loss = max(0.0, daily_start - value)
            drawdown = max(0.0, peak_equity - value)
            self.save(state)
            return {
                "equity": value,
                "daily_start_equity": daily_start,
                "peak_equity": peak_equity,
                "daily_loss": daily_loss,
                "drawdown": drawdown,
                "day": day,
                "emergency_stop": bool(state.get("emergency_stop", False)),
            }

    def record_submission(self, client_order_id: str, result: dict) -> dict:
        with self._lock:
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
