import re
import asyncio
from typing import Type, Tuple, Optional

from pydantic import BaseModel

from .log import logger
from .utils import run_sync
from .typing import T_Handler
from .exception import StopPropagation
from .event import Event, SendMessageEvent


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

    def _check(self, event: Event) -> bool:
        """检查事件是否满足处理函数运行条件"""
        if isinstance(event, self.event_type):
            if isinstance(event, SendMessageEvent):
                if self.startswith is not None and not event.message.startswith(
                    self.startswith
                ):
                    logger.opt(colors=True).trace(
                        f"{event.get_event_name()} not startswith \"{'|'.join(self.startswith)}\" of <y>{self}</y>, pass"
                    )
                    return False
                if self.endswith is not None and not event.message.endswith(
                    self.endswith
                ):
                    logger.opt(colors=True).trace(
                        f"{event.get_event_name()} not endswith \"{'|'.join(self.endswith)}\" of <y>{self}</y>, pass"
                    )
                    return False
                if self.keywords is not None and not any(
                    keyword in event.message for keyword in self.keywords
                ):
                    logger.opt(colors=True).trace(
                        f"{event.get_event_name()} not contains \"{'|'.join(self.keywords)}\" of <y>{self}</y>, pass"
                    )
                    return False
                if self.regex is not None and not event.message.match(self.regex):
                    logger.opt(colors=True).trace(
                        f'{event.get_event_name()} not match "{self.regex}" of <y>{self}</y>, <y>pass</y>'
                    )
                    return False
            return True
        return False

    async def _run(self, event: Event):
        """运行事件处理器"""
        if not self._check(event):
            return
        try:
            logger.opt(colors=True).info(
                f"{event.get_event_name()} will be handled by <y>{self}</y>"
            )
            if asyncio.iscoroutinefunction(self.func):
                await self.func(event)
            else:
                await run_sync(self.func)(event)
            if self.block:
                raise StopPropagation(handler=self)
        except StopPropagation as e:
            raise e
        except Exception as e:
            logger.opt(colors=True, exception=e).error(
                f"Error when running <y>{self}</y> for {event.get_event_name()}"
            )
