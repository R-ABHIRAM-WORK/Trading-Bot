from ui.ui_helpers import (
    available_quote_assets,
    filter_symbols,
    format_balance_rows,
    format_binance_time,
    format_decimal_text,
    format_money_text,
    trading_symbols,
)


def test_trading_symbols_filters_to_active_symbols() -> None:
    exchange_info = {
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING"},
            {"symbol": "OLDUSDT", "status": "BREAK"},
        ]
    }

    assert trading_symbols(exchange_info) == [{"symbol": "BTCUSDT", "status": "TRADING"}]


def test_filter_symbols_by_quote_and_search_text() -> None:
    symbols = [
        {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT"},
        {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT"},
        {"symbol": "BTCEUR", "baseAsset": "BTC", "quoteAsset": "EUR"},
    ]

    result = filter_symbols(symbols, "USDT", "btc")

    assert [item["symbol"] for item in result] == ["BTCUSDT"]


def test_available_quote_assets_are_sorted() -> None:
    symbols = [
        {"quoteAsset": "USDT"},
        {"quoteAsset": "EUR"},
        {"quoteAsset": "USDT"},
    ]

    assert available_quote_assets(symbols) == ["EUR", "USDT"]


def test_format_helpers_are_readable() -> None:
    assert format_decimal_text("5000.000") == "5000"
    assert format_decimal_text("0.0100") == "0.01"
    assert format_money_text("5000.4445") == "5000.44"
    assert format_binance_time(1716200000000).endswith("UTC")
    assert format_binance_time("bad") == "bad"


def test_balance_rows_use_readable_amounts() -> None:
    rows = format_balance_rows(
        [
            {
                "asset": "USDT",
                "balance": "5000.44452265",
                "availableBalance": "4982.0655518",
            }
        ]
    )

    assert rows == [{"Asset": "USDT", "Balance": "5000.44", "Available": "4982.07"}]
