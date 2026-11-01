from xyfuss_forex_autopilot.dashboard import DashboardServer


def test_dashboard_server_serves_page():
    server = DashboardServer(host="127.0.0.1", port=8765)
    server.start()
    assert server._server is not None
    server.stop()
