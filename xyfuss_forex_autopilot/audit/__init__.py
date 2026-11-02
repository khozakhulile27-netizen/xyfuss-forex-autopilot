from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any


class AuditReporter:
    """Keep an in-memory, append-only audit trail for risk decisions."""

    def __init__(self, ledger_path: str | Path | None = None):
        self.records: list[dict[str, Any]] = []
        self._lock = Lock()
        self.ledger_path = Path(ledger_path) if ledger_path else None
        if self.ledger_path:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details or {},
        }
        with self._lock:
            self.records.append(record)
            if self.ledger_path:
                line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
                with self.ledger_path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
        return record

    def list_records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [record.copy() for record in self.records]

    def report(self) -> list[dict[str, Any]]:
        return self.list_records()
