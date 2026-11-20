from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CTraderOAuthError(RuntimeError):
    """Safe-to-display OAuth error; never contains credentials or token values."""


class CTraderOAuthService:
    """Single-operator cTrader OAuth flow with encrypted, server-side token storage."""

    TOKEN_URL = "https://openapi.ctrader.com/apps/token"
    AUTHORIZE_URL = "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
    AAD = b"xyfuss-ctrader-oauth-v1"

    def __init__(
        self,
        database_path: str | Path,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        encryption_key: str,
        opener: Callable = urlopen,
    ) -> None:
        if not all((client_id.strip(), client_secret.strip(), redirect_uri.strip())):
            raise CTraderOAuthError("cTrader application settings are incomplete.")
        try:
            key = base64.urlsafe_b64decode(encryption_key.encode("ascii"))
        except (ValueError, UnicodeError) as exc:
            raise CTraderOAuthError("The token encryption key is invalid.") from exc
        if len(key) != 32:
            raise CTraderOAuthError("The token encryption key must decode to exactly 32 bytes.")

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._cipher = AESGCM(key)
        self._opener = opener
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._init_db()

    @classmethod
    def from_environment(cls) -> "CTraderOAuthService":
        required = (
            "CTRADER_CLIENT_ID",
            "CTRADER_CLIENT_SECRET",
            "CTRADER_REDIRECT_URI",
            "XYFUSS_TOKEN_ENCRYPTION_KEY",
        )
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise CTraderOAuthError("Server-side cTrader configuration is incomplete: " + ", ".join(missing))
        return cls(
            database_path=os.environ.get("XYFUSS_TOKEN_DATABASE", "data/ctrader_tokens.sqlite3"),
            client_id=os.environ["CTRADER_CLIENT_ID"],
            client_secret=os.environ["CTRADER_CLIENT_SECRET"],
            redirect_uri=os.environ["CTRADER_REDIRECT_URI"],
            encryption_key=os.environ["XYFUSS_TOKEN_ENCRYPTION_KEY"],
        )

    @contextmanager
    def _db(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            yield connection
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS oauth_states "
                "(state_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS oauth_tokens "
                "(id INTEGER PRIMARY KEY CHECK (id = 1), encrypted BLOB NOT NULL, "
                "expires_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)"
            )
        try:
            self.database_path.chmod(0o600)
        except OSError:
            pass

    def _seal(self, payload: dict) -> bytes:
        nonce = secrets.token_bytes(12)
        ciphertext = self._cipher.encrypt(nonce, json.dumps(payload).encode("utf-8"), self.AAD)
        return nonce + ciphertext

    def _open(self, blob: bytes) -> dict:
        try:
            return json.loads(self._cipher.decrypt(blob[:12], blob[12:], self.AAD))
        except Exception as exc:
            raise CTraderOAuthError("Stored cTrader credentials could not be decrypted; reconnect is required.") from exc

    def authorization_url(self) -> str:
        state = secrets.token_urlsafe(32)
        digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
        now = int(time.time())
        with self._db() as db:
            db.execute("DELETE FROM oauth_states WHERE expires_at < ?", (now,))
            db.execute(
                "INSERT INTO oauth_states(state_hash, expires_at) VALUES (?, ?)",
                (digest, now + 600),
            )
        query = urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "accounts",
            "product": "web",
            "state": state,
        })
        return f"{self.AUTHORIZE_URL}?{query}"

    def _consume_state(self, state: str) -> None:
        if not state or len(state) > 256:
            raise CTraderOAuthError("The cTrader sign-in state is missing or invalid.")
        digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
        now = int(time.time())
        with self._db() as db:
            row = db.execute(
                "SELECT expires_at FROM oauth_states WHERE state_hash = ?", (digest,)
            ).fetchone()
            db.execute("DELETE FROM oauth_states WHERE state_hash = ?", (digest,))
        if row is None or int(row[0]) < now:
            raise CTraderOAuthError("The cTrader sign-in request expired or was already used. Start again.")

    def _request_tokens(self, params: dict, method: str = "GET") -> dict:
        url = self.TOKEN_URL
        data = None
        headers = {"Accept": "application/json"}
        if method == "GET":
            url += "?" + urlencode(params)
        else:
            data = urlencode(params).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise CTraderOAuthError("cTrader token service could not be reached. Try again later.") from exc
        if not isinstance(payload, dict) or payload.get("errorCode"):
            raise CTraderOAuthError("cTrader rejected the authorisation. Check the app approval and redirect URI.")
        if not payload.get("accessToken") or not payload.get("refreshToken"):
            raise CTraderOAuthError("cTrader returned an incomplete token response.")
        return payload

    def complete_callback(self, code: str, state: str) -> None:
        self._consume_state(state)
        if not code or len(code) > 2048:
            raise CTraderOAuthError("cTrader did not return a valid authorisation code.")
        payload = self._request_tokens({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        expires_in = int(payload.get("expiresIn", 0))
        if expires_in <= 0:
            raise CTraderOAuthError("cTrader returned an invalid token lifetime.")
        encrypted = self._seal({
            "access_token": payload["accessToken"],
            "refresh_token": payload["refreshToken"],
            "token_type": payload.get("tokenType", "bearer"),
        })
        now = int(time.time())
        with self._db() as db:
            db.execute(
                "INSERT INTO oauth_tokens(id, encrypted, expires_at, updated_at) VALUES (1, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET encrypted=excluded.encrypted, "
                "expires_at=excluded.expires_at, updated_at=excluded.updated_at",
                (encrypted, now + expires_in, now),
            )

    def _load_tokens(self) -> tuple[dict, int] | None:
        with self._db() as db:
            row = db.execute(
                "SELECT encrypted, expires_at FROM oauth_tokens WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return self._open(row[0]), int(row[1])

    def access_token(self) -> str:
        stored = self._load_tokens()
        if stored is None:
            raise CTraderOAuthError("No cTrader account is connected yet.")
        tokens, expires_at = stored
        if expires_at - int(time.time()) <= 300:
            payload = self._request_tokens({
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }, method="POST")
            expires_in = int(payload.get("expiresIn", 0))
            if expires_in <= 0:
                raise CTraderOAuthError("cTrader returned an invalid refreshed token lifetime.")
            tokens = {
                "access_token": payload["accessToken"],
                "refresh_token": payload["refreshToken"],
                "token_type": payload.get("tokenType", "bearer"),
            }
            now = int(time.time())
            with self._db() as db:
                db.execute(
                    "UPDATE oauth_tokens SET encrypted=?, expires_at=?, updated_at=? WHERE id=1",
                    (self._seal(tokens), now + expires_in, now),
                )
        return str(tokens["access_token"])

    def status(self) -> dict:
        stored = self._load_tokens()
        if stored is None:
            return {"connected": False, "provider": "cTrader", "environment": "demo"}
        _, expires_at = stored
        return {
            "connected": True,
            "provider": "cTrader",
            "environment": "demo",
            "token_expires_at": expires_at,
            "refresh_required": expires_at - int(time.time()) <= 300,
        }

    def disconnect(self) -> None:
        with self._db() as db:
            db.execute("DELETE FROM oauth_tokens WHERE id = 1")


def create_wsgi_app(service: CTraderOAuthService | None = None):
    """Small same-origin WSGI API; deploy behind private operator access/TLS."""

    def app(environ, start_response):
        from urllib.parse import parse_qs

        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET")
        try:
            active = service or CTraderOAuthService.from_environment()
            if path == "/api/v1/ctrader/connect" and method == "GET":
                body = {"authorization_url": active.authorization_url()}
                status = "200 OK"
            elif path == "/api/v1/ctrader/callback" and method == "GET":
                query = parse_qs(environ.get("QUERY_STRING", ""))
                if query.get("error"):
                    raise CTraderOAuthError("cTrader sign-in was cancelled or denied.")
                active.complete_callback(
                    query.get("code", [""])[0],
                    query.get("state", [""])[0],
                )
                body = {"connected": True, "provider": "cTrader", "environment": "demo"}
                status = "200 OK"
            elif path == "/api/v1/ctrader/status" and method == "GET":
                body = active.status()
                status = "200 OK"
            elif path == "/api/v1/ctrader/disconnect" and method == "POST":
                active.disconnect()
                body = {"connected": False, "provider": "cTrader"}
                status = "200 OK"
            else:
                body = {"error": "not_found"}
                status = "404 Not Found"
        except CTraderOAuthError as exc:
            body = {"error": str(exc)}
            status = "400 Bad Request"
        except Exception:
            body = {"error": "cTrader control service is unavailable; check server configuration."}
            status = "503 Service Unavailable"

        encoded = json.dumps(body).encode("utf-8")
        start_response(status, [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(encoded))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [encoded]

    return app
