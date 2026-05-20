from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


class ValidationError(Exception):
    """Raised when user input fails validation."""


@dataclass
class ValidatedOrder:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None


def normalize_symbol(symbol: str) -> str:
    cleaned = (symbol or "").strip().upper()
    if not cleaned:
        raise ValidationError("Symbol is required.")
    return cleaned


def normalize_side(side: str) -> str:
    cleaned = (side or "").strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValidationError("Side must be BUY or SELL.")
    return cleaned


def normalize_order_type(order_type: str) -> str:
    cleaned = (order_type or "").strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError("Order type must be MARKET or LIMIT.")
    return cleaned


def parse_positive_decimal(value: Any, field_name: str) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc

    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be a finite number.")

    if decimal_value <= 0:
        raise ValidationError(f"{field_name} must be greater than 0.")

    return decimal_value


def _extract_filter(symbol_info: Dict[str, Any], filter_type: str) -> Optional[Dict[str, Any]]:
    for item in symbol_info.get("filters", []):
        if item.get("filterType") == filter_type:
            return item
    return None


def _is_step_aligned(value: Decimal, step: Decimal) -> bool:
    if step == 0:
        return True
    return (value % step) == 0


def validate_symbol_exists(symbol: str, symbol_info: Optional[Dict[str, Any]]) -> None:
    if not symbol_info:
        raise ValidationError(f"Symbol '{symbol}' does not exist on Binance Futures Testnet.")
    if symbol_info.get("status") != "TRADING":
        raise ValidationError(f"Symbol '{symbol}' is not currently trading on Binance Futures Testnet.")


def validate_quantity_rules(
    quantity: Decimal,
    symbol_info: Dict[str, Any],
    order_type: str = "LIMIT",
) -> None:
    lot_size = None
    if order_type == "MARKET":
        lot_size = _extract_filter(symbol_info, "MARKET_LOT_SIZE")
    if not lot_size:
        lot_size = _extract_filter(symbol_info, "LOT_SIZE")
    if not lot_size:
        return

    min_qty = Decimal(lot_size["minQty"])
    max_qty = Decimal(lot_size["maxQty"])
    step_size = Decimal(lot_size["stepSize"])

    if quantity < min_qty:
        raise ValidationError(f"Quantity must be at least {min_qty}.")
    if quantity > max_qty:
        raise ValidationError(f"Quantity must be at most {max_qty}.")
    if not _is_step_aligned(quantity, step_size):
        raise ValidationError(f"Quantity must follow step size {step_size}.")


def validate_price_rules(price: Decimal, symbol_info: Dict[str, Any]) -> None:
    price_filter = _extract_filter(symbol_info, "PRICE_FILTER")
    if not price_filter:
        return

    min_price = Decimal(price_filter["minPrice"])
    max_price = Decimal(price_filter["maxPrice"])
    tick_size = Decimal(price_filter["tickSize"])

    if price < min_price:
        raise ValidationError(f"Price must be at least {min_price}.")
    if max_price != 0 and price > max_price:
        raise ValidationError(f"Price must be at most {max_price}.")
    if not _is_step_aligned(price, tick_size):
        raise ValidationError(f"Price must follow tick size {tick_size}.")


def validate_percent_price_rules(
    price: Decimal,
    reference_price: Optional[Decimal],
    symbol_info: Dict[str, Any],
) -> None:
    percent_filter = _extract_filter(symbol_info, "PERCENT_PRICE")
    if not percent_filter or reference_price is None:
        return

    multiplier_up = Decimal(percent_filter["multiplierUp"])
    multiplier_down = Decimal(percent_filter["multiplierDown"])
    max_price = reference_price * multiplier_up
    min_price = reference_price * multiplier_down

    if price > max_price:
        raise ValidationError(
            f"Price must be at most {max_price.normalize()} based on current market price."
        )
    if price < min_price:
        raise ValidationError(
            f"Price must be at least {min_price.normalize()} based on current market price."
        )


def validate_notional_rules(
    quantity: Decimal,
    reference_price: Optional[Decimal],
    symbol_info: Dict[str, Any],
) -> None:
    min_notional_filter = _extract_filter(symbol_info, "MIN_NOTIONAL")
    if not min_notional_filter or reference_price is None:
        return

    min_notional = Decimal(min_notional_filter["notional"])
    order_notional = quantity * reference_price
    if order_notional < min_notional:
        raise ValidationError(
            f"Order notional must be at least {min_notional}. "
            f"Current estimate is {order_notional.normalize()}."
        )


def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Any = None,
    symbol_info: Optional[Dict[str, Any]] = None,
    reference_price: Any = None,
) -> ValidatedOrder:
    normalized_symbol = normalize_symbol(symbol)
    normalized_side = normalize_side(side)
    normalized_order_type = normalize_order_type(order_type)
    normalized_quantity = parse_positive_decimal(quantity, "Quantity")

    validate_symbol_exists(normalized_symbol, symbol_info)
    validate_quantity_rules(normalized_quantity, symbol_info, normalized_order_type)

    normalized_price: Optional[Decimal] = None
    if normalized_order_type == "LIMIT":
        if price is None or str(price).strip() == "":
            raise ValidationError("Price is required for LIMIT orders.")
        normalized_price = parse_positive_decimal(price, "Price")
        validate_price_rules(normalized_price, symbol_info)
        percent_reference_price = None
        if reference_price is not None and str(reference_price).strip() != "":
            percent_reference_price = parse_positive_decimal(reference_price, "Reference price")
        validate_percent_price_rules(normalized_price, percent_reference_price, symbol_info)

    effective_reference_price: Optional[Decimal] = None
    if normalized_order_type == "LIMIT":
        effective_reference_price = normalized_price
    elif reference_price is not None and str(reference_price).strip() != "":
        effective_reference_price = parse_positive_decimal(reference_price, "Reference price")

    validate_notional_rules(normalized_quantity, effective_reference_price, symbol_info)

    return ValidatedOrder(
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_order_type,
        quantity=normalized_quantity,
        price=normalized_price,
    )
