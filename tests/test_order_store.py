from pathlib import Path

from ui import order_store
from ui.ui_helpers import refresh_tracked_orders


def test_tracked_orders_are_scoped_by_symbol_and_order_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")

    order_store.upsert_tracked_order(
        order_id="100",
        symbol="BTCUSDT",
        status="NEW",
        latest_status={"status": "NEW"},
    )
    order_store.upsert_tracked_order(
        order_id="100",
        symbol="ETHUSDT",
        status="FILLED",
        latest_status={"status": "FILLED"},
    )

    rows = order_store.list_tracked_orders()

    assert len(rows) == 2
    assert {row["symbol"] for row in rows} == {"BTCUSDT", "ETHUSDT"}


def test_delete_tracked_order_can_use_symbol_scope(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")

    order_store.upsert_tracked_order("100", "BTCUSDT", "NEW", {"status": "NEW"})
    order_store.upsert_tracked_order("100", "ETHUSDT", "NEW", {"status": "NEW"})

    order_store.delete_tracked_order("100", "BTCUSDT")

    rows = order_store.list_tracked_orders()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ETHUSDT"


def test_corrupt_status_json_does_not_crash_listing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")
    order_store.initialize_database()

    with order_store.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tracked_orders
                (order_id, symbol, status, latest_status_json)
            VALUES (?, ?, ?, ?)
            """,
            ("broken", "BTCUSDT", "NEW", "{bad json"),
        )
        connection.commit()

    rows = order_store.list_tracked_orders()
    assert rows[0]["latest_status"] == {}


def test_newest_order_uses_row_order_when_timestamps_match(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")
    order_store.initialize_database()

    with order_store.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tracked_orders
                (order_id, symbol, status, latest_status_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("1", "BTCUSDT", "NEW", "{}", "2026-05-20 10:00:00"),
        )
        connection.execute(
            """
            INSERT INTO tracked_orders
                (order_id, symbol, status, latest_status_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2", "ETHUSDT", "NEW", "{}", "2026-05-20 10:00:00"),
        )
        connection.commit()

    rows = order_store.list_tracked_orders()
    assert rows[0]["order_id"] == "2"


def test_refresh_tracked_orders_marks_bad_order_id_without_crashing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")
    order_store.upsert_tracked_order("not-an-int", "BTCUSDT", "NEW", {"status": "NEW"})

    class Client:
        def get_order(self, symbol: str, order_id: int) -> dict:
            raise AssertionError("bad IDs should fail before the client call")

    refresh_tracked_orders(Client())

    rows = order_store.list_tracked_orders()
    assert rows[0]["status"] == "REFRESH_FAILED"


def test_refresh_tracked_orders_updates_each_order_even_when_one_fails(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")
    order_store.upsert_tracked_order("1", "BTCUSDT", "NEW", {"status": "NEW"})
    order_store.upsert_tracked_order("2", "ETHUSDT", "NEW", {"status": "NEW"})

    class Client:
        def get_order(self, symbol: str, order_id: int) -> dict:
            if symbol == "BTCUSDT":
                raise RuntimeError("temporary failure")
            return {"status": "FILLED", "executedQty": "1", "avgPrice": "100"}

    refresh_tracked_orders(Client())

    rows = {(row["symbol"], row["order_id"]): row for row in order_store.list_tracked_orders()}
    assert rows[("BTCUSDT", "1")]["status"] == "REFRESH_FAILED"
    assert rows[("ETHUSDT", "2")]["status"] == "FILLED"


def test_migrates_legacy_order_table_without_symbol(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(order_store, "DB_PATH", tmp_path / "orders.db")

    with order_store.get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE tracked_orders (
                order_id TEXT PRIMARY KEY
            )
            """
        )
        connection.execute("INSERT INTO tracked_orders (order_id) VALUES (?)", ("legacy",))
        connection.commit()

    order_store.initialize_database()
    rows = order_store.list_tracked_orders()

    assert rows[0]["order_id"] == "legacy"
    assert rows[0]["symbol"] == "UNKNOWN"
