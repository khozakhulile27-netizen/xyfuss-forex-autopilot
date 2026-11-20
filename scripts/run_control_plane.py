from __future__ import annotations

import os
from wsgiref.simple_server import make_server

from xyfuss_forex_autopilot.control_plane.ctrader_oauth import create_wsgi_app


def main() -> None:
    # Keep this service private. Expose it only through the authenticated
    # dashboard reverse proxy or a private VPN; never bind it to 0.0.0.0.
    host = os.environ.get("XYFUSS_CONTROL_API_HOST", "127.0.0.1")
    port = int(os.environ.get("XYFUSS_CONTROL_API_PORT", "8765"))
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("Refusing public bind. Put the control API behind a private authenticated reverse proxy.")
    app = create_wsgi_app()
    with make_server(host, port, app) as server:
        print(f"XYFUSS cTrader control API listening privately on {host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
