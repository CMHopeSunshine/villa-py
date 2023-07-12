from typing import Any, Awaitable, Callable, TypeVar, Union

from .event import Event

T_Event = TypeVar("T_Event", bound=Event)


T_Handler = Union[Callable[[T_Event], Any], Callable[[T_Event], Awaitable[Any]]]
T_Func = Callable[..., Any]
