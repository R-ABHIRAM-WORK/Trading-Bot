from typing import Any, Dict, List

import streamlit as st

from bot.api_client import BinanceFuturesTestnetClient
from bot.logging_config import setup_logging


@st.cache_resource
def get_client() -> BinanceFuturesTestnetClient:
    logger = setup_logging("trading_bot.log")
    return BinanceFuturesTestnetClient(logger=logger)


@st.cache_data(ttl=60)
def get_exchange_info() -> Dict[str, Any]:
    return get_client().get_exchange_info()


@st.cache_data(ttl=10)
def get_symbol_price(symbol: str) -> Dict[str, Any]:
    return get_client().get_ticker_price(symbol)


@st.cache_data(ttl=30)
def get_balances() -> List[Dict[str, Any]]:
    return get_client().get_balance()


@st.cache_data(ttl=30)
def get_account() -> Dict[str, Any]:
    return get_client().get_account()


def clear_account_caches() -> None:
    get_balances.clear()
    get_account.clear()
    get_symbol_price.clear()
