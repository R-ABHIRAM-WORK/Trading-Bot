import streamlit as st

from bot.api_client import BinanceAPIError, BinanceCredentialsError
from ui.streamlit_shared import get_client
from ui.ui_helpers import (
    get_all_tracked_orders,
    order_result_rows,
    refresh_tracked_orders,
    remove_all_tracked_orders,
    tracked_orders_rows,
)


st.set_page_config(page_title="Order Tracking", page_icon="B", layout="wide")


def main() -> None:
    st.title("Order Tracking")
    st.caption("Review and refresh the orders placed from this app.")
    st.info("Use this page to see whether a limit order is still waiting, partially filled, or fully filled.")

    try:
        client = get_client()
    except BinanceCredentialsError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unable to initialize Binance client: {exc}")
        st.stop()

    tracked_orders = get_all_tracked_orders()
    if not tracked_orders:
        st.info("No tracked orders yet. Place an order from the main page first.")
        return

    action_col1, action_col2 = st.columns([1, 1])
    refresh_all = action_col1.button("Refresh all tracked orders", use_container_width=True)
    clear_all = action_col2.button("Clear tracked orders", use_container_width=True)

    if clear_all:
        remove_all_tracked_orders()
        st.success("Tracked orders cleared.")
        return

    if refresh_all:
        try:
            refresh_tracked_orders(client)
            tracked_orders = get_all_tracked_orders()
            st.success("Tracked orders refreshed.")
        except BinanceAPIError as exc:
            st.error(f"Binance API error while refreshing: {exc}")
        except ConnectionError as exc:
            st.error(f"Network error while refreshing: {exc}")
        except Exception as exc:
            st.error(f"Unexpected refresh error: {exc}")

    rows = tracked_orders_rows(get_all_tracked_orders())
    st.dataframe(rows, use_container_width=True, hide_index=True)

    order_options = [
        f"{item.get('symbol')} | {item.get('order_id')} | {item.get('status', 'UNKNOWN')}"
        for item in get_all_tracked_orders()
    ]
    selected_label = st.selectbox("Inspect a tracked order", options=order_options)
    selected_index = order_options.index(selected_label)
    selected_order = get_all_tracked_orders()[selected_index]
    latest_status = selected_order.get("latest_status", {})

    st.markdown("### Order details")
    detail_rows = order_result_rows(latest_status)
    if detail_rows:
        st.dataframe(detail_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No detailed status is available yet for this order.")


if __name__ == "__main__":
    main()
