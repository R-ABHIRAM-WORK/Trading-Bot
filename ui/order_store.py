import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "trading_app.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        existing_columns = connection.execute(
            "PRAGMA table_info(tracked_orders)"
        ).fetchall()
        if existing_columns:
            primary_keys = [row["name"] for row in existing_columns if row["pk"]]
            if primary_keys == ["order_id"]:
                existing_names = {row["name"] for row in existing_columns}
                connection.execute("ALTER TABLE tracked_orders RENAME TO tracked_orders_old")
                connection.execute(
                    """
                    CREATE TABLE tracked_orders (
                        order_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        status TEXT,
                        latest_status_json TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, order_id)
                    )
                    """
                )
                symbol_select = "symbol" if "symbol" in existing_names else "'UNKNOWN'"
                status_select = "status" if "status" in existing_names else "''"
                latest_status_select = (
                    "latest_status_json" if "latest_status_json" in existing_names else "'{}'"
                )
                created_at_select = (
                    "created_at" if "created_at" in existing_names else "CURRENT_TIMESTAMP"
                )
                connection.execute(
                    f"""
                    INSERT OR IGNORE INTO tracked_orders
                        (order_id, symbol, status, latest_status_json, created_at)
                    SELECT order_id, {symbol_select}, {status_select},
                        {latest_status_select}, {created_at_select}
                    FROM tracked_orders_old
                    """
                )
                connection.execute("DROP TABLE tracked_orders_old")
                connection.commit()
                return

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_orders (
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                status TEXT,
                latest_status_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, order_id)
            )
            """
        )
        connection.commit()


def upsert_tracked_order(
    order_id: str,
    symbol: str,
    status: str,
    latest_status: Optional[Dict[str, Any]] = None,
) -> None:
    initialize_database()
    payload = json.dumps(latest_status or {})
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tracked_orders (order_id, symbol, status, latest_status_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol, order_id) DO UPDATE SET
                symbol = excluded.symbol,
                status = excluded.status,
                latest_status_json = excluded.latest_status_json
            """,
            (order_id, symbol, status, payload),
        )
        connection.commit()


def list_tracked_orders() -> List[Dict[str, Any]]:
    initialize_database()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT order_id, symbol, status, latest_status_json, created_at
            FROM tracked_orders
            ORDER BY datetime(created_at) DESC, rowid DESC
            """
        ).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        try:
            latest_status = json.loads(row["latest_status_json"] or "{}")
        except json.JSONDecodeError:
            latest_status = {}
        results.append(
            {
                "order_id": row["order_id"],
                "symbol": row["symbol"],
                "status": row["status"],
                "latest_status": latest_status,
                "created_at": row["created_at"],
            }
        )
    return results


def delete_tracked_order(order_id: str, symbol: Optional[str] = None) -> None:
    initialize_database()
    with get_connection() as connection:
        if symbol:
            connection.execute(
                "DELETE FROM tracked_orders WHERE order_id = ? AND symbol = ?",
                (order_id, symbol),
            )
        else:
            connection.execute("DELETE FROM tracked_orders WHERE order_id = ?", (order_id,))
        connection.commit()


def clear_tracked_orders() -> None:
    initialize_database()
    with get_connection() as connection:
        connection.execute("DELETE FROM tracked_orders")
        connection.commit()
