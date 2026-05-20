from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from ui.order_store import clear_tracked_orders, delete_tracked_order, list_tracked_orders, upsert_tracked_order


def trading_symbols(exchange_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        symbol
        for symbol in exchange_info.get("symbols", [])
        if symbol.get("status") == "TRADING"
    ]


def available_quote_assets(symbols: List[Dict[str, Any]]) -> List[str]:
    quotes = {symbol.get("quoteAsset") for symbol in symbols if symbol.get("quoteAsset")}
    return sorted(quotes)


def filter_symbols(
    symbols: List[Dict[str, Any]], quote_asset: str, search_text: str
) -> List[Dict[str, Any]]:
    search = search_text.strip().upper()
    filtered = [symbol for symbol in symbols if symbol.get("quoteAsset") == quote_asset]
    if search:
        filtered = [
            symbol
            for symbol in filtered
            if search in symbol.get("symbol", "").upper()
            or search in symbol.get("baseAsset", "").upper()
        ]
    return sorted(filtered, key=lambda item: item.get("symbol", ""))


def format_decimal_text(value: Any) -> str:
    try:
        decimal_value = Decimal(str(value))
        normalized = format(decimal_value.normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized or "0"
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def format_money_text(value: Any) -> str:
    try:
        decimal_value = Decimal(str(value))
        return format(decimal_value.quantize(Decimal("0.01")), "f")
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def format_balance_rows(balances: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for balance in balances:
        amount = Decimal(balance.get("balance", "0"))
        available = Decimal(balance.get("availableBalance", "0"))
        if amount == 0 and available == 0:
            continue
        rows.append(
            {
                "Asset": balance.get("asset", ""),
                "Balance": format_money_text(amount),
                "Available": format_money_text(available),
            }
        )
    return rows


def order_result_rows(response: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = []
    for key in [
        "orderId",
        "symbol",
        "status",
        "side",
        "type",
        "origQty",
        "executedQty",
        "avgPrice",
        "price",
        "timeInForce",
        "updateTime",
    ]:
        if key in response:
            rows.append({"Field": key, "Value": format_decimal_text(response.get(key))})
    return rows


def format_position_rows(positions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for position in positions:
        position_amt = Decimal(position.get("positionAmt", "0"))
        entry_price = Decimal(position.get("entryPrice", "0"))
        unrealized_pnl = Decimal(position.get("unRealizedProfit", "0"))
        if position_amt == 0 and entry_price == 0 and unrealized_pnl == 0:
            continue
        rows.append(
            {
                "Symbol": position.get("symbol", ""),
                "Position Amt": format_decimal_text(position_amt),
                "Entry Price": format_decimal_text(entry_price),
                "Unrealized PnL": format_decimal_text(unrealized_pnl),
                "Leverage": str(position.get("leverage", "")),
                "Margin Type": str(position.get("marginType", "")),
            }
        )
    return rows


def tracked_orders_rows(tracked_orders: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in tracked_orders:
        latest_status = item.get("latest_status", {})
        rows.append(
            {
                "Order ID": str(item.get("order_id", "")),
                "Symbol": str(item.get("symbol", "")),
                "Side": str(latest_status.get("side", "")),
                "Type": str(latest_status.get("type", "")),
                "Status": str(latest_status.get("status", item.get("status", "UNKNOWN"))),
                "Executed Qty": format_decimal_text(latest_status.get("executedQty", "0")),
                "Average Price": format_decimal_text(latest_status.get("avgPrice", "0")),
                "Updated": format_binance_time(latest_status.get("updateTime", "")),
            }
        )
    return rows


def format_binance_time(value: Any) -> str:
    try:
        from datetime import datetime, timezone

        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except (TypeError, ValueError, OSError):
        return str(value or "")


def add_tracked_order(order_payload: Dict[str, Any]) -> None:
    upsert_tracked_order(
        order_id=str(order_payload.get("order_id", "")),
        symbol=str(order_payload.get("symbol", "")),
        status=str(order_payload.get("status", "")),
        latest_status=order_payload.get("latest_status", {}),
    )


def refresh_tracked_orders(client: Any) -> None:
    tracked_orders = list_tracked_orders()
    for item in tracked_orders:
        try:
            latest_status = client.get_order(item["symbol"], int(item["order_id"]))
            status = str(latest_status.get("status", item.get("status", "")))
        except (TypeError, ValueError) as exc:
            latest_status = {"status": "REFRESH_FAILED", "error": str(exc)}
            status = "REFRESH_FAILED"
        except Exception as exc:
            latest_status = {"status": "REFRESH_FAILED", "error": str(exc)}
            status = "REFRESH_FAILED"

        upsert_tracked_order(
            order_id=str(item["order_id"]),
            symbol=str(item["symbol"]),
            status=status,
            latest_status=latest_status,
        )


def newest_tracked_order() -> Optional[Dict[str, Any]]:
    tracked_orders = list_tracked_orders()
    return tracked_orders[0] if tracked_orders else None


def get_all_tracked_orders() -> List[Dict[str, Any]]:
    return list_tracked_orders()


def remove_tracked_order(order_id: str, symbol: Optional[str] = None) -> None:
    delete_tracked_order(order_id, symbol)


def remove_all_tracked_orders() -> None:
    clear_tracked_orders()
