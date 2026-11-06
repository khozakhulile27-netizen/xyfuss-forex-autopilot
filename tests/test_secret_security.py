import logging

from xyfuss_forex_autopilot.auth import load_ctrader_demo_credentials, load_mt5_demo_credentials, redact_secrets
from xyfuss_forex_autopilot.config import load_settings


def test_mt5_credentials_load_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "environment-secret")
    monkeypatch.setenv("MT5_SERVER", "Exness-MT5Demo1")
    credentials = load_mt5_demo_credentials(str(tmp_path / "missing.json"))
    assert credentials["environment"] == "demo"
    assert credentials["password"] == "environment-secret"


def test_missing_environment_credentials_fail_closed(monkeypatch, tmp_path):
    for name in ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "EXNESS_MT5_LOGIN", "EXNESS_MT5_PASSWORD", "EXNESS_MT5_SERVER"):
        monkeypatch.delenv(name, raising=False)
    assert load_mt5_demo_credentials(str(tmp_path / "missing.json")) == {}


def test_ctrader_credentials_load_from_environment(monkeypatch):
    monkeypatch.setenv("CTRADER_DEMO_CLIENT_ID", "client")
    monkeypatch.setenv("CTRADER_DEMO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("CTRADER_DEMO_ACCESS_TOKEN", "token")
    monkeypatch.setenv("CTRADER_DEMO_ACCOUNT_ID", "123")
    credentials = load_ctrader_demo_credentials()
    assert credentials["environment"] == "demo"
    assert credentials["access_token"] == "token"


def test_secrets_are_redacted_from_logs_and_messages():
    secret = "very-sensitive-value"
    message = f"authentication failed for {secret}"
    assert secret not in redact_secrets(message, {"password": secret})
    assert "[REDACTED]" in redact_secrets(message, {"password": secret})


def test_no_secret_values_in_recorded_log(caplog):
    secret = "log-secret-value"
    with caplog.at_level(logging.ERROR):
        logging.getLogger("xyfuss-test").error("Broker error: %s", redact_secrets(secret, {"password": secret}))
    assert secret not in caplog.text


def test_live_trading_requires_environment_approval(monkeypatch, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("trading_mode: live\nlive_trading_enabled: true\n", encoding="utf-8")
    monkeypatch.setenv("XYFUSS_LIVE_TRADING_ENABLED", "true")
    monkeypatch.delenv("XYFUSS_LIVE_TRADING_APPROVAL", raising=False)
    settings = load_settings(str(config))
    assert settings.trading_mode == "paper"
    assert settings.live_trading_enabled is False


def test_demo_execution_requires_config_and_environment_opt_in(monkeypatch, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("demo_execution_enabled: true\\n", encoding="utf-8")
    monkeypatch.delenv("XYFUSS_LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("XYFUSS_LIVE_TRADING_APPROVAL", raising=False)
    monkeypatch.delenv("XYFUSS_DEMO_EXECUTION_ENABLED", raising=False)
    assert load_settings(str(config)).demo_execution_enabled is False
    monkeypatch.setenv("XYFUSS_DEMO_EXECUTION_ENABLED", "true")
    assert load_settings(str(config)).demo_execution_enabled is True


def test_demo_execution_is_blocked_when_live_mode_is_approved(monkeypatch, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("live_trading_enabled: true\\ndemo_execution_enabled: true\\n", encoding="utf-8")
    monkeypatch.setenv("XYFUSS_LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("XYFUSS_LIVE_TRADING_APPROVAL", "I_UNDERSTAND_LIVE_TRADING")
    monkeypatch.setenv("XYFUSS_DEMO_EXECUTION_ENABLED", "true")
    settings = load_settings(str(config))
    assert settings.live_trading_enabled is True
    assert settings.demo_execution_enabled is False


def test_explicit_live_trading_approval_is_required(monkeypatch, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("trading_mode: live\nlive_trading_enabled: true\n", encoding="utf-8")
    monkeypatch.setenv("XYFUSS_LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("XYFUSS_LIVE_TRADING_APPROVAL", "I_UNDERSTAND_LIVE_TRADING")
    settings = load_settings(str(config))
    assert settings.trading_mode == "live"
    assert settings.live_trading_enabled is True
