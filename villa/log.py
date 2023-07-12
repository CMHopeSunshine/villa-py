import logging
import sys
from typing import TYPE_CHECKING

import loguru

if TYPE_CHECKING:
    from loguru import Logger, Record

logger: "Logger" = loguru.logger


class LoguruHandler(logging.Handler):
    """logging 与 loguru 之间的桥梁，将 logging 的日志转发到 loguru。"""

    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def default_filter(record: "Record"):
    """默认的日志过滤器，根据 `config.log_level` 配置改变日志等级。"""
    log_level = record["extra"].get("villa_log_level", "INFO")
    levelno = logger.level(log_level).no if isinstance(log_level, str) else log_level
    return record["level"].no >= levelno


default_format: str = (
    "<g>{time:MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    "{message}"
)
"""默认日志格式"""


def _log_patcher(record: "loguru.Record"):
    record["name"] = record["name"].split(".")[0]  # type: ignore


logger.remove()
logger_id = logger.add(
    sys.stdout,
    level=0,
    diagnose=True,
    backtrace=False,
    filter=default_filter,
    format=default_format,
)
