import logging
from pathlib import Path
from typing import Any


class ExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base_message = super().format(record)
        extra_fields = []
        for key in [
            "event",
            "method",
            "endpoint",
            "status_code",
            "symbol",
            "side",
            "order_type",
            "quantity",
            "price",
            "order_id",
            "order_status",
            "params",
            "response",
            "error_code",
        ]:
            value: Any = getattr(record, key, None)
            if value is not None:
                extra_fields.append(f"{key}={value}")
        if not extra_fields:
            return base_message
        return f"{base_message} | {' '.join(extra_fields)}"


def setup_logging(log_file: str = "trading_bot.log") -> logging.Logger:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.INFO)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = ExtraFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger
