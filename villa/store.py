from typing import Dict, Optional, TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from .bot import Bot

_bots: Dict[str, "Bot"] = {}
_app: FastAPI = FastAPI()


def get_bot(bot_id: Optional[str] = None) -> Optional["Bot"]:
    """获取一个 Bot 实例

    如果没有 Bot，则返回 None。
    如果没有指定 bot_id，则返回第一个 Bot 实例。

    返回:
        _type_: Bot
    """
    if not _bots:
        return None
    if bot_id is None:
        return _bots[list(_bots.keys())[0]]
    return _bots.get(bot_id)


def get_bots() -> Dict[str, "Bot"]:
    """获取所有 Bot 实例"""
    return _bots


def store_bot(bot: "Bot") -> None:
    if bot.bot_id in _bots:
        raise ValueError(f"Bot {bot.bot_id} already in bots")
    _bots[bot.bot_id] = bot


def get_app() -> FastAPI:
    """获取 FastAPI 实例"""
    return _app


__all__ = ["get_bot", "get_bots", "store_bot", "get_app"]
