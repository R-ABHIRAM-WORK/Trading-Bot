import streamlit as st

from bot.api_client import BinanceCredentialsError
from ui.streamlit_shared import get_account, get_balances, get_client
from ui.ui_helpers import format_balance_rows, format_money_text, format_position_rows


st.set_page_config(page_title="Wallet and Positions", page_icon="B", layout="wide")


def main() -> None:
    st.title("Wallet and Positions")
    st.caption("View your Binance Futures Testnet balances, buying power, and open positions.")
    st.info("This page reflects the same Binance testnet account used by the trading page, including manual account activity.")

    try:
        client = get_client()
        balances = get_balances()
        account = get_account()
    except BinanceCredentialsError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unable to load account data: {exc}")
        st.stop()

    assets = format_balance_rows(balances)
    positions = format_position_rows(account.get("positions", []))

    summary_col1, summary_col2, summary_col3 = st.columns(3)
    summary_col1.metric(
        "Total Wallet Balance",
        f"{format_money_text(account.get('totalWalletBalance', 'N/A'))} USDT",
    )
    summary_col2.metric(
        "Available Balance",
        f"{format_money_text(account.get('availableBalance', 'N/A'))} USDT",
    )
    summary_col3.metric(
        "Total Unrealized PnL",
        f"{format_money_text(account.get('totalUnrealizedProfit', 'N/A'))} USDT",
    )

    st.markdown("### Asset balances")
    if assets:
        st.dataframe(assets, use_container_width=True, hide_index=True)
    else:
        st.info("No non-zero balances found.")

    st.markdown("### Open and non-zero positions")
    if positions:
        st.dataframe(positions, use_container_width=True, hide_index=True)
    else:
        st.info("No open positions found.")

    with st.expander("Raw account snapshot"):
        st.json(
            {
                "feeTier": account.get("feeTier"),
                "canTrade": account.get("canTrade"),
                "canDeposit": account.get("canDeposit"),
                "canWithdraw": account.get("canWithdraw"),
                "assets_count": len(account.get("assets", [])),
                "positions_count": len(account.get("positions", [])),
            }
        )


if __name__ == "__main__":
    main()
