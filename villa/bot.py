import re
import asyncio
from itertools import product
from typing import Any, Set, Dict, List, Type, Union, Literal, Optional

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import parse_obj_as
from fastapi.responses import JSONResponse

from .models import *
from .store import _bots
from .message import Message
from .exception import ActionFailed
from .message import MessageSegment
from .log import logger, _log_patcher
from .utils import run_sync, escape_tag
from .message import Link as LinkSegment
from .message import Text as TextSegment
from .message import Image as ImageSegment
from .typing import T_Handler, EventHandler
from .message import RoomLink as RoomLinkSegment
from .message import MentionAll as MentionAllSegment
from .message import MentionUser as MentionUserSegment
from .message import MentionRobot as MentionRobotSegment
from .event import Event, SendMessageEvent, event_classes


class Bot:
    _event_handlers: List[EventHandler] = []

    def __init__(self, bot_id: str, bot_secret: str, callback_url: str):
        self.bot_id: str = bot_id
        self.bot_secret: str = bot_secret
        self.callback_url: str = callback_url
        self.bot_info: Optional[Robot] = None
        if bot_id in _bots:
            raise ValueError(f"Bot {bot_id} already in bots")
        _bots[bot_id] = self

    def on_event(
        self, *event_type: Type[Event], block: bool = False, priority: int = 1
    ):
        """注册一个事件处理函数

        当事件属于 event_type 中的任意一个时，执行处理函数。

        参数:
            block: 是否阻止更低优先级的处理函数执行. 默认为 False.
            priority: 优先级. 默认为 1.
        """

        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append(
                EventHandler(
                    event_type=event_type, func=func, block=block, priority=priority
                )
            )
            self._event_handlers.sort(key=lambda x: x.priority)
            return func

        return _decorator

    def on_message(self, block: bool = False, priority: int = 1):
        """注册一个消息事件处理函数

        当事件属于 SendMessageEvent 消息事件时，执行处理函数。

        参数:
            block: 是否阻止更低优先级的处理函数执行. 默认为 False.
            priority: 优先级. 默认为 1.
        """

        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append(
                EventHandler(
                    event_type=(SendMessageEvent,),
                    func=func,
                    block=block,
                    priority=priority,
                )
            )
            self._event_handlers.sort(key=lambda x: x.priority)
            return func

        return _decorator

    def on_startswith(
        self,
        *startswith: str,
        prefix: Union[str, Set[str]] = set(""),
        block: bool = False,
        priority: int = 1,
    ):
        """注册一个消息事件处理函数

        当事件属于 SendMessageEvent 消息事件且纯文本部分以指定字符串开头时，执行处理函数。

        参数:
            *startswith: 字符串列表.
            prefix: 字符串前缀. 可以是字符串或字符串集合. 默认为 "".
            block: 是否阻止更低优先级的处理函数执行. 默认为 False.
            priority: 优先级. 默认为 1.
        """
        if isinstance(prefix, str):
            prefix = {prefix}
        startswith = tuple(set(p + s for p, s in list(product(prefix, startswith))))

        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append(
                EventHandler(
                    event_type=(SendMessageEvent,),
                    func=func,
                    block=block,
                    priority=priority,
                    startswith=startswith or None,
                )
            )
            self._event_handlers.sort(key=lambda x: x.priority)
            return func

        return _decorator

    def on_endswith(self, *endswith: str, block: bool = False, priority: int = 1):
        """注册一个消息事件处理函数

        当事件属于 SendMessageEvent 消息事件且纯文本部分以指定字符串结尾时，执行处理函数。

        参数:
            *endswith: 字符串列表.
            block: 是否阻止更低优先级的处理函数执行. 默认为 False.
            priority: 优先级. 默认为 1.
        """

        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append(
                EventHandler(
                    event_type=(SendMessageEvent,),
                    func=func,
                    block=block,
                    priority=priority,
                    endswith=endswith or None,
                )
            )
            self._event_handlers.sort(key=lambda x: x.priority)
            return func

        return _decorator

    def on_keyword(self, *keywords: str, block: bool = False, priority: int = 1):
        """注册一个消息事件处理函数

        当事件属于 SendMessageEvent 消息事件且纯文本部分包含指定关键词时，执行处理函数。

        参数:
            *keywords: 关键词列表.
            block: 是否阻止更低优先级的处理函数执行. 默认为 False.
            priority: 优先级. 默认为 1.
        """

        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append(
                EventHandler(
                    event_type=(SendMessageEvent,),
                    func=func,
                    block=block,
                    priority=priority,
                    keywords=keywords or None,
                )
            )
            self._event_handlers.sort(key=lambda x: x.priority)
            return func

        return _decorator

    def on_regex(
        self, pattern: Union[str, re.Pattern], block: bool = False, priority: int = 1
    ):
        """注册一个消息事件处理函数

        当事件属于 SendMessageEvent 消息事件且纯文本部分与正则表达式匹配时，执行处理函数。

        参数:
            pattern: 正则表达式.
            block: 是否阻止更低优先级的处理函数执行. 默认为 False.
            priority: 优先级. 默认为 1.
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        def _decorator(func: T_Handler) -> T_Handler:
            self._event_handlers.append(
                EventHandler(
                    event_type=(SendMessageEvent,),
                    func=func,
                    block=block,
                    priority=priority,
                    regex=pattern,
                )
            )
            self._event_handlers.sort(key=lambda x: x.priority)
            return func

        return _decorator

    async def send(
        self, villa_id: int, room_id: int, message: Union[str, Message, MessageSegment]
    ) -> str:
        if isinstance(message, str):
            message = MessageSegment.text(message)
        if isinstance(message, MessageSegment):
            message = Message(message)
        content = await self._parse_message_content(message)
        return await self.send_message(
            villa_id=villa_id,
            room_id=room_id,
            object_name="MHY:Text",
            msg_content=content,
        )

    async def check_member_bot_access_token(
        self, token: str, villa_id: Optional[int] = None
    ) -> CheckMemberBotAccessTokenReturn:
        return CheckMemberBotAccessTokenReturn.parse_obj(
            await self._request(
                "GET",
                "vila/api/bot/platform/checkMemberBotAccessToken",
                villa_id,
                json={"token": token},
            )
        )

    async def get_villa(self, villa_id: int) -> Villa:
        return Villa.parse_obj(
            (
                await self._request(
                    "GET", "vila/api/bot/platform/getVilla", villa_id, json={}
                )
            )["villa"]
        )

    async def get_member(self, villa_id: int, uid: int) -> Member:
        return Member.parse_obj(
            (
                await self._request(
                    "GET",
                    "vila/api/bot/platform/getMember",
                    villa_id,
                    json={"uid": uid},
                )
            )["member"]
        )

    async def get_villa_members(
        self, villa_id: int, offset: int, size: int
    ) -> MemberListReturn:
        return MemberListReturn.parse_obj(
            await self._request(
                "GET",
                "vila/api/bot/platform/getVillaMembers",
                villa_id,
                json={"offset": offset, "size": size},
            )
        )

    async def delete_villa_member(self, villa_id: int, uid: int) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/deleteVillaMember",
            villa_id,
            json={"uid": uid},
        )

    async def pin_message(
        self, villa_id: int, msg_uid: str, is_cancel: bool, room_id: int, send_at: int
    ) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/pinMessage",
            villa_id,
            json={
                "msg_uid": msg_uid,
                "is_cancel": is_cancel,
                "room_id": room_id,
                "send_at": send_at,
            },
        )

    async def recall_message(
        self, villa_id: int, msg_uid: str, room_id: int, msg_time: int
    ) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/recallMessage",
            villa_id,
            json={"msg_uid": msg_uid, "msg_time": msg_time, "room_id": room_id},
        )

    async def send_message(
        self,
        villa_id: int,
        room_id: int,
        object_name: str,
        msg_content: Union[str, MessageContentInfo],
    ) -> str:
        if isinstance(msg_content, MessageContentInfo):
            content = msg_content.json(by_alias=True, exclude_none=True)
        else:
            content = msg_content
        return (
            await self._request(
                "POST",
                "vila/api/bot/platform/sendMessage",
                villa_id,
                json={
                    "room_id": room_id,
                    "object_name": object_name,
                    "msg_content": content,
                },
            )
        )["bot_msg_id"]

    async def create_group(self, villa_id: int, group_name: str) -> int:
        return (
            await self._request(
                "POST",
                "vila/api/bot/platform/createGroup",
                villa_id,
                json={
                    "group_name": group_name,
                },
            )
        )["group_id"]

    async def edit_group(self, villa_id: int, group_id: int, group_name: str) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/editGroup",
            villa_id,
            json={"group_id": group_id, "group_name": group_name},
        )

    async def delete_group(self, villa_id: int, group_id: int) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/deleteGroup",
            villa_id,
            json={"group_id": group_id},
        )

    async def get_group_list(self, villa_id: int) -> List[Group]:
        return parse_obj_as(
            List[Group],
            (
                await self._request(
                    "GET", "vila/api/bot/platform/getGroupList", villa_id, json={}
                )
            )["list"],
        )

    async def sort_group_list(self, villa_id: int, group_ids: List[int]) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/sortGroupList",
            villa_id,
            json={"villa_id": villa_id, "group_ids": group_ids},
        )

    async def create_room(
        self,
        villa_id: int,
        room_name: str,
        room_type: Union[Literal[1, 2, 3], CreateRoomType],
        group_id: int,
        room_default_notify_type: Union[Literal[1, 2], CreateRoomDefaultNotifyType],
        send_msg_auth_range: SendMsgAuthRange,
    ) -> Room:
        return Room.parse_obj(
            (
                await self._request(
                    "POST",
                    "vila/api/bot/platform/createRoom",
                    villa_id,
                    json={
                        "room_name": room_name,
                        "room_type": room_type,
                        "group_id": group_id,
                        "room_default_notify_type": room_default_notify_type,
                        "send_msg_auth_range": send_msg_auth_range.dict(),
                    },
                )
            )["room"]
        )

    async def edit_room(self, villa_id: int, room_id: int, room_name: str) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/editRoom",
            villa_id,
            json={"room_id": room_id, "room_name": room_name},
        )

    async def delete_room(self, villa_id: int, room_id: int) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/deleteRoom",
            villa_id,
            json={"room_id": room_id},
        )

    async def get_room(self, villa_id: int, room_id: int) -> Room:
        return Room.parse_obj(
            await self._request(
                "GET",
                "vila/api/bot/platform/getRoom",
                villa_id,
                json={"room_id": room_id},
            )
        )

    async def get_villa_group_room_list(self, villa_id: int) -> GroupRoom:
        return GroupRoom.parse_obj(
            (
                await self._request(
                    "GET",
                    "vila/api/bot/platform/getVillaGroupRoomList",
                    villa_id,
                    json={},
                )
            )["list"]
        )

    async def sort_room_list(self, villa_id: int, room_list: List[RoomSort]) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/sortRoomList",
            villa_id,
            json={
                "villa_id": villa_id,
                "room_list": [room.dict() for room in room_list],
            },
        )

    async def operate_member_to_role(
        self, villa_id: int, role_id: int, uid: int, is_add: bool
    ) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/operateMemberToRole",
            villa_id,
            json={"role_id": role_id, "uid": uid, "is_add": is_add},
        )

    async def create_member_role(
        self, villa_id: int, name: str, color: Color, permissions: List[Permission]
    ) -> int:
        return (
            await self._request(
                "POST",
                "vila/api/bot/platform/createMemberRole",
                villa_id,
                json={"name": name, "color": str(color), "permissions": permissions},
            )
        )["id"]

    async def edit_member_role(
        self,
        villa_id: int,
        role_id: int,
        name: str,
        color: Color,
        permissions: List[Permission],
    ) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/editMemberRole",
            villa_id,
            json={
                "id": role_id,
                "name": name,
                "color": str(color),
                "permissions": permissions,
            },
        )

    async def delete_member_role(self, villa_id: int, role_id: int) -> None:
        await self._request(
            "POST",
            "vila/api/bot/platform/deleteMemberRole",
            villa_id,
            json={"id": role_id},
        )

    async def get_member_role_info(
        self, villa_id: int, role_id: int
    ) -> MemberRoleDetail:
        return MemberRoleDetail.parse_obj(
            (
                await self._request(
                    "GET",
                    "vila/api/bot/platform/getMemberRoleInfo",
                    villa_id,
                    json={"id": role_id},
                )
            )["role"]
        )

    async def get_villa_member_roles(self, villa_id: int) -> List[MemberRoleDetail]:
        return parse_obj_as(
            List[MemberRoleDetail],
            (
                await self._request(
                    "GET",
                    "vila/api/bot/platform/getVillaMemberRoles",
                    villa_id,
                    json={},
                )
            )["list"],
        )

    async def get_all_emoticons(self, villa_id: int) -> List[Emoticon]:
        return parse_obj_as(
            List[Emoticon],
            (
                await self._request(
                    "GET",
                    "vila/api/bot/platform/getAllEmoticons",
                    villa_id,
                    json={},
                )
            )["list"],
        )

    async def audit(
        self,
        villa_id: int,
        audit_content: str,
        pass_through: str,
        room_id: int,
        uid: int,
    ) -> int:
        return (
            await self._request(
                "POST",
                "vila/api/bot/platform/audit",
                villa_id,
                json={
                    "audit_content": audit_content,
                    "pass_through": pass_through,
                    "room_id": room_id,
                    "uid": uid,
                },
            )
        )["audit_id"]

    def _get_headers(self, villa_id: Optional[int] = None) -> Dict[str, str]:
        return {
            "x-rpc-bot_id": self.bot_id,
            "x-rpc-bot_secret": self.bot_secret,
            "x-rpc-bot_villa_id": str(villa_id) if villa_id else "",
        }

    async def _request(
        self,
        method: str,
        api: str,
        villa_id: Optional[int],
        json: Dict[str, Any],
        **kwargs,
    ) -> Any:
        logger.opt(colors=True).debug(
            f"<b><m>{self.bot_id}</m></b> | Calling API <y>{api.split('/')[-1]}</y>"
        )
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method=method,
                    url=f"https://bbs-api.miyoushe.com/{api}",
                    headers=self._get_headers(villa_id),
                    json=json,
                    **kwargs,
                )
                resp = ApiResponse.parse_raw(resp.content)
                if resp.retcode == 0:
                    return resp.data
                else:
                    raise ActionFailed(resp.retcode, resp)
        except Exception as e:
            raise e

    async def _handle_event(self, event: Event):
        is_handled = False
        for event_handler in self._event_handlers:
            if isinstance(event, event_handler.event_type):
                if isinstance(event, SendMessageEvent):
                    if (
                        event_handler.startswith is not None
                        and not event.message.startswith(event_handler.startswith)
                    ):
                        logger.opt(colors=True).trace(
                            f"<b><y>[{event.__class__.__name__}]</y></b> not startswith \"{'|'.join(event_handler.startswith)}\", pass"
                        )
                        continue
                    if (
                        event_handler.endswith is not None
                        and not event.message.endswith(event_handler.endswith)
                    ):
                        logger.opt(colors=True).trace(
                            f"<b><y>[{event.__class__.__name__}]</y></b> not endswith \"{'|'.join(event_handler.endswith)}\", pass"
                        )
                        continue
                    if event_handler.keywords is not None and not any(
                        keyword in event.message for keyword in event_handler.keywords
                    ):
                        logger.opt(colors=True).trace(
                            f"<b><y>[{event.__class__.__name__}]</y></b> not contains \"{'|'.join(event_handler.keywords)}\", pass"
                        )
                        continue
                    if event_handler.regex is not None and not event.message.match(
                        event_handler.regex
                    ):
                        logger.opt(colors=True).trace(
                            f'<b><y>[{event.__class__.__name__}]</y></b> not match "{event_handler.regex}", <y>pass</y>'
                        )
                        continue
                logger.opt(colors=True).info(
                    f"<b><y>[{event.__class__.__name__}]</y></b> will be handled by <y>{event_handler}</y>"
                )
                await run_handler(event_handler, event)
                is_handled = True
                if event_handler.block:
                    logger.opt(colors=True).debug(
                        f"<b><y>[{event.__class__.__name__}]</y></b> stop handled by <y>{event_handler}</y>"
                    )
                    break
        if is_handled:
            logger.opt(colors=True).success(
                f"<b><y>[{event.__class__.__name__}]</y></b> handle completed"
            )

    async def _parse_message_content(self, message: Message) -> MessageContentInfo:
        if quote := message["quote", 1]:
            quote = QuoteInfo(**quote.dict())
        message_text = ""
        message_offset = 0
        entities: List[TextEntity] = []
        images: List[Image] = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for i, seg in enumerate(message.__root__):
            try:
                space = " " if i != len(message) - 1 else ""
                if isinstance(seg, TextSegment):
                    message_text += seg.content
                    message_offset += len(seg.content)
                elif isinstance(seg, MentionAllSegment):
                    message_text += "@全体成员{space}"
                    entities.append(
                        TextEntity(
                            offset=message_offset, length=6, entity=MentionedAll()
                        )
                    )
                    message_offset += 6
                    mentioned.type = MentionType.ALL
                elif isinstance(seg, MentionRobotSegment):
                    bot_name = self.bot_info.template.name if self.bot_info else "Bot"
                    message_text += f"@{bot_name}{space}"
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=len(f"@{bot_name}".encode("utf-16")) // 2,
                            entity=MentionedRobot(bot_id=self.bot_id),
                        )
                    )
                    message_offset += len(f"@{bot_name}") + 1
                    mentioned.user_id_list.append(self.bot_id)
                elif isinstance(seg, MentionUserSegment):
                    # 需要调用API获取被@的用户的昵称
                    user = await self.get_member(villa_id=seg.villa_id, uid=seg.user_id)
                    message_text += f"@{user.basic.nickname}{space}"
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=len(f"@{user.basic.nickname}".encode("utf-16")) // 2,
                            entity=MentionedUser(user_id=str(user.basic.uid)),
                        )
                    )
                    message_offset += len(f"@{user.basic.nickname}") + 1
                    mentioned.user_id_list.append(str(user.basic.uid))
                elif isinstance(seg, RoomLinkSegment):
                    # 需要调用API获取房间的名称
                    room = await self.get_room(
                        villa_id=seg.villa_id, room_id=seg.room_id
                    )
                    message_text += f"#{room.room_name}{space}"
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=len(f"#{room.room_name}".encode("utf-16")) // 2,
                            entity=VillaRoomLink(
                                villa_id=str(seg.villa_id),
                                room_id=str(seg.room_id),
                            ),
                        )
                    )
                    message_offset += len(f"#{room.room_name} ")
                elif isinstance(seg, LinkSegment):
                    show_text = seg.show_text or seg.url
                    message_text += show_text + space
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=len(show_text.encode("utf-16")) // 2,
                            entity=Link(url=seg.url),
                        )
                    )
                    message_offset += len(show_text) + 1
                elif isinstance(seg, ImageSegment):
                    images.append(
                        Image(
                            url=seg.url,
                            size=ImageSize(width=seg.width, height=seg.height)
                            if (seg.width and seg.height)
                            else None,
                            file_size=seg.file_size,
                        )
                    )
            except Exception as e:
                logger.opt(exception=e).warning("error when parse message content")

        # 不能单独只发图片而没有其他文本内容
        if images and not message_text:
            message_text = "图片"

        if not (mentioned.type == MentionType.ALL and mentioned.user_id_list):
            mentioned = None
        return MessageContentInfo(
            content=MessageContent(text=message_text, entities=entities, images=images),
            mentionedInfo=mentioned,
            quote=quote,
        )

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 13350,
        log_level: str = "INFO",
        **kwargs,
    ):
        run_bots(bots=[self], host=host, port=port, log_level=log_level, **kwargs)


def run_bots(
    bots: List[Bot],
    host: str = "127.0.0.1",
    port: int = 13350,
    log_level: str = "INFO",
    **kwargs,
):
    logger.configure(extra={"villa_log_level": log_level}, patcher=_log_patcher)
    logger.success("Starting Villa...")
    fastapi_kwargs = {
        k.lstrip("fastapi"): v for k, v in kwargs.items() if k.startswith("fastapi_")
    }
    uvicorn_kwargs = {
        k.lstrip("uvicorn_"): v for k, v in kwargs.items() if k.startswith("uvicorn_")
    }
    app = FastAPI(**fastapi_kwargs)
    for bot in bots:
        logger.opt(colors=True).info(f"Initializing Bot <m>{bot.bot_id}</m>...")
        logger.opt(colors=True).debug(
            f"With Secret: <m>{bot.bot_secret}</m> and Callback URL: <m>{bot.callback_url}</m>"
        )
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
        **uvicorn_kwargs,
    )


async def handle_event(data: dict) -> JSONResponse:
    if not (payload_data := data.get("event", None)):
        logger.warning(f"Received invalid data: {escape_tag(str(data))}")
        return JSONResponse(
            status_code=400, content={"retcode": -1, "msg": "Invalid data"}
        )
    try:
        payload = Payload.parse_obj(payload_data)
    except Exception as e:
        logger.opt(exception=e).warning(
            f"Failed to parse payload {escape_tag(str(payload_data))}"
        )
        return JSONResponse(
            status_code=400, content={"retcode": -1, "msg": "Invalid data"}
        )
    logger.trace(f"Received payload {escape_tag(repr(payload))}")
    if not (bot := _bots.get(payload.robot.template.id, None)):
        raise ValueError(f"Bot {payload.robot.template.id} not found")
    bot.bot_info = payload.robot
    if (event_class := event_classes.get(payload.type, None)) and (
        event_class.__type__.name in payload.extend_data["EventData"]
    ):
        try:
            event = event_class.parse_obj(
                payload.extend_data["EventData"][event_class.__type__.name]
            )
            logger.opt(colors=True).success(
                f"<b><m>{bot.bot_id}</m></b> | <b><y>[{event.__class__.__name__}]</y></b>: {escape_tag(str(event.dict()))}"
            )
        except Exception as e:
            logger.opt(exception=e).warning(
                f"Failed to parse event {escape_tag(str(payload.extend_data['EventData']))} to {event_class.__name__}"
            )
        else:
            asyncio.create_task(bot._handle_event(event))
    else:
        logger.warning(
            f"Unknown event type: {payload.type} data={escape_tag(str(payload.extend_data))}"
        )

    return JSONResponse(status_code=200, content={"retcode": 0, "message": "success"})


async def run_handler(handler: EventHandler, event: Event):
    try:
        if asyncio.iscoroutinefunction(handler.func):
            await handler.func(event)
        else:
            await run_sync(handler.func)(event)
    except Exception as e:
        logger.opt(exception=e).error(
            f"Error when running {handler} for {event.__class__.__name__}"
        )
