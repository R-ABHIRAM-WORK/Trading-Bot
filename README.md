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

### 1. Clone the repository

```bash
git clone https://github.com/R-ABHIRAM-WORK/Trading-Bot.git
cd Trading-Bot
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your local environment file

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
copy .env.example .env
```

### 5. Add Binance Futures Testnet credentials

Open `.env` in your editor and fill in your own testnet credentials:

```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
```

You can create Binance Futures Testnet credentials from the Binance Futures Testnet site. Do not use real Binance/mainnet keys.

### 6. Check the app locally

Run the test suite:

```bash
pytest
```

Run a CLI help check:

```bash
python cli.py --help
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

Then open the local URL shown by Streamlit, usually:

```text
http://localhost:8501
```

The dashboard can place orders, show account balances/positions, and refresh tracked order statuses.

## Run Checklist

On a fresh device, the usual path is:

```bash
git clone https://github.com/R-ABHIRAM-WORK/Trading-Bot.git
cd Trading-Bot
python -m venv .venv
# activate the virtual environment for your OS
pip install -r requirements.txt
cp .env.example .env
# add your Binance Futures Testnet keys to .env
pytest
python cli.py --help
streamlit run Trade.py
```

For Windows, replace `cp .env.example .env` with:

```powershell
copy .env.example .env
```

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
