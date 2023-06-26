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
from .message import Message
from .exception import ActionFailed
from .message import MessageSegment
from .log import logger, _log_patcher
from .utils import run_sync, escape_tag
from .message import Link as LinkSegment
from .message import Post as PostSegment
from .message import Text as TextSegment
from .message import Image as ImageSegment
from .store import get_app, get_bot, store_bot
from .message import RoomLink as RoomLinkSegment
from .typing import T_Func, T_Handler, EventHandler
from .message import MentionAll as MentionAllSegment
from .message import MentionUser as MentionUserSegment
from .message import MentionRobot as MentionRobotSegment
from .event import Event, SendMessageEvent, event_classes, pre_handle_event


class Bot:
    """Villa Bot"""

    _event_handlers: List[EventHandler] = []
    _client: httpx.AsyncClient
    bot_id: str
    """机器人 Id"""
    bot_secret: str
    """机器人密钥"""
    callback_url: str
    """事件回调地址"""
    _bot_info: Optional[Robot] = None
    """机器人信息"""

    def __init__(self, bot_id: str, bot_secret: str, callback_url: str):
        """初始化一个 Bot 实例

        参数:
            bot_id: 机器人 ID
            bot_secret: 机器人密钥
            callback_url: 事件回调地址
        """
        self.bot_id: str = bot_id
        self.bot_secret: str = bot_secret
        self.callback_url: str = callback_url
        self._client = httpx.AsyncClient(
            base_url="https://bbs-api.miyoushe.com/vila/api/bot/platform/"
        )
        store_bot(self)

    @property
    def nickname(self) -> str:
        """Bot 昵称"""
        if self._bot_info is None:
            raise ValueError(f"Bot {self.bot_id} not connected")
        return self._bot_info.template.name

    @property
    def avatar_icon(self) -> str:
        """Bot 头像地址"""
        if self._bot_info is None:
            raise ValueError(f"Bot {self.bot_id} not connected")
        return self._bot_info.template.icon

    @property
    def commands(self) -> Optional[List[Command]]:
        """Bot 预设命令列表"""
        if self._bot_info is None:
            raise ValueError(f"Bot {self.bot_id} not connected")
        return self._bot_info.template.commands

    @property
    def description(self) -> str:
        """Bot 介绍"""
        if self._bot_info is None:
            raise ValueError(f"Bot {self.bot_id} not connected")
        return self._bot_info.template.desc

    @property
    def current_villa_id(self) -> int:
        """Bot 最后收到的事件的大别野 ID"""
        if self._bot_info is None:
            raise ValueError(f"Bot {self.bot_id} not connected")
        return self._bot_info.villa_id

    def on_event(
        self, *event_type: Type[Event], block: bool = False, priority: int = 1
    ):
        """注册一个事件处理函数

        当事件属于 event_type 中的任意一个时，执行处理函数。

        参数:
            *event_type: 事件类型列表.
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
        """发送消息

        参数:
            villa_id: 大别野 ID
            room_id: 房间 ID
            message: 消息内容

        返回:
            str: 消息 ID
        """
        if isinstance(message, str):
            message = MessageSegment.text(message)
        if isinstance(message, MessageSegment):
            message = Message(message)
        content_info = await self._parse_message_content(message)
        if isinstance(content_info.content, TextMessageContent):
            object_name = "MHY:Text"
        elif isinstance(content_info.content, ImageMessageContent):
            object_name = "MHY:Image"
        else:
            object_name = "MHY:Post"
        return await self.send_message(
            villa_id=villa_id,
            room_id=room_id,
            object_name=object_name,
            msg_content=content_info.json(by_alias=True, exclude_none=True),
        )

    async def check_member_bot_access_token(
        self, token: str, villa_id: Optional[int] = None
    ) -> CheckMemberBotAccessTokenReturn:
        """校验用户机器人访问凭证，并返回用户信息

        参数:
            token: 用户机器人访问凭证
            villa_id: 大别野 ID. 默认为 None.

        返回:
            CheckMemberBotAccessTokenReturn: 用户信息
        """
        return CheckMemberBotAccessTokenReturn.parse_obj(
            await self._request(
                "GET",
                "checkMemberBotAccessToken",
                villa_id,
                json={"token": token},
            )
        )

    async def get_villa(self, villa_id: int) -> Villa:
        """获取大别野信息

        参数:
            villa_id: 大别野 ID

        返回:
            Villa: 大别野信息
        """
        return Villa.parse_obj(
            (await self._request("GET", "getVilla", villa_id, json={}))["villa"]
        )

    async def get_member(self, villa_id: int, uid: int) -> Member:
        """获取用户信息

        参数:
            villa_id: 大别野
            uid: 用户 ID

        返回:
            Member: 用户详情
        """
        return Member.parse_obj(
            (
                await self._request(
                    "GET",
                    "getMember",
                    villa_id,
                    json={"uid": uid},
                )
            )["member"]
        )

    async def get_villa_members(
        self, villa_id: int, offset: int, size: int
    ) -> MemberListReturn:
        """获取大别野成员列表

        参数:
            villa_id: 大别野 ID
            offset: 偏移量
            size: 分页大小

        返回:
            MemberListReturn: 大别野成员列表信息
        """
        return MemberListReturn.parse_obj(
            await self._request(
                "GET",
                "getVillaMembers",
                villa_id,
                json={"offset": offset, "size": size},
            )
        )

    async def delete_villa_member(self, villa_id: int, uid: int) -> None:
        """踢出大别野用户

        参数:
            villa_id: 大别野 ID
            uid: 用户 ID
        """
        await self._request(
            "POST",
            "deleteVillaMember",
            villa_id,
            json={"uid": uid},
        )

    async def pin_message(
        self, villa_id: int, msg_uid: str, is_cancel: bool, room_id: int, send_at: int
    ) -> None:
        """置顶消息

        参数:
            villa_id: 大别野 ID
            msg_uid: 消息 ID
            is_cancel: 是否取消置顶
            room_id: 房间 ID
            send_at: 消息发送时间
        """
        await self._request(
            "POST",
            "pinMessage",
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
        """撤回消息

        参数:
            villa_id: 大别野 ID
            msg_uid: 消息 ID
            room_id: 房间 ID
            msg_time: 消息发送时间
        """
        await self._request(
            "POST",
            "recallMessage",
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
        """发送消息

        参数:
            villa_id: 大别野 ID
            room_id: 房间 ID
            object_name: 消息类型
            msg_content: 将 MsgContentInfo 结构体序列化后的字符串

        返回:
            str: 消息 ID
        """
        if isinstance(msg_content, MessageContentInfo):
            content = msg_content.json(by_alias=True, exclude_none=True)
        else:
            content = msg_content
        return (
            await self._request(
                "POST",
                "sendMessage",
                villa_id,
                json={
                    "room_id": room_id,
                    "object_name": object_name,
                    "msg_content": content,
                },
            )
        )["bot_msg_id"]

    async def create_group(self, villa_id: int, group_name: str) -> int:
        """创建分组

        参数:
            villa_id: 大别野 ID
            group_name: 分组名称

        返回:
            int: 分组 ID
        """
        return (
            await self._request(
                "POST",
                "createGroup",
                villa_id,
                json={
                    "group_name": group_name,
                },
            )
        )["group_id"]

    async def edit_group(self, villa_id: int, group_id: int, group_name: str) -> None:
        """编辑分组

        参数:
            villa_id: 大别野 ID
            group_id: 分组 ID
            group_name: 分组名称
        """
        await self._request(
            "POST",
            "editGroup",
            villa_id,
            json={"group_id": group_id, "group_name": group_name},
        )

    async def delete_group(self, villa_id: int, group_id: int) -> None:
        """删除分组

        参数:
            villa_id: 大别野 ID
            group_id: 分组 ID
        """
        await self._request(
            "POST",
            "deleteGroup",
            villa_id,
            json={"group_id": group_id},
        )

    async def get_group_list(self, villa_id: int) -> List[Group]:
        """获取分组列表

        参数:
            villa_id: 大别野 ID

        返回:
            List[Group]: 分组列表
        """
        return parse_obj_as(
            List[Group],
            (await self._request("GET", "getGroupList", villa_id, json={}))["list"],
        )

    async def sort_group_list(self, villa_id: int, group_ids: List[int]) -> None:
        """分组列表排序

        参数:
            villa_id: 大别野 ID
            group_ids: 分组 ID 排序
        """
        await self._request(
            "POST",
            "sortGroupList",
            villa_id,
            json={"villa_id": villa_id, "group_ids": group_ids},
        )

    async def edit_room(self, villa_id: int, room_id: int, room_name: str) -> None:
        """编辑房间

        参数:
            villa_id: 大别野 ID
            room_id: 房间 ID
            room_name: 房间名称
        """
        await self._request(
            "POST",
            "editRoom",
            villa_id,
            json={"room_id": room_id, "room_name": room_name},
        )

    async def delete_room(self, villa_id: int, room_id: int) -> None:
        """删除房间

        参数:
            villa_id: 大别野 ID
            room_id: 房间 ID
        """
        await self._request(
            "POST",
            "deleteRoom",
            villa_id,
            json={"room_id": room_id},
        )

    async def get_room(self, villa_id: int, room_id: int) -> Room:
        """获取房间信息

        参数:
            villa_id: 大别野 ID
            room_id: 房间 ID

        返回:
            Room: 房间详情
        """
        return Room.parse_obj(
            (
                await self._request(
                    "GET",
                    "getRoom",
                    villa_id,
                    json={"room_id": room_id},
                )
            )["room"]
        )

    async def get_villa_group_room_list(self, villa_id: int) -> GroupRoom:
        """获取房间列表信息

        参数:
            villa_id: 大别野 ID

        返回:
            GroupRoom: 房间列表
        """
        return GroupRoom.parse_obj(
            (
                await self._request(
                    "GET",
                    "getVillaGroupRoomList",
                    villa_id,
                    json={},
                )
            )["list"]
        )

    async def sort_room_list(self, villa_id: int, room_list: List[RoomSort]) -> None:
        """房间列表排序

        参数:
            villa_id: 大别野 ID
            room_list: 期望的排序列表
        """
        await self._request(
            "POST",
            "sortRoomList",
            villa_id,
            json={
                "villa_id": villa_id,
                "room_list": [room.dict() for room in room_list],
            },
        )

    async def operate_member_to_role(
        self, villa_id: int, role_id: int, uid: int, is_add: bool
    ) -> None:
        """向身份组操作用户

        参数:
            villa_id: 大别野 ID
            role_id: 身份组 ID
            uid: 用户 ID
            is_add: 是否添加用户
        """
        await self._request(
            "POST",
            "operateMemberToRole",
            villa_id,
            json={"role_id": role_id, "uid": uid, "is_add": is_add},
        )

    async def create_member_role(
        self, villa_id: int, name: str, color: Color, permissions: List[Permission]
    ) -> int:
        """创建身份组

        参数:
            villa_id: 大别野 ID
            name: 身份组名称
            color: 身份组颜色
            permissions: 权限列表

        返回:
            int: 身份组 ID
        """
        return (
            await self._request(
                "POST",
                "createMemberRole",
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
        """编辑身份组

        参数:
            villa_id: 大别野 ID
            role_id: 身份组 ID
            name: 身份组名称
            color: 身份组颜色
            permissions: 权限列表
        """
        await self._request(
            "POST",
            "editMemberRole",
            villa_id,
            json={
                "id": role_id,
                "name": name,
                "color": str(color),
                "permissions": permissions,
            },
        )

    async def delete_member_role(self, villa_id: int, role_id: int) -> None:
        """删除身份组

        参数:
            villa_id: 大别野 ID
            role_id: 身份组 ID
        """
        await self._request(
            "POST",
            "deleteMemberRole",
            villa_id,
            json={"id": role_id},
        )

    async def get_member_role_info(
        self, villa_id: int, role_id: int
    ) -> MemberRoleDetail:
        """获取身份组

        参数:
            villa_id: 大别野 ID
            role_id: 身份组 ID

        返回:
            MemberRoleDetail: 身份组详情
        """
        return MemberRoleDetail.parse_obj(
            (
                await self._request(
                    "GET",
                    "getMemberRoleInfo",
                    villa_id,
                    json={"role_id": role_id},
                )
            )["role"]
        )

    async def get_villa_member_roles(self, villa_id: int) -> List[MemberRoleDetail]:
        """获取大别野下所有身份组

        参数:
            villa_id: 大别野 ID

        返回:
            List[MemberRoleDetail]: 身份组列表
        """
        return parse_obj_as(
            List[MemberRoleDetail],
            (
                await self._request(
                    "GET",
                    "getVillaMemberRoles",
                    villa_id,
                    json={},
                )
            )["list"],
        )

    async def get_all_emoticons(self) -> List[Emoticon]:
        """获取全量表情

        参数:
            villa_id: 参数说明

        返回:
            List[Emoticon]: 表情列表
        """
        return parse_obj_as(
            List[Emoticon],
            (
                await self._request(
                    "GET",
                    "getAllEmoticons",
                    None,
                    json={},
                )
            )["list"],
        )

    async def audit(
        self,
        villa_id: int,
        audit_content: str,
        pass_through: Optional[str] = None,
        room_id: Optional[int] = None,
        uid: Optional[int] = None,
    ) -> int:
        """审核

        审核用户配置内容是否合规，调用成功后会返回审核事件id(audit_id)。审核结果会通过回调接口异步通知。

        参数:
            villa_id: 大别野 ID
            audit_content: 待审核内容
            pass_through: 透传信息，该字段会在审核结果回调时携带给开发者，选填
            room_id: 房间 id，选填
            uid: 用户 id, 选填明

        返回:
            int: 审核事件 ID
        """
        return (
            await self._request(
                "POST",
                "audit",
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
        """获取鉴权请求头

        参数:
            villa_id: 大别野 ID，部分无需

        返回:
            Dict[str, str]: 请求头
        """
        return {
            "x-rpc-bot_id": self.bot_id,
            "x-rpc-bot_secret": self.bot_secret,
            "x-rpc-bot_villa_id": str(villa_id) if villa_id else "",
        }

    async def _request(
        self,
        method: Literal["GET", "POST"],
        api: str,
        villa_id: Optional[int],
        json: Dict[str, Any],
        **kwargs,
    ) -> Any:
        """请求 API

        参数:
            method: 请求方法
            api: API 名称
            villa_id: 大别野 ID
            json: JSON请求体

        异常:
            ActionFailed: 动作失败
            e: 其他请求异常

        返回:
            Any: 返回结果
        """
        logger.opt(colors=True).debug(
            f"<b><m>{self.bot_id}</m></b> | Calling API <y>{api}</y>"
        )
        try:
            resp = await self._client.request(
                method=method,
                url=api,
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

    async def _close_client(self) -> None:
        """关闭 HTTP Client"""
        await self._client.aclose()

    async def _handle_event(self, event: Event):
        """处理事件

        参数:
            event: 事件
        """
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
        """解析消息内容"""
        if quote := message["quote", 0]:
            quote = QuoteInfo(**quote.dict())

        if images_msg := (message["image"] or None):  # type: ignore
            images_msg: List[ImageSegment]
            images = [
                Image(
                    url=seg.url,
                    size=ImageSize(width=seg.width, height=seg.height)
                    if seg.width and seg.height
                    else None,
                    file_size=seg.file_size,
                )
                for seg in images_msg
            ]
        else:
            images = None
        if posts_msg := (message["post"] or None):  # type: ignore
            posts_msg: List[PostSegment]
            post_ids = [seg.post_id for seg in posts_msg]
        else:
            post_ids = None
        cal_len = lambda x: len(x.encode("utf-16")) // 2 - 1
        message_text = ""
        message_offset = 0
        entities: List[TextEntity] = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for seg in message:  # type: ignore
            try:
                if seg.type in ("quote", "image", "post"):
                    continue
                if isinstance(seg, TextSegment):
                    seg_text = seg.content
                    length = cal_len(seg_text)
                elif isinstance(seg, MentionAllSegment):
                    seg_text = f"@{seg.show_text} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=MentionedAll(show_text=seg.show_text),
                        )
                    )
                    mentioned.type = MentionType.ALL
                elif isinstance(seg, MentionRobotSegment):
                    seg_text = f"@{seg.bot_name} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=MentionedRobot(
                                bot_id=seg.bot_id, bot_name=seg.bot_name
                            ),
                        )
                    )
                    mentioned.user_id_list.append(seg.bot_id)
                elif isinstance(seg, MentionUserSegment):
                    # 需要调用API获取被@的用户的昵称
                    user = await self.get_member(villa_id=seg.villa_id, uid=seg.user_id)
                    seg_text = f"@{user.basic.nickname} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=MentionedUser(
                                user_id=str(user.basic.uid),
                                user_name=user.basic.nickname,
                            ),
                        )
                    )
                    mentioned.user_id_list.append(str(user.basic.uid))
                elif isinstance(seg, RoomLinkSegment):
                    # 需要调用API获取房间的名称
                    room = await self.get_room(
                        villa_id=seg.villa_id, room_id=seg.room_id
                    )
                    seg_text = f"#{room.room_name} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=VillaRoomLink(
                                villa_id=str(seg.villa_id),
                                room_id=str(seg.room_id),
                                room_name=room.room_name,
                            ),
                        )
                    )
                else:
                    seg: LinkSegment
                    seg_text = seg.show_text
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=Link(url=seg.url, show_text=seg.show_text),
                        )
                    )
                message_offset += length
                message_text += seg_text
            except Exception as e:
                logger.opt(exception=e).warning("error when parse message content")

        if not (mentioned.type == MentionType.ALL and mentioned.user_id_list):
            mentioned = None

        if not (message_text or entities):
            if images:
                if len(images) > 1:
                    logger.warning(
                        "Sending multiple images in one message will not be visible on the web side!"
                    )
                    content = TextMessageContent(text="\u200B", images=images)
                else:
                    content = ImageMessageContent(**images[0].dict())
            elif post_ids:
                if len(post_ids) > 1:
                    logger.opt(colors=True).warning(
                        f"Only support one post in one message, so use the last one <m>{post_ids[-1]}</m>!"
                    )
                content = PostMessageContent(post_id=post_ids[-1])
            else:
                raise ValueError("message content is empty")
        else:
            if images and message_text:
                logger.warning(
                    "When a message is accompanied by text and image, image will not visible on the web side!"
                )
            if post_ids and message_text:
                logger.warning(
                    "When a message is accompanied by text and post, post will not visible!"
                )
            content = TextMessageContent(
                text=message_text, entities=entities, images=images
            )

        return MessageContentInfo(
            content=content,
            mentionedInfo=mentioned,
            quote=quote,
        )

    def init_app(self, app: FastAPI):
        logger.opt(colors=True).info(f"Initializing Bot <m>{self.bot_id}</m>...")
        logger.opt(colors=True).debug(
            f"With Secret: <m>{self.bot_secret}</m> and Callback URL: <m>{self.callback_url}</m>"
        )
        app.post(self.callback_url, status_code=200)(handle_event)
        app.on_event("shutdown")(self._close_client)

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 13350,
        log_level: str = "INFO",
        **kwargs,
    ):
        """启动机器人.

        参数:
            host: HOST 地址. 默认为 "127.0.0.1".
            port: 端口号. 默认为 13350.
            log_level: 日志等级. 默认为 "INFO".
        """
        run_bots(bots=[self], host=host, port=port, log_level=log_level, **kwargs)


def run_bots(
    bots: List[Bot],
    host: str = "127.0.0.1",
    port: int = 13350,
    log_level: str = "INFO",
    **kwargs,
):
    """启动多个机器人.

    参数:
        bots: 机器人列表.
        host: HOST 地址. 默认为 "127.0.0.1".
        port: 端口号. 默认为 13350.
        log_level: 日志等级. 默认为 "INFO".
    """
    logger.configure(extra={"villa_log_level": log_level}, patcher=_log_patcher)
    logger.success("Starting Villa...")
    fastapi_kwargs = {
        k.lstrip("fastapi_"): v for k, v in kwargs.items() if k.startswith("fastapi_")
    }
    uvicorn_kwargs = {
        k.lstrip("uvicorn_"): v for k, v in kwargs.items() if k.startswith("uvicorn_")
    }
    app = get_app()
    for key, value in fastapi_kwargs.items():
        setattr(app, key, value)
    for bot in bots:
        bot.init_app(app)
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


async def handle_event(data: Dict[str, Any]) -> JSONResponse:
    """处理事件"""
    if not (payload_data := data.get("event", None)):
        logger.warning(f"Received invalid data: {escape_tag(str(data))}")
        return JSONResponse(
            status_code=400, content={"retcode": -1, "msg": "Invalid data"}
        )
    try:
        event = parse_obj_as(event_classes, pre_handle_event(payload_data))
        if (bot := get_bot(event.bot_id)) is None:
            raise ValueError(f"Bot {event.bot_id} not found")
        bot._bot_info = event.robot
        logger.opt(colors=True).success(
            f"<b><m>{bot.bot_id}</m></b> | <b><y>[{event.__class__.__name__}]</y></b>: {event.get_event_description()}"
        )
    except Exception as e:
        logger.opt(exception=e).warning(
            f"Failed to parse payload {escape_tag(str(payload_data))}"
        )
        return JSONResponse(
            status_code=400, content={"retcode": -1, "msg": "Invalid data"}
        )
    else:
        asyncio.create_task(bot._handle_event(event))
    return JSONResponse(status_code=200, content={"retcode": 0, "message": "success"})


async def run_handler(handler: EventHandler, event: Event):
    """运行事件处理器"""
    try:
        if asyncio.iscoroutinefunction(handler.func):
            await handler.func(event)
        else:
            await run_sync(handler.func)(event)
    except Exception as e:
        logger.opt(exception=e).error(
            f"Error when running {handler} for {event.__class__.__name__}"
        )


def on_startup(func: T_Func):
    """让函数在 APP 启动时运行

    参数:
        func: 无参函数
    """
    get_app().on_event("startup")(func)


def on_shutdown(func: T_Func):
    """让函数在 APP 终止前运行

    参数:
        func: 无参函数
    """
    get_app().on_event("shutdown")(func)
