import httpx
import asyncio
import uvicorn
from typing import Any, Dict, List, Tuple, Type
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .models import Payload, MessageContentInfo, MessageContent, ApiResponse
from .event import Event, SendMessageEvent, event_classes
from .log import logger, _log_patcher
from .utils import escape_tag, run_sync
from .typing import T_Handler
from .exception import ActionFailed

_bots: Dict[str, "Bot"] = {}

class Bot:
    _event_handlers: List[Tuple[Type[Event], T_Handler]] = []

    def __init__(self, 
                 bot_id: str, 
                 bot_secret: str, 
                 callback_url: str):
        self.bot_id = bot_id
        self.bot_secret = bot_secret
        self.callback_url = callback_url
        if bot_id in _bots:
            raise ValueError(f"Bot {bot_id} already in bots")
        _bots[bot_id] = self

    
    def _get_headers(self, villa_id: int) -> Dict[str, str]:
        return {
            "x-rpc-bot_id": self.bot_id,
            "x-rpc-bot_secret": self.bot_secret,
            "x-rpc-bot_villa_id": str(villa_id)
        } 

    
    async def _request(
            self, 
            method: str, 
            api: str, 
            villa_id: int, 
            json: Dict[str, Any],
            **kwargs
    ) -> Any:
        logger.opt(colors=True).debug(f"Calling API <y>{api}</y>")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method=method,
                    url=f"https://bbs-api.miyoushe.com/{api}",
                    headers=self._get_headers(villa_id),
                    json=json,
                    **kwargs
                )
                resp = ApiResponse.parse_raw(resp.content)
                if resp.retcode == 0:
                    return resp.data
                else:
                    raise ActionFailed(resp.retcode, resp)
        except Exception as e:
            raise e
    
    def on_event(self, event_type: Type[Event]):
        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append((event_type, func))
            return func
        
        return _decorator
    

    def on_message(self):
        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append((SendMessageEvent, func))
            return func
        
        return _decorator
    

    async def send_msg(self, 
                       villa_id: int, 
                       room_id: int,
                       message: str) -> str:
        content = MessageContentInfo(
            content=MessageContent(text=message)
        )
        return (await self._request(
            "POST",
            "vila/api/bot/platform/sendMessage",
            villa_id,
            json={
                "room_id": room_id,
                "object_name": "MHY:Text", 
                "msg_content": content.json(by_alias=True, exclude_none=True)
            }
        ))["bot_msg_id"]

    async def handle_event(self, event: Event):
        for event_type, func in self._event_handlers:
            if isinstance(event, event_type):
                if asyncio.iscoroutinefunction(func):
                    await func(self, event)
                else:
                    await run_sync(func)(self, event)


    def run(self,
            host: str = "127.0.0.1",
            port: int = 9960,
            log_level: str = "INFO",
            **kwargs):
        run_bots(bots=[self], host=host, port=port, log_level=log_level, **kwargs)


def run_bots(bots: List[Bot], 
            host: str = "127.0.0.1",
            port: int = 9960,
            log_level: str = "INFO",
            **kwargs):
    logger.configure(extra={"villa_log_level": log_level}, patcher=_log_patcher)
    logger.success("Starting Villa...")
    fastapi_kwargs = {k.lstrip("fastapi"): v for k, v in kwargs.items() if k.startswith("fastapi_")}
    uvicorn_kwargs = {k.lstrip("uvicorn_"): v for k, v in kwargs.items() if k.startswith("uvicorn_")}
    app = FastAPI(**fastapi_kwargs)
    for bot in bots:
        logger.opt(colors=True).info(f"Initializing Bot <y>{bot.bot_id}</y>")
        logger.opt(colors=True).debug(f"with Secret: <y>{bot.bot_secret}</y> and Callback URL: <y>{bot.callback_url}</y>")
        app.post(bot.callback_url, status_code=200)(handle_event)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "default": {
                    "class": "villa.log.LoguruHandler",
                },
            },
            "loggers": {
                "uvicorn.error": {"handlers": ["default"], "level": "INFO"},
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": "INFO",
                },
            },
        },
        **uvicorn_kwargs
    )

async def handle_event(data: dict) -> JSONResponse:
    if not (payload_data := data.get("event", None)):
        logger.trace(f"Received invalid data: {escape_tag(str(data))}")
        return JSONResponse(status_code=400, content={"retcode": -1, "msg": "Invalid data"})
    try:
        payload = Payload.parse_obj(payload_data)
    except Exception as e:
        logger.opt(exception=e).warning(f"Failed to parse payload {escape_tag(str(payload_data))}")
        return
    logger.trace(f"Received payload {escape_tag(repr(payload))}")
    if not (bot := _bots.get(payload.robot.template.id, None)):
        raise ValueError(f"Bot {payload.robot.template.id} not found")
    if (event_class := event_classes.get(payload.type, None)) and (
        event_class.__type__.name in payload.extend_data["EventData"]
    ):
        try:
            event = event_class.parse_obj(
                payload.extend_data["EventData"][event_class.__type__.name]
            )
            logger.opt(colors=True).success(f"<m>Bot {bot.bot_id}</m> <y>[{event.__class__.__name__}]</y>: {escape_tag(str(event.dict()))}")
        except Exception as e:
            logger.opt(exception=e).warning(f"Failed to parse event {escape_tag(repr(event))} to {event_class.__name__}")
        else:
            asyncio.create_task(bot.handle_event(event))
    else:
        logger.warning(f"Unknown event type: {event.type} data={escape_tag(str(payload.extend_data))}")

    return JSONResponse(status_code=200, content={"retcode": 0, "message": "success"})