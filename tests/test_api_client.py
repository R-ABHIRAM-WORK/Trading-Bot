import logging

import pytest
import requests

from bot.api_client import BinanceAPIError, BinanceFuturesTestnetClient


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.headers = {}
        self.last_request = None

    def request(self, **kwargs):
        self.last_request = kwargs
        return self.response


class RaisingSession:
    def __init__(self) -> None:
        self.headers = {}

    def request(self, **kwargs):
        raise requests.RequestException(
            "failed url https://example.test?signature=SECRET_SIG&timestamp=123"
        )


def make_client(response: FakeResponse) -> BinanceFuturesTestnetClient:
    client = BinanceFuturesTestnetClient(
        api_key="test-api-key",
        secret_key="test-secret-key",
        logger=logging.getLogger("test-client"),
    )
    client.session = FakeSession(response)
    return client


def test_place_order_sends_decimal_strings() -> None:
    client = make_client(FakeResponse(200, {"orderId": 1, "status": "FILLED"}))

    result = client.place_order(
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity="0.001",
        price="100000.10",
    )

    assert result["orderId"] == 1
    params = client.session.last_request["params"]
    assert params["quantity"] == "0.001"
    assert params["price"] == "100000.10"
    assert "signature" in params


def test_api_error_includes_status_and_endpoint() -> None:
    client = make_client(FakeResponse(400, {"code": -2019, "msg": "Margin is insufficient."}))

    with pytest.raises(BinanceAPIError, match="HTTP 400, /fapi/v1/order"):
        client.place_order("BTCUSDT", "BUY", "MARKET", "0.001")


def test_non_json_error_includes_status_and_body_preview() -> None:
    client = make_client(FakeResponse(502, ValueError("no json"), "Bad gateway"))

    with pytest.raises(BinanceAPIError, match="status 502"):
        client.get_exchange_info()


def test_network_error_message_does_not_leak_signature() -> None:
    client = BinanceFuturesTestnetClient(
        api_key="test-api-key",
        secret_key="test-secret-key",
        logger=logging.getLogger("test-client-network"),
    )
    client.session = RaisingSession()

    with pytest.raises(ConnectionError) as exc_info:
        client.place_order("BTCUSDT", "BUY", "MARKET", "0.001")

    assert "SECRET_SIG" not in str(exc_info.value)
    assert "signature=" not in str(exc_info.value)


def test_safe_params_redacts_timestamp_and_signature() -> None:
    client = make_client(FakeResponse(200, {}))

    safe = client._safe_params(
        {"symbol": "BTCUSDT", "timestamp": 123456, "signature": "SECRET"}
    )

    assert safe == {"symbol": "BTCUSDT", "timestamp": "<redacted>"}


def test_account_response_logging_is_summarized() -> None:
    client = make_client(FakeResponse(200, {}))

    safe = client._safe_response(
        "/fapi/v2/account",
        {
            "assets": [{"asset": "USDT"}],
            "positions": [{"symbol": "BTCUSDT"}],
            "canTrade": True,
            "totalWalletBalance": "999999",
        },
    )

    assert safe == {"assets_count": 1, "positions_count": 1, "canTrade": True}
    assert "totalWalletBalance" not in safe


def test_get_balance_returns_empty_list_for_unexpected_payload() -> None:
    client = make_client(FakeResponse(200, {"unexpected": "shape"}))

    assert client.get_balance() == []
