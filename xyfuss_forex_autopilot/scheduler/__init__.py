from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class DashboardServer:
    """Simple mobile-friendly dashboard served locally."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000, status: dict | None = None):
        self.host = host
        self.port = port
        self.status = status or {"status": "paper", "market": "EUR/USD", "autopilot": "online"}
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

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
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

            def log_message(self, *_args):
                return

        Handler.dashboard_page = self._page()
        return Handler

    def start(self):
        self._server = HTTPServer((self.host, self.port), self._handler_factory())
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
