import os
import time
import hmac
import hashlib
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv


class BinanceAPIError(Exception):
    """Raised when Binance returns an API-level error."""


class BinanceCredentialsError(Exception):
    """Raised when API credentials are missing."""


class BinanceFuturesTestnetClient:
    BASE_URL = "https://testnet.binancefuture.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        timeout: int = 15,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        load_dotenv()

        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.secret_key = secret_key or os.getenv("BINANCE_SECRET_KEY")
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key or ""})

        if not self.api_key or not self.secret_key:
            raise BinanceCredentialsError(
                "Missing Binance API credentials. Set BINANCE_API_KEY and "
                "BINANCE_SECRET_KEY in your environment or .env file."
            )

    def _safe_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        safe = {}
        for key, value in params.items():
            if key == "signature":
                continue
            if key == "timestamp":
                safe[key] = "<redacted>"
            else:
                safe[key] = value
        return safe

    def _safe_response(self, endpoint: str, payload: Any) -> Any:
        if endpoint in {"/fapi/v2/account", "/fapi/v2/balance"}:
            if isinstance(payload, list):
                return {"items": len(payload)}
            if isinstance(payload, dict):
                return {
                    "assets_count": len(payload.get("assets", [])),
                    "positions_count": len(payload.get("positions", [])),
                    "canTrade": payload.get("canTrade"),
                }
            return {"type": type(payload).__name__}

        if isinstance(payload, dict):
            keys = [
                "code",
                "msg",
                "orderId",
                "clientOrderId",
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
            ]
            return {key: payload[key] for key in keys if key in payload}
        if isinstance(payload, list):
            return {"items": len(payload)}
        return payload

    def _sign_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        signed_params = dict(params)
        signed_params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(signed_params)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed_params["signature"] = signature
        return signed_params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any] | list[Dict[str, Any]]:
        params = params or {}
        request_params = self._sign_params(params) if signed else params
        url = f"{self.BASE_URL}{endpoint}"

        self.logger.info(
            "Sending Binance request",
            extra={
                "event": "binance_request",
                "method": method,
                "endpoint": endpoint,
                "params": self._safe_params(request_params),
            },
        )

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=request_params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            self.logger.error(
                "Network error while calling Binance",
                extra={
                    "event": "binance_network_error",
                    "method": method,
                    "endpoint": endpoint,
                    "error_code": exc.__class__.__name__,
                },
            )
            raise ConnectionError(
                f"Network error while calling Binance "
                f"({method} {endpoint}): {exc.__class__.__name__}"
            ) from exc

        try:
            payload: Any = response.json()
        except ValueError as exc:
            body_preview = response.text[:300]
            self.logger.error(
                "Binance returned a non-JSON response",
                extra={
                    "event": "binance_non_json_response",
                    "status_code": response.status_code,
                    "endpoint": endpoint,
                    "response": body_preview,
                },
            )
            raise BinanceAPIError(
                f"Binance returned non-JSON response "
                f"(status {response.status_code}): {body_preview}"
            ) from exc

        self.logger.info(
            "Received Binance response",
            extra={
                "event": "binance_response",
                "status_code": response.status_code,
                "endpoint": endpoint,
                "response": self._safe_response(endpoint, payload),
            },
        )

        if not response.ok:
            if isinstance(payload, dict):
                message = payload.get("msg", "Unknown Binance API error")
                code = payload.get("code", "unknown")
            else:
                message = str(payload)
                code = "unknown"
            raise BinanceAPIError(
                f"Binance API error {code} "
                f"(HTTP {response.status_code}, {endpoint}): {message}"
            )

        return payload

    def ping(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/ping")

    def get_exchange_info(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        exchange_info = self.get_exchange_info()
        symbols = exchange_info.get("symbols", [])
        target = symbol.upper()
        return next((item for item in symbols if item.get("symbol") == target), None)

    def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        result = self._request(
            "GET",
            "/fapi/v1/ticker/price",
            params={"symbol": symbol.upper()},
        )
        return result if isinstance(result, dict) else {}

    def get_balance(self) -> list[Dict[str, Any]]:
        result = self._request("GET", "/fapi/v2/balance", signed=True)
        return result if isinstance(result, list) else []

    def get_account(self) -> Dict[str, Any]:
        result = self._request("GET", "/fapi/v2/account", signed=True)
        return result if isinstance(result, dict) else {}

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        result = self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol.upper(), "orderId": order_id, "recvWindow": 5000},
            signed=True,
        )
        return result if isinstance(result, dict) else {}

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Any,
        price: Optional[Any] = None,
        time_in_force: str = "GTC",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
            "recvWindow": 5000,
            "newOrderRespType": "RESULT",
        }

        if params["type"] == "LIMIT":
            if price is None:
                raise ValueError("Price is required for LIMIT orders")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if extra_params:
            params.update(extra_params)

        result = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        return result if isinstance(result, dict) else {}
