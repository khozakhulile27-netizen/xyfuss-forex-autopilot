from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlparse

from xyfuss_forex_autopilot.control_plane.ctrader_oauth import CTraderOAuthError, CTraderOAuthService


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout=15):
        self.requests.append(request)
        return FakeResponse(self.payloads.pop(0))


def make_service(tmp_path, opener):
    key = base64.urlsafe_b64encode(b"x" * 32).decode("ascii")
    return CTraderOAuthService(
        database_path=tmp_path / "private" / "tokens.sqlite3",
        client_id="public-client-id",
        client_secret="test-secret-not-for-logs",
        redirect_uri="https://control.example.test/api/v1/ctrader/callback",
        encryption_key=key,
        opener=opener,
    )


def test_authorization_uses_read_only_scope_and_random_state(tmp_path):
    service = make_service(tmp_path, FakeOpener())
    first = urlparse(service.authorization_url())
    second = urlparse(service.authorization_url())
    first_query = parse_qs(first.query)
    second_query = parse_qs(second.query)

    assert first.scheme == "https"
    assert first.netloc == "id.ctrader.com"
    assert first_query["scope"] == ["accounts"]
    assert first_query["product"] == ["web"]
    assert first_query["client_id"] == ["public-client-id"]
    assert first_query["state"][0] != second_query["state"][0]
    assert service.status()["connected"] is False


def test_callback_encrypts_tokens_and_status_never_returns_them(tmp_path):
    opener = FakeOpener({
        "accessToken": "access-token-secret",
        "refreshToken": "refresh-token-secret",
        "expiresIn": 3600,
        "tokenType": "bearer",
        "errorCode": None,
    })
    service = make_service(tmp_path, opener)
    query = parse_qs(urlparse(service.authorization_url()).query)
    service.complete_callback("one-minute-code", query["state"][0])

    status = service.status()
    assert status["connected"] is True
    assert status["environment"] == "demo"
    assert "access-token-secret" not in json.dumps(status)
    assert "refresh-token-secret" not in json.dumps(status)

    stored = service._load_tokens()
    assert stored is not None
    encrypted_blob, _ = service._db().__enter__() if False else (None, None)
    assert service.access_token() == "access-token-secret"
    with service._db() as db:
        blob = db.execute("SELECT encrypted FROM oauth_tokens WHERE id=1").fetchone()[0]
    assert b"access-token-secret" not in blob
    assert b"refresh-token-secret" not in blob


def test_oauth_state_is_one_time_use(tmp_path):
    service = make_service(tmp_path, FakeOpener())
    state = parse_qs(urlparse(service.authorization_url()).query)["state"][0]
    service._consume_state(state)
    try:
        service._consume_state(state)
    except CTraderOAuthError as exc:
        assert "expired or was already used" in str(exc)
    else:
        raise AssertionError("OAuth state must not be reusable")


def test_access_token_refreshes_before_expiry(tmp_path):
    opener = FakeOpener(
        {
            "accessToken": "old-access",
            "refreshToken": "old-refresh",
            "expiresIn": 1,
            "errorCode": None,
        },
        {
            "accessToken": "new-access",
            "refreshToken": "new-refresh",
            "expiresIn": 3600,
            "errorCode": None,
        },
    )
    service = make_service(tmp_path, opener)
    state = parse_qs(urlparse(service.authorization_url()).query)["state"][0]
    service.complete_callback("short-lived-code", state)

    assert service.access_token() == "new-access"
    assert len(opener.requests) == 2
    assert opener.requests[1].get_method() == "POST"
    assert "grant_type=refresh_token" in opener.requests[1].data.decode("ascii")


def test_disconnect_removes_encrypted_token_record(tmp_path):
    opener = FakeOpener({
        "accessToken": "access",
        "refreshToken": "refresh",
        "expiresIn": 3600,
        "errorCode": None,
    })
    service = make_service(tmp_path, opener)
    state = parse_qs(urlparse(service.authorization_url()).query)["state"][0]
    service.complete_callback("code", state)
    service.disconnect()
    assert service.status()["connected"] is False


def test_invalid_encryption_key_is_rejected(tmp_path):
    try:
        CTraderOAuthService(
            database_path=tmp_path / "tokens.sqlite3",
            client_id="id",
            client_secret="secret",
            redirect_uri="https://example.test/callback",
            encryption_key=base64.urlsafe_b64encode(b"short").decode("ascii"),
        )
    except CTraderOAuthError as exc:
        assert "exactly 32 bytes" in str(exc)
    else:
        raise AssertionError("Invalid encryption key must be rejected")
