from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import string
from pathlib import Path
import os


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "$scrypt$1$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        parts = encoded.split("$")
        if len(parts) != 5 or parts[0] != "":
            return False
        _empty, scheme, version, salt_text, digest_text = parts
        if scheme != "scrypt" or version != "1":
            return False

        def decode(value: str) -> bytes:
            return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

        expected = decode(digest_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=decode(salt_text), n=2**14, r=8, p=1, dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError, UnicodeError):
        return False


def generate_dashboard_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(character.islower() for character in password)
            and any(character.isupper() for character in password)
            and any(character.isdigit() for character in password)
            and any(character in "!@#$%^&*_-" for character in password)
        ):
            return password


def save_dashboard_hash(encoded_hash: str, path: str = "data/dashboard-auth.json") -> None:
    import json
    import os

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"password_hash": encoded_hash}), encoding="utf-8")
    os.chmod(destination, 0o600)


def save_broker_credentials(credentials: dict[str, str], path: str) -> None:
    import json
    import os

    from cryptography.fernet import Fernet

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    key_path = destination.with_suffix(destination.suffix + ".key")
    if key_path.exists():
        key = key_path.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        os.chmod(key_path, 0o600)
    payload = Fernet(key).encrypt(json.dumps(credentials, sort_keys=True).encode("utf-8")).decode("ascii")
    destination.write_text(json.dumps({"encrypted": payload}), encoding="utf-8")
    os.chmod(destination, 0o600)


def load_broker_credentials(path: str) -> dict[str, str]:
    import json

    from cryptography.fernet import Fernet

    source = Path(path)
    if not source.exists():
        return {}
    key_path = source.with_suffix(source.suffix + ".key")
    with source.open("r", encoding="utf-8") as handle:
        envelope = json.load(handle)
    if "encrypted" not in envelope:
        raise ValueError("Credential vault format is invalid.")
    if not key_path.exists():
        raise ValueError("Credential vault key is unavailable.")
    decrypted = Fernet(key_path.read_bytes().strip()).decrypt(envelope["encrypted"].encode("ascii"))
    return {str(key): str(value) for key, value in json.loads(decrypted.decode("utf-8")).items()}


def load_mt5_demo_credentials(path: str) -> dict[str, str]:
    """Load demo credentials exclusively from environment variables."""
    env = {
        "login": os.getenv("MT5_DEMO_LOGIN") or os.getenv("MT5_LOGIN") or os.getenv("EXNESS_MT5_LOGIN"),
        "password": os.getenv("MT5_DEMO_PASSWORD") or os.getenv("MT5_PASSWORD") or os.getenv("EXNESS_MT5_PASSWORD"),
        "server": os.getenv("MT5_DEMO_SERVER") or os.getenv("MT5_SERVER") or os.getenv("EXNESS_MT5_SERVER") or "Exness-MT5Trial10",
    }
    if all(env.values()):
        return {key: value for key, value in env.items()} | {"environment": "demo"}
    return {}


def load_ctrader_demo_credentials() -> dict[str, str]:
    credentials = {
        "client_id": os.getenv("CTRADER_DEMO_CLIENT_ID", ""),
        "client_secret": os.getenv("CTRADER_DEMO_CLIENT_SECRET", ""),
        "access_token": os.getenv("CTRADER_DEMO_ACCESS_TOKEN", ""),
        "ctid_trader_account_id": os.getenv("CTRADER_DEMO_ACCOUNT_ID", ""),
        "environment": "demo",
    }
    return credentials if all(credentials[key] for key in ("client_id", "client_secret", "access_token", "ctid_trader_account_id")) else {}


def redact_secrets(text: object, secrets: object) -> str:
    rendered = str(text)
    values = secrets.values() if isinstance(secrets, dict) else []
    for value in values:
        secret = str(value)
        if secret:
            rendered = rendered.replace(secret, "[REDACTED]")
    return rendered
