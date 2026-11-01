from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class AuditReporter:
    """Maintain execution logs and audit history for traceability."""

    def __init__(self):
        self.entries: list[dict[str, Any]] = []

    def record(self, event: str, details: dict | None = None) -> dict:
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        self.entries.append(payload)
        return payload

    def report(self) -> dict:
        return {"events": len(self.entries), "entries": self.entries[-10:]}
