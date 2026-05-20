from decimal import Decimal

import streamlit as st

from bot.api_client import (
    BinanceAPIError,
    BinanceCredentialsError,
    BinanceFuturesTestnetClient,
)
from bot.validators import ValidationError, validate_order_inputs
from ui.streamlit_shared import (
    clear_account_caches,
    get_account,
    get_balances,
    get_client,
    get_exchange_info,
    get_symbol_price,
)
from ui.ui_helpers import (
    add_tracked_order,
    available_quote_assets,
    filter_symbols,
    format_balance_rows,
    format_position_rows,
    get_all_tracked_orders,
    newest_tracked_order,
    order_result_rows,
    remove_tracked_order,
    tracked_orders_rows,
    trading_symbols,
)


def decimal_to_api_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def default_symbol_index(symbol_options: list[str]) -> int:
    for preferred in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]:
        if preferred in symbol_options:
            return symbol_options.index(preferred)
    return 0


def safe_quantity_default(selected_symbol: str) -> str:
    if selected_symbol == "BTCUSDT":
        return "0.001"
    if selected_symbol == "ETHUSDT":
        return "0.01"
    return "1"


def display_amount(value: object, suffix: str = "") -> str:
    try:
        decimal_value = Decimal(str(value))
        text = format(decimal_value.quantize(Decimal("0.01")), "f")
    except Exception:
        text = str(value)
    return f"{text}{suffix}"


st.set_page_config(
    page_title="Binance Futures Testnet Bot",
    page_icon="B",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 1180px; }
    div[data-testid="stMetric"] {
        background: rgba(38, 39, 48, 0.55);
        border: 1px solid rgba(250, 250, 250, 0.08);
        border-radius: 8px;
        padding: 0.85rem 1rem;
    }
    div[data-testid="stAlert"] { border-radius: 8px; }
    .trade-badge {
        display: inline-flex;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        background: rgba(46, 160, 67, 0.16);
        color: #9be9a8;
        border: 1px solid rgba(46, 160, 67, 0.35);
        font-size: 0.84rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }
    .step-label {
        color: #a8b3cf;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin: 0.5rem 0 0.25rem;
    }
    .preview-line {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.35rem 0;
        border-bottom: 1px solid rgba(250, 250, 250, 0.08);
    }
    .preview-line:last-child { border-bottom: 0; }
    .muted-note { color: #a8b3cf; font-size: 0.92rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def order_result_block(response: dict, heading: str) -> None:
    st.subheader(heading)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Order ID", str(response.get("orderId", "N/A")))
    col2.metric("Status", str(response.get("status", "N/A")))
    col3.metric("Executed Qty", str(response.get("executedQty", "N/A")))
    col4.metric("Average Price", str(response.get("avgPrice", "N/A")))
    rows = order_result_rows(response)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)


def show_tracked_order_section(client: BinanceFuturesTestnetClient) -> None:
    tracked_order = newest_tracked_order()
    if not tracked_order:
        return

    st.markdown("### Track last order")
    st.caption(
        f"Watching order `{tracked_order['order_id']}` for `{tracked_order['symbol']}`."
    )

    action_col1, action_col2 = st.columns([1, 1])
    refresh_clicked = action_col1.button("Refresh last order status", use_container_width=True)
    clear_clicked = action_col2.button("Clear tracked order", use_container_width=True)

    if clear_clicked:
        remove_tracked_order(str(tracked_order["order_id"]), str(tracked_order["symbol"]))
        st.info("Tracked order cleared.")
        return

    if refresh_clicked:
        try:
            latest_status = client.get_order(
                tracked_order["symbol"],
                int(tracked_order["order_id"]),
            )
            add_tracked_order(
                {
                    "symbol": tracked_order["symbol"],
                    "order_id": str(tracked_order["order_id"]),
                    "latest_status": latest_status,
                    "status": str(latest_status.get("status", "")),
                }
            )
        except BinanceAPIError as exc:
            st.error(f"Binance API error while refreshing order: {exc}")
        except ConnectionError as exc:
            st.error(f"Network error while refreshing order: {exc}")
        except Exception as exc:
            st.error(f"Unexpected refresh error: {exc}")

    latest_status = newest_tracked_order().get("latest_status") if newest_tracked_order() else None
    if latest_status:
        order_result_block(latest_status, "Tracked order status")
        status = str(latest_status.get("status", "")).upper()
        if status == "FILLED":
            st.success("Limit condition has been met and the order is filled.")
        elif status in {"NEW", "PARTIALLY_FILLED"}:
            st.info("Order is still active. Refresh again to check for fills.")
        elif status in {"CANCELED", "EXPIRED", "REJECTED"}:
            st.warning(f"Order is no longer active: {status}.")


def main() -> None:
    st.markdown('<div class="trade-badge">Testnet only</div>', unsafe_allow_html=True)
    st.title("Place a Futures Test Order")
    st.caption(
        "A guided Binance Futures Testnet trade ticket for MARKET and LIMIT orders."
    )

    try:
        client = get_client()
        exchange_info = get_exchange_info()
        symbols = trading_symbols(exchange_info)
        quote_assets = available_quote_assets(symbols)
        balances = get_balances()
        account = get_account()
    except BinanceCredentialsError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unable to load Binance testnet data: {exc}")
        st.stop()

    position_rows = format_position_rows(account.get("positions", []))
    open_position_symbols = [row["Symbol"] for row in position_rows]

    summary_col1, summary_col2, summary_col3 = st.columns(3)
    summary_col1.metric(
        "Wallet Balance",
        display_amount(account.get("totalWalletBalance", "N/A"), " USDT"),
    )
    summary_col2.metric(
        "Available Balance",
        display_amount(account.get("availableBalance", "N/A"), " USDT"),
    )
    summary_col3.metric(
        "Unrealized PnL",
        display_amount(account.get("totalUnrealizedProfit", "N/A"), " USDT"),
    )

    st.divider()
    st.markdown("### Trade Ticket")
    st.markdown(
        '<p class="muted-note">Start with BTCUSDT and a tiny quantity. Everything here uses testnet funds.</p>',
        unsafe_allow_html=True,
    )

    form_left, form_right = st.columns([1.05, 0.95])

    with form_left:
        st.markdown('<div class="step-label">Step 1: Market</div>', unsafe_allow_html=True)
        quote_asset = st.selectbox(
            "Market group",
            options=quote_assets,
            index=quote_assets.index("USDT") if "USDT" in quote_assets else 0,
            help="USDT markets are the simplest starting point for this testnet task.",
        )
        search_text = st.text_input(
            "Search market",
            placeholder="BTC, ETH, SOL...",
            help="Leave blank to start with common USDT pairs.",
        )
        matching_symbols = filter_symbols(symbols, quote_asset, search_text)

        if not matching_symbols:
            st.warning("No markets match that search. Clear it to return to BTCUSDT.")
            show_tracked_order_section(client)
            tracked_rows = tracked_orders_rows(get_all_tracked_orders())
            if tracked_rows:
                st.markdown("### Recent tracked orders")
                st.dataframe(tracked_rows, use_container_width=True, hide_index=True)
            return

        selected_symbol = st.selectbox(
            "Market",
            options=[item["symbol"] for item in matching_symbols],
            index=default_symbol_index([item["symbol"] for item in matching_symbols]),
            help="BTCUSDT is selected by default because it is familiar and liquid.",
        )

        selected_symbol_info = next(
            item for item in matching_symbols if item["symbol"] == selected_symbol
        )
        ticker_data = get_symbol_price(selected_symbol)
        current_price = ticker_data.get("price", "N/A")

        st.markdown('<div class="step-label">Step 2: Action</div>', unsafe_allow_html=True)
        side = st.radio(
            "Direction",
            options=["BUY", "SELL"],
            horizontal=True,
            help="BUY increases a long position. SELL can reduce a long position or open a short.",
        )
        order_type = st.radio(
            "Execution",
            options=["MARKET", "LIMIT"],
            horizontal=True,
            help="MARKET executes now. LIMIT waits for your chosen price.",
        )

        st.markdown('<div class="step-label">Step 3: Size</div>', unsafe_allow_html=True)
        quantity = st.text_input(
            "Quantity",
            value=safe_quantity_default(selected_symbol),
            help="Use a tiny amount for testing. Binance step-size rules are checked before submit.",
        )

    with form_right:
        st.markdown('<div class="step-label">Review</div>', unsafe_allow_html=True)
        info_col1, info_col2 = st.columns(2)
        info_col1.metric("Live Price", str(current_price))
        info_col2.markdown(
            f"""
            <div style="border: 1px solid rgba(250,250,250,0.08); border-radius: 8px; padding: 0.85rem 1rem; background: rgba(38,39,48,0.55); min-height: 104px;">
                <div style="font-size: 0.88rem; color: #c9d1d9; margin-bottom: 0.6rem;">Market</div>
                <div style="font-size: 1.6rem; font-weight: 700; line-height: 1.2;">{selected_symbol}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        price_value = ""
        if order_type == "LIMIT":
            price_value = st.text_input(
                "Limit price",
                value=str(current_price),
                help="The order waits until this price or better is available.",
            )
        else:
            st.text_input(
                "Limit price",
                value="Not needed for MARKET",
                disabled=True,
            )

        with st.container(border=True):
            st.markdown("#### Order preview")
            st.markdown(
                f"""
                <div class="preview-line"><span>Market</span><strong>{selected_symbol}</strong></div>
                <div class="preview-line"><span>Direction</span><strong>{side}</strong></div>
                <div class="preview-line"><span>Order type</span><strong>{order_type}</strong></div>
                <div class="preview-line"><span>Quantity</span><strong>{quantity}</strong></div>
                """,
                unsafe_allow_html=True,
            )
            if order_type == "MARKET":
                st.caption("This test order submits immediately at the available testnet price.")
            else:
                st.caption("This test order waits until the limit price can be matched.")

    if side == "SELL":
        st.markdown("### Sell-side position guide")
        if position_rows:
            st.caption(
                "These are your current open or non-zero futures positions. Use them as a guide before placing a sell order."
            )
            st.dataframe(position_rows, use_container_width=True, hide_index=True)
            if selected_symbol in open_position_symbols:
                st.info(
                    f"You currently have an open position in {selected_symbol}, so this sell order can be used to reduce or close it."
                )
            else:
                st.warning(
                    f"You do not currently have an open position in {selected_symbol}. On futures, a sell order here may open or increase a short position instead of closing an existing one."
                )
        else:
            st.warning(
                "No open positions were found. A SELL order may open a new short position rather than selling an existing holding."
            )

    estimated_price = price_value if order_type == "LIMIT" else str(current_price)
    try:
        estimated_notional = Decimal(str(quantity)) * Decimal(str(estimated_price))
        st.info(f"Estimated test order value: {estimated_notional.normalize()} USDT")
    except Exception:
        st.caption("Estimated order value will appear after valid quantity and price input.")

    confirm = st.checkbox("I understand this will place a Binance Futures Testnet order.")
    submitted = st.button(
        "Place testnet order",
        type="primary",
        use_container_width=True,
        disabled=not confirm,
    )

    if submitted:
        try:
            validated = validate_order_inputs(
                symbol=selected_symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price_value if order_type == "LIMIT" else None,
                symbol_info=selected_symbol_info,
                reference_price=current_price,
            )

            with st.spinner("Placing order on Binance Futures Testnet..."):
                response = client.place_order(
                    symbol=validated.symbol,
                    side=validated.side,
                    order_type=validated.order_type,
                    quantity=decimal_to_api_text(validated.quantity),
                    price=decimal_to_api_text(validated.price) if validated.price else None,
                )
                latest_status = {}
                order_id = response.get("orderId")
                if order_id:
                    try:
                        latest_status = client.get_order(validated.symbol, int(order_id))
                    except (BinanceAPIError, ConnectionError) as exc:
                        st.warning(
                            "Order was submitted, but the latest status lookup failed. "
                            f"Use Order Tracking to refresh it later. Details: {exc}"
                        )

            st.success("Order submitted successfully.")
            clear_account_caches()
            order_result_block(response, "Immediate response")
            status_payload = latest_status or response
            if latest_status:
                order_result_block(latest_status, "Latest order status")
            if order_id:
                add_tracked_order(
                    {
                        "symbol": validated.symbol,
                        "order_id": str(order_id),
                        "latest_status": status_payload,
                        "status": str(status_payload.get("status", "")),
                    }
                )

            with st.expander("Order summary"):
                st.json(
                    {
                        "symbol": validated.symbol,
                        "side": validated.side,
                        "order_type": validated.order_type,
                        "quantity": str(validated.quantity),
                        "price": str(validated.price) if validated.price else None,
                    }
                )

        except ValidationError as exc:
            st.error(f"Validation error: {exc}")
        except BinanceAPIError as exc:
            st.error(f"Binance API error: {exc}")
        except ConnectionError as exc:
            st.error(f"Network error: {exc}")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

    show_tracked_order_section(client)
    tracked_rows = tracked_orders_rows(get_all_tracked_orders())
    if tracked_rows:
        st.markdown("### Recent tracked orders")
        st.dataframe(tracked_rows, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
