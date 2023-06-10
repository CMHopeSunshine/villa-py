import re
from typing import Any, Type, Tuple, Union, TypeVar, Callable, Optional, Awaitable

from pydantic import BaseModel

from .event import Event

T_Event = TypeVar("T_Event", bound=Event)


T_Handler = Union[Callable[[T_Event], Any], Callable[[T_Event], Awaitable[Any]]]
T_Func = Callable[..., Any]


class EventHandler(BaseModel):
    event_type: Tuple[Type[Event], ...]
    func: T_Handler
    priority: int = 1
    block: bool = False

    startswith: Optional[Tuple[str, ...]] = None
    endswith: Optional[Tuple[str, ...]] = None
    keywords: Optional[Tuple[str, ...]] = None
    regex: Optional[re.Pattern] = None

    def __str__(self) -> str:
        return f"Handler(func={self.func.__name__}, priority={self.priority}, block={self.block})"

    def __repr__(self) -> str:
        return super().__str__()
