import argparse
import sys
from decimal import Decimal
from typing import Optional

from bot.api_client import (
    BinanceAPIError,
    BinanceCredentialsError,
    BinanceFuturesTestnetClient,
)
from bot.logging_config import setup_logging
from bot.validators import (
    ValidationError,
    normalize_order_type,
    normalize_side,
    normalize_symbol,
    parse_positive_decimal,
    validate_order_inputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place Binance Futures Testnet MARKET or LIMIT orders."
    )
    parser.add_argument("--symbol", help="Trading symbol, for example BTCUSDT")
    parser.add_argument("--side", help="Order side: BUY or SELL")
    parser.add_argument("--type", dest="order_type", help="Order type: MARKET or LIMIT")
    parser.add_argument("--quantity", help="Order quantity, for example 0.01")
    parser.add_argument("--price", help="Order price, required for LIMIT orders")
    parser.add_argument(
        "--log-file",
        default="trading_bot.log",
        help="Path to the log file",
    )
    return parser


def prompt_if_missing(value: Optional[str], prompt_text: str, allow_prompt: bool) -> str:
    if value is not None and str(value).strip():
        return str(value).strip()
    if not allow_prompt:
        return ""
    return input(prompt_text).strip()


def collect_inputs(args: argparse.Namespace) -> dict[str, Optional[str]]:
    allow_prompt = not any(
        [args.symbol, args.side, args.order_type, args.quantity, args.price]
    )
    symbol = prompt_if_missing(args.symbol, "Enter symbol (e.g. BTCUSDT): ", allow_prompt)
    side = prompt_if_missing(args.side, "Enter side (BUY/SELL): ", allow_prompt)
    order_type = prompt_if_missing(args.order_type, "Enter order type (MARKET/LIMIT): ", allow_prompt)
    quantity = prompt_if_missing(args.quantity, "Enter quantity: ", allow_prompt)

    price = args.price
    if order_type.strip().upper() == "LIMIT":
        price = prompt_if_missing(args.price, "Enter limit price: ", allow_prompt)

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }


def format_decimal(value: Optional[Decimal]) -> str:
    if value is None:
        return "N/A"
    return format(value.normalize(), "f")


def decimal_to_api_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def validate_basic_inputs(raw_inputs: dict[str, Optional[str]]) -> None:
    normalize_symbol(raw_inputs["symbol"] or "")
    normalize_side(raw_inputs["side"] or "")
    order_type = normalize_order_type(raw_inputs["order_type"] or "")
    parse_positive_decimal(raw_inputs["quantity"], "Quantity")
    if order_type == "LIMIT":
        if raw_inputs["price"] is None or str(raw_inputs["price"]).strip() == "":
            raise ValidationError("Price is required for LIMIT orders.")
        parse_positive_decimal(raw_inputs["price"], "Price")


def print_order_summary(symbol: str, side: str, order_type: str, quantity: Decimal, price: Optional[Decimal]) -> None:
    print("Order Request Summary")
    print(f"Symbol: {symbol}")
    print(f"Side: {side}")
    print(f"Order Type: {order_type}")
    print(f"Quantity: {format_decimal(quantity)}")
    if order_type == "LIMIT":
        print(f"Price: {format_decimal(price)}")


def print_order_response(response: dict) -> None:
    print("Order Response Details")
    print(f"Order ID: {response.get('orderId', 'N/A')}")
    print(f"Status: {response.get('status', 'N/A')}")
    print(f"Executed Quantity: {response.get('executedQty', 'N/A')}")
    print(f"Average Price: {response.get('avgPrice', 'N/A')}")


def print_order_status(status_response: dict) -> None:
    print("Latest Order Status")
    print(f"Order ID: {status_response.get('orderId', 'N/A')}")
    print(f"Status: {status_response.get('status', 'N/A')}")
    print(f"Executed Quantity: {status_response.get('executedQty', 'N/A')}")
    print(f"Average Price: {status_response.get('avgPrice', 'N/A')}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(args.log_file)

    try:
        raw_inputs = collect_inputs(args)
        validate_basic_inputs(raw_inputs)
        client = BinanceFuturesTestnetClient(logger=logger)
        symbol_info = client.get_symbol_info(raw_inputs["symbol"])
        ticker_price = None
        if symbol_info:
            ticker_price = client.get_ticker_price(raw_inputs["symbol"]).get("price")
        validated_order = validate_order_inputs(
            symbol=raw_inputs["symbol"],
            side=raw_inputs["side"],
            order_type=raw_inputs["order_type"],
            quantity=raw_inputs["quantity"],
            price=raw_inputs["price"],
            symbol_info=symbol_info,
            reference_price=ticker_price,
        )

        print_order_summary(
            validated_order.symbol,
            validated_order.side,
            validated_order.order_type,
            validated_order.quantity,
            validated_order.price,
        )

        logger.info(
            "Validated order request",
            extra={
                "event": "validated_order",
                "symbol": validated_order.symbol,
                "side": validated_order.side,
                "order_type": validated_order.order_type,
                "quantity": decimal_to_api_text(validated_order.quantity),
                "price": decimal_to_api_text(validated_order.price) if validated_order.price else None,
            },
        )

        response = client.place_order(
            symbol=validated_order.symbol,
            side=validated_order.side,
            order_type=validated_order.order_type,
            quantity=decimal_to_api_text(validated_order.quantity),
            price=decimal_to_api_text(validated_order.price) if validated_order.price else None,
        )

        print_order_response(response)
        order_id = response.get("orderId")
        if order_id:
            try:
                latest_status = client.get_order(validated_order.symbol, int(order_id))
                print_order_status(latest_status)
            except (BinanceAPIError, ConnectionError) as exc:
                logger.warning(
                    "Order placed but latest status lookup failed: %s",
                    exc,
                    extra={
                        "event": "status_lookup_failed",
                        "symbol": validated_order.symbol,
                        "order_id": order_id,
                    },
                )
                print(f"Warning: order placed, but latest status lookup failed: {exc}")
        print()
        print("Success: order placed on Binance Futures Testnet.")
        print("Warning: testnet only. Review risk before placing any order.")
        return 0

    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"Error: {exc}")
        return 1
    except BinanceCredentialsError as exc:
        logger.error("Credentials error: %s", exc)
        print(f"Error: {exc}")
        return 1
    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        print(f"Error: {exc}")
        return 1
    except ConnectionError as exc:
        logger.error("Connection error: %s", exc)
        print(f"Error: {exc}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        print("\nCancelled by user.")
        return 130
    except Exception as exc:
        logger.exception("Unexpected error")
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
