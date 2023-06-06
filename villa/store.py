from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .bot import Bot

_bots: Dict[str, "Bot"] = {}
