import argparse
import sys

import pytest

import cli


def test_log_file_only_still_allows_interactive_prompts(monkeypatch) -> None:
    answers = iter(["BTCUSDT", "BUY", "MARKET", "0.001"])
    monkeypatch.setattr(sys, "argv", ["cli.py", "--log-file", "logs/test.log"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    args = argparse.Namespace(
        symbol=None,
        side=None,
        order_type=None,
        quantity=None,
        price=None,
        log_file="logs/test.log",
    )

    assert cli.collect_inputs(args) == {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "0.001",
        "price": None,
    }


def test_cli_main_places_order_and_returns_success(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, logger=None) -> None:
            self.logger = logger

        def get_symbol_info(self, symbol: str) -> dict:
            return {
                "symbol": symbol,
                "status": "TRADING",
                "filters": [
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.001",
                        "maxQty": "100",
                        "stepSize": "0.001",
                    },
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "1",
                        "maxPrice": "1000000",
                        "tickSize": "0.10",
                    },
                    {"filterType": "MIN_NOTIONAL", "notional": "5"},
                ],
            }

        def get_ticker_price(self, symbol: str) -> dict:
            return {"price": "100000"}

        def place_order(self, **kwargs) -> dict:
            assert kwargs["quantity"] == "0.001"
            return {
                "orderId": 123,
                "status": "FILLED",
                "executedQty": "0.001",
                "avgPrice": "100000",
            }

        def get_order(self, symbol: str, order_id: int) -> dict:
            return {
                "orderId": order_id,
                "status": "FILLED",
                "executedQty": "0.001",
                "avgPrice": "100000",
            }

    monkeypatch.setattr(cli, "BinanceFuturesTestnetClient", FakeClient)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--type",
            "MARKET",
            "--quantity",
            "0.001",
        ],
    )

    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Order Request Summary" in output
    assert "Success: order placed" in output


def test_cli_status_lookup_failure_is_warning_not_failure(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, logger=None) -> None:
            self.logger = logger

        def get_symbol_info(self, symbol: str) -> dict:
            return {
                "symbol": symbol,
                "status": "TRADING",
                "filters": [
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.001",
                        "maxQty": "100",
                        "stepSize": "0.001",
                    },
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "1",
                        "maxPrice": "1000000",
                        "tickSize": "0.10",
                    },
                    {"filterType": "MIN_NOTIONAL", "notional": "5"},
                ],
            }

        def get_ticker_price(self, symbol: str) -> dict:
            return {"price": "100000"}

        def place_order(self, **kwargs) -> dict:
            return {"orderId": 456, "status": "FILLED", "executedQty": "0.001"}

        def get_order(self, symbol: str, order_id: int) -> dict:
            raise cli.BinanceAPIError("Order does not exist")

    monkeypatch.setattr(cli, "BinanceFuturesTestnetClient", FakeClient)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--type",
            "MARKET",
            "--quantity",
            "0.001",
        ],
    )

    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Warning: order placed" in output
    assert "Success: order placed" in output


def test_cli_basic_validation_happens_before_client_creation(monkeypatch) -> None:
    def fail_if_created(logger=None):
        raise AssertionError("client should not be created for invalid local input")

    monkeypatch.setattr(cli, "BinanceFuturesTestnetClient", fail_if_created)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "--symbol",
            "BTCUSDT",
            "--side",
            "HOLD",
            "--type",
            "MARKET",
            "--quantity",
            "0.001",
        ],
    )

    assert cli.main() == 1
