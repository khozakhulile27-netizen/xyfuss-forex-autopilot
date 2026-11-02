from __future__ import annotations

import json
import secrets
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import threading
import time
from typing import Callable

from xyfuss_forex_autopilot.auth import verify_password


class AutonomousScheduler:
    """Run an optional autonomous cycle in a background thread."""

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


class DashboardServer:
    """Simple mobile-friendly dashboard served locally."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        status: dict | None = None,
        access_token: str | None = None,
        password_hash: str | None = None,
        on_emergency_stop: Callable[[], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.status = status or {"status": "paper", "market": "EUR/USD", "autopilot": "online"}
        self.access_token = access_token
        self.password_hash = password_hash
        self.sessions: dict[str, float] = {}
        self.on_emergency_stop = on_emergency_stop
        self._server = None
        self._thread = None

    def _page(self) -> str:
        return """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>XYFUSS Forex Autopilot</title>
            <style>
                body { font-family: Arial, sans-serif; background: #08121d; color: #eaeef5; margin: 0; padding: 24px; }
                .card { max-width: 900px; margin: 0 auto; background: #101d2d; border-radius: 18px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); }
                h1 { margin-top: 0; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
                .metric { background: #16283d; border-radius: 12px; padding: 16px; }
                .tag { display: inline-block; background: #1f9d72; color: white; padding: 6px 10px; border-radius: 999px; font-size: 12px; margin-bottom: 8px; }
                @media (max-width: 640px) { body { padding: 16px; } }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="tag">ACTIVE</div>
                <h1>XYFUSS Forex Autopilot</h1>
                <p>Evidence-driven and autonomous, paper-trading ready.</p>
                <div class="grid">
                    <div class="metric"><strong>Mode</strong><br />paper</div>
                    <div class="metric"><strong>Market</strong><br />EUR/USD</div>
                    <div class="metric"><strong>Risk</strong><br />1.5% daily</div>
                    <div class="metric"><strong>System</strong><br />Online</div>
                </div>
                <h3>Decision loop</h3>
                <ul>
                    <li>Discover</li>
                    <li>Investigate</li>
                    <li>Gather Evidence</li>
                    <li>Analyse</li>
                    <li>Compare</li>
                    <li>Recommend</li>
                    <li>Rank</li>
                    <li>Select</li>
                    <li>Risk Verification</li>
                    <li>Execute</li>
                    <li>Verify</li>
                    <li>Learn</li>
                </ul>
            </div>
        </body>
        </html>
        """

    def _handler_factory(self):
        status_payload = json.dumps(self.status)
        access_token = self.access_token
        password_hash = self.password_hash
        sessions = self.sessions

        class Handler(BaseHTTPRequestHandler):
            def _authorized(self) -> bool:
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                session = cookie.get("xyfuss_session")
                if session and sessions.get(session.value, 0) > time.time():
                    return True
                if password_hash is None and (self.server.dashboard_binds_local or access_token is None):
                    return True
                header_token = self.headers.get("X-XYFUSS-TOKEN")
                return bool(access_token) and header_token == access_token

            def _json(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if not self._authorized():
                    if password_hash:
                        body = b'<!doctype html><html><body><h1>XYFUSS login required</h1><form method="post" action="/login"><label>Password <input type="password" name="password" autocomplete="current-password" required></label><button type="submit">Sign in</button></form></body></html>'
                        self.send_response(401)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    self.send_response(401)
                    self.end_headers()
                    return
                if self.path in {"/", "/index.html"}:
                    body = self.server.dashboard_page.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path == "/status":
                    body = status_payload.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/login" and password_hash:
                    length = int(self.headers.get("Content-Length", "0"))
                    try:
                        body = self.rfile.read(length).decode("utf-8")
                        if self.headers.get("Content-Type", "").startswith("application/json"):
                            credentials = json.loads(body)
                            password = credentials.get("password", "")
                        else:
                            password = urllib.parse.parse_qs(body).get("password", [""])[0]
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        password = ""
                    if not isinstance(password, str) or not verify_password(password, password_hash):
                        self._json(401, {"status": "authentication_failed"})
                        return
                    session = secrets.token_urlsafe(32)
                    sessions[session] = time.time() + 8 * 60 * 60
                    body = b'{"status":"authenticated"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Set-Cookie", f"xyfuss_session={session}; HttpOnly; SameSite=Strict; Max-Age=28800; Path=/")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if not self._authorized():
                    self.send_response(401)
                    self.end_headers()
                    return
                if self.path == "/emergency-stop":
                    if self.server.on_emergency_stop:
                        self.server.on_emergency_stop()
                    self.server.dashboard_status["autopilot"] = "stopped"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    body = b'{"status":"stopped"}'
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, *_args):
                return

        Handler.dashboard_page = self._page()
        return Handler

    def start(self):
        binds_non_loopback = self.host not in {"127.0.0.1", "localhost", "::1"}
        if binds_non_loopback and not self.access_token:
            raise ValueError("A dashboard access token is required for non-loopback binding.")
        self._server = HTTPServer((self.host, self.port), self._handler_factory())
        self._server.dashboard_binds_local = self.host in {"127.0.0.1", "localhost", "::1"}
        self._server.on_emergency_stop = self.on_emergency_stop
        self._server.dashboard_status = self.status
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
