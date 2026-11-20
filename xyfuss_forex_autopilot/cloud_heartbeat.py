"""Optional authenticated presence reporting to XYFUSS CLOUD.

Only fixed identity/version/mode metadata is sent. This is not a broker
connection and does not send market data, orders, positions, or credentials.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from time import monotonic
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class CloudHeartbeat:
    def __init__(
        self,
        base_url: str,
        token: str,
        version: str = "0.1.0",
        interval_seconds: int = 60,
        timeout_seconds: float = 5.0,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("XYFUSS_CLOUD_URL must be an HTTP(S) URL")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Non-loopback Cloud URLs require HTTPS")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("XYFUSS_CLOUD_URL must be an origin URL without a path")
        if len(token) < 32:
            raise ValueError("Cloud agent token must contain at least 32 characters")
        if not version or len(version) > 40 or not version.isascii():
            raise ValueError("Agent version must be 1-40 ASCII characters")
        if isinstance(interval_seconds, bool) or interval_seconds < 15:
            raise ValueError("Heartbeat interval must be at least 15 seconds")

        self.url = base_url.rstrip("/") + "/v1/agents/heartbeat"
        self.token = token
        self.version = version
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = "not_started"
        self._last_success_monotonic: float | None = None

    @classmethod
    def from_environment(cls) -> "CloudHeartbeat | None":
        base_url = os.environ.get("XYFUSS_CLOUD_URL", "").strip()
        token = os.environ.get("XYFUSS_CLOUD_AGENT_TOKEN", "").strip()
        token_file = os.environ.get("XYFUSS_CLOUD_AGENT_TOKEN_FILE", "").strip()
        if token_file:
            try:
                token = Path(token_file).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ValueError("Configured Cloud agent token file is unavailable") from exc
        if not base_url and not token:
            return None
        if not base_url or not token:
            raise ValueError("Both XYFUSS_CLOUD_URL and a Cloud agent token are required")
        raw_interval = os.environ.get("XYFUSS_CLOUD_HEARTBEAT_INTERVAL_SECONDS", "60")
        try:
            interval = int(raw_interval)
        except ValueError as exc:
            raise ValueError("Cloud heartbeat interval must be an integer") from exc
        return cls(
            base_url=base_url,
            token=token,
            version=os.environ.get("XYFUSS_AGENT_VERSION", "0.1.0"),
            interval_seconds=interval,
        )

    @property
    def status(self) -> str:
        if self._last_success_monotonic is not None:
            if monotonic() - self._last_success_monotonic <= self.interval_seconds * 3:
                return "online"
        return self._status

    def send_once(self) -> bool:
        payload = json.dumps({
            "agent_id": "xyfuss-forex-autopilot",
            "version": self.version,
            "mode": "paper",
        }).encode("utf-8")
        request = Request(
            self.url,
            data=payload,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                raise URLError("Cloud heartbeat was not accepted")
            result = json.loads(response.read().decode("utf-8"))
        if (
            result.get("accepted") is not True
            or result.get("agent", {}).get("agent_id") != "xyfuss-forex-autopilot"
            or result.get("agent", {}).get("mode") != "paper"
        ):
            raise URLError("Cloud returned an invalid paper-mode acknowledgement")
        self._last_success_monotonic = monotonic()
        self._status = "online"
        return True

    def start(self) -> "CloudHeartbeat":
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="xyfuss-forex-cloud-heartbeat",
            daemon=True,
        )
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.send_once()
            except (OSError, URLError, ValueError, json.JSONDecodeError):
                self._status = "offline"
            self._stop.wait(self.interval_seconds)

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.timeout_seconds + 1)
        self._thread = None
