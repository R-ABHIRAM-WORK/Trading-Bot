from decimal import Decimal

import pytest

from bot.validators import ValidationError, parse_positive_decimal, validate_order_inputs


def symbol_info() -> dict:
    return {
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "filters": [
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.001",
                "maxQty": "100",
                "stepSize": "0.001",
            },
            {
                "filterType": "MARKET_LOT_SIZE",
                "minQty": "0.01",
                "maxQty": "50",
                "stepSize": "0.01",
            },
            {
                "filterType": "PRICE_FILTER",
                "minPrice": "1",
                "maxPrice": "1000000",
                "tickSize": "0.10",
            },
            {"filterType": "MIN_NOTIONAL", "notional": "5"},
            {
                "filterType": "PERCENT_PRICE",
                "multiplierUp": "1.0500",
                "multiplierDown": "0.9500",
                "multiplierDecimal": "4",
            },
        ],
    }


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_parse_positive_decimal_rejects_non_finite_values(value: str) -> None:
    with pytest.raises(ValidationError, match="finite"):
        parse_positive_decimal(value, "Quantity")


def test_limit_order_requires_price() -> None:
    with pytest.raises(ValidationError, match="Price is required"):
        validate_order_inputs(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity="0.001",
            price=None,
            symbol_info=symbol_info(),
        )


def test_market_order_uses_market_lot_size_when_available() -> None:
    with pytest.raises(ValidationError, match="at least 0.01"):
        validate_order_inputs(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity="0.001",
            symbol_info=symbol_info(),
            reference_price="10000",
        )


def test_valid_limit_order_returns_decimals() -> None:
    validated = validate_order_inputs(
        symbol="btcusdt",
        side="buy",
        order_type="limit",
        quantity="0.002",
        price="100000.10",
        symbol_info=symbol_info(),
        reference_price="100000",
    )

    assert validated.symbol == "BTCUSDT"
    assert validated.side == "BUY"
    assert validated.order_type == "LIMIT"
    assert validated.quantity == Decimal("0.002")
    assert validated.price == Decimal("100000.10")


def test_non_trading_symbol_is_rejected() -> None:
    info = symbol_info()
    info["status"] = "BREAK"

    with pytest.raises(ValidationError, match="not currently trading"):
        validate_order_inputs(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity="0.01",
            symbol_info=info,
            reference_price="10000",
        )


def test_limit_order_rejects_percent_price_band_violation() -> None:
    with pytest.raises(ValidationError, match="at most"):
        validate_order_inputs(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity="0.001",
            price="50000",
            symbol_info=symbol_info(),
            reference_price="10000",
        )
