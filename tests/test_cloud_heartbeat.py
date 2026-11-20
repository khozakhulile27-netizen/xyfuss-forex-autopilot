import json
from unittest.mock import MagicMock, patch

import pytest

from xyfuss_forex_autopilot.cloud_heartbeat import CloudHeartbeat


TOKEN = "test-token-that-is-long-enough-for-unit-tests-123456"


def test_sends_only_paper_mode_presence_metadata():
    heartbeat = CloudHeartbeat("http://127.0.0.1:8080", TOKEN)
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps({
        "accepted": True,
        "agent": {
            "agent_id": "xyfuss-forex-autopilot",
            "mode": "paper",
        },
    }).encode()
    response.__enter__.return_value = response

    with patch(
        "xyfuss_forex_autopilot.cloud_heartbeat.urlopen",
        return_value=response,
    ) as opener:
        assert heartbeat.send_once() is True

    request = opener.call_args.args[0]
    assert json.loads(request.data.decode()) == {
        "agent_id": "xyfuss-forex-autopilot",
        "version": "0.1.0",
        "mode": "paper",
    }
    assert heartbeat.status == "online"


def test_rejects_plain_http_for_non_loopback_cloud():
    with pytest.raises(ValueError, match="HTTPS"):
        CloudHeartbeat("http://example.com:8080", TOKEN)


def test_rejects_short_token():
    with pytest.raises(ValueError, match="32 characters"):
        CloudHeartbeat("http://127.0.0.1:8080", "short")


def test_cloud_heartbeat_is_optional_when_not_configured(monkeypatch):
    monkeypatch.delenv("XYFUSS_CLOUD_URL", raising=False)
    monkeypatch.delenv("XYFUSS_CLOUD_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("XYFUSS_CLOUD_AGENT_TOKEN_FILE", raising=False)
    assert CloudHeartbeat.from_environment() is None
