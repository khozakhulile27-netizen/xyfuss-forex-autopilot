import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from xyfuss_forex_autopilot.auth import (
    generate_dashboard_password,
    hash_password,
    load_broker_credentials,
    save_broker_credentials,
    verify_password,
)
from xyfuss_forex_autopilot.scheduler import DashboardServer


def test_password_hash_is_salted_and_verifies():
    password = generate_dashboard_password()
    first = hash_password(password)
    second = hash_password(password)
    assert first != second
    assert verify_password(password, first)
    assert verify_password(password + "wrong", first) is False


def test_broker_credentials_file_is_owner_readable_only(tmp_path):
    destination = tmp_path / "mt5-demo.json"
    save_broker_credentials(
        {"login": "demo-user", "password": "demo-password", "server": "Demo-Server", "environment": "demo"},
        str(destination),
    )
    assert destination.stat().st_mode & 0o777 == 0o600
    assert "demo-password" not in destination.read_text()
    loaded = load_broker_credentials(str(destination))
    assert loaded["login"] == "demo-user"


def test_password_login_and_emergency_stop(tmp_path):
    password = generate_dashboard_password()
    password_hash = hash_password(password)
    stopped = []
    server = DashboardServer(
        host="127.0.0.1",
        port=0,
        password_hash=password_hash,
        on_emergency_stop=lambda: stopped.append(True),
    )
    server.start()
    port = server._server.server_address[1]

    unauthorized = Request(f"http://127.0.0.1:{port}/status")
    with pytest.raises(Exception) as exc:
        urlopen(unauthorized, timeout=2)
    assert getattr(exc.value, "code", None) == 401

    login = Request(
        f"http://127.0.0.1:{port}/login",
        data=json.dumps({"password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(login, timeout=2) as response:
        session_cookie = response.headers["Set-Cookie"].split(";", 1)[0]
        assert response.status == 200

    status = Request(
        f"http://127.0.0.1:{port}/status",
        headers={"Cookie": session_cookie},
    )
    with urlopen(status, timeout=2) as response:
        assert response.status == 200

    emergency = Request(
        f"http://127.0.0.1:{port}/emergency-stop",
        data=b"",
        headers={"Cookie": session_cookie},
        method="POST",
    )
    with urlopen(emergency, timeout=2) as response:
        assert response.status == 200
    assert stopped == [True]
    server.stop()


def test_dashboard_never_returns_credentials():
    password_hash = hash_password(generate_dashboard_password())
    server = DashboardServer(host="127.0.0.1", port=0, password_hash=password_hash)
    assert "password_hash" not in server._page()
    assert server.password_hash == password_hash
