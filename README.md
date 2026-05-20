# Binance Futures Testnet Trading Bot

A Python trading bot for Binance USDT-M Futures Testnet. It supports MARKET and LIMIT orders from a CLI, includes a lightweight Streamlit dashboard, validates Binance symbol filters, logs sanitized API activity, and tracks submitted orders locally.

This project is intentionally testnet-only.

## Features

- Place MARKET and LIMIT orders on Binance Futures Testnet
- Support BUY and SELL sides
- Validate symbol, side, order type, quantity, price, tick size, step size, and minimum notional
- Print clear CLI request and response summaries
- Log sanitized API requests, responses, and errors
- View balances, positions, order responses, and tracked order status in Streamlit
- Persist tracked order status in a local SQLite database

## Setup

1. Create and activate a Python 3.10+ virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from `.env.example`.

```bash
# macOS/Linux
cp .env.example .env

# Windows PowerShell
copy .env.example .env
```

4. Add Binance Futures Testnet credentials to `.env`.

```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
```

## CLI Usage

MARKET order:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

LIMIT order:

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 110000
```

Interactive mode:

```bash
python cli.py
```

Use a custom log file:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --log-file logs/trading_bot.log
```

## Streamlit UI

```bash
streamlit run Trade.py
```

The dashboard can place orders, show account balances/positions, and refresh tracked order statuses.

## Logs

Runtime logs are written to `trading_bot.log` by default. They contain sanitized request and response metadata, excluding API secrets and signatures.

Sample sanitized logs are included in `examples/logs/`.

## Tests

```bash
pytest
```

The tests focus on validation, request signing/error handling, and local order persistence.

## Assumptions

- Only Binance USDT-M Futures Testnet is supported.
- The app uses direct REST calls with `requests`.
- The UI is optional and intended as a lightweight dashboard, not a production trading terminal.
- Local SQLite persistence is used only for tracked order status in the Streamlit app.
- This project does not execute autonomous strategies or trade real funds.
