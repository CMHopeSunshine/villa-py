from typing import Any, Union, TypeVar, Callable, Awaitable

from .event import Event

T_Event = TypeVar("T_Event", bound=Event)


T_Handler = Union[Callable[[T_Event], Any], Callable[[T_Event], Awaitable[Any]]]
T_Func = Callable[..., Any]
