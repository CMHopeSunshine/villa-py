from typing import (
    Union, 
    Callable, 
    Awaitable, 
    TYPE_CHECKING,
    Any
)
if TYPE_CHECKING:
    from .bot import Bot
    from .event import Event


T_Handler = Union[Callable[["Bot", "Event"], Any], Callable[["Bot", "Event"], Awaitable[Any]]]