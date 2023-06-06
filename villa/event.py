import json
from enum import IntEnum
from typing import Any, Dict, Type, Union, Optional

from pydantic import Extra, BaseModel, validator

from .store import _bots
from .models import MessageContentInfo
from .message import Message, MessageSegment


class EventType(IntEnum):
    """事件类型"""

    JoinVilla = 1
    SendMessage = 2
    CreateRobot = 3
    DeleteRobot = 4
    AddQuickEmoticon = 5
    AuditCallback = 6


class AuditResult(IntEnum):
    """审核结果类型"""

    Compatibility = 0
    """兼容"""
    Pass = 1
    """通过"""
    Reject = 2
    """驳回"""


class Event(BaseModel):
    """Villa 事件基类"""

    __type__: EventType

    class Config:
        extra = Extra.allow


class JoinVillaEvent(Event):
    """新用户加入大别野事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###JoinVilla"""

    __type__ = EventType.JoinVilla
    join_uid: int
    """用户ID"""
    join_user_nickname: str
    """用户昵称"""
    join_at: int
    """用户加入时间的时间戳"""


class SendMessageEvent(Event):
    """用户@机器人发送消息事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###SendMessage"""

    __type__ = EventType.SendMessage
    content: MessageContentInfo
    """消息内容"""
    from_user_id: int
    """发送者ID"""
    send_at: int
    """发送时间的时间戳"""
    room_id: int
    """房间ID"""
    object_name: int
    """目前只支持文本类型消息"""
    nickname: str
    """用户昵称"""
    msg_uid: str
    """消息ID"""
    bot_msg_id: Optional[str]
    """如果被回复的消息从属于机器人，则该字段不为空字符串"""

    villa_id: int
    """大别野ID"""
    bot_id: str
    """机器人ID"""

    @validator("content", pre=True)
    def _content_str_to_dict(cls, v: Any):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @property
    def message(self) -> Message:
        if not hasattr(self, "_message"):
            setattr(self, "_message", Message._parse(self.content, self.villa_id))
        return getattr(self, "_message")

    async def send(
        self,
        message: Union[str, MessageSegment, Message],
        mention_sender: bool = False,
        quote_message: bool = False,
    ) -> str:
        """回复消息"""
        if not (bot := _bots.get(self.bot_id)):
            raise ValueError("bot not found")
        if isinstance(message, (str, MessageSegment)):
            message = Message(message)
        if mention_sender:
            message.insert(
                0, MessageSegment.mention_user(self.from_user_id, self.villa_id)
            )
        if quote_message:
            message.append(MessageSegment.quote(self.msg_uid, self.send_at))
        return await bot.send(self.villa_id, self.room_id, message)


class CreateRobotEvent(Event):
    """大别野添加机器人实例事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###CreateRobot"""

    __type__ = EventType.CreateRobot
    villa_id: int
    """大别野ID"""


class DeleteRobotEvent(Event):
    """大别野删除机器人实例事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###DeleteRobot"""

    __type__ = EventType.DeleteRobot
    villa_id: int
    """大别野ID"""


class AddQuickEmoticonEvent(Event):
    """用户使用表情回复消息表态事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html#AddQuickEmoticon"""

    __type__ = EventType.AddQuickEmoticon
    villa_id: int
    """大别野ID"""
    room_id: int
    """房间ID"""
    uid: int
    """发送表情的用户ID"""
    emoticon_id: int
    """表情ID"""
    emoticon: str
    """表情内容"""
    msg_uid: str
    """被回复的消息 id"""
    bot_msg_id: Optional[str]
    """如果被回复的消息从属于机器人，则该字段不为空字符串"""
    is_cancel: bool = False
    """是否是取消表情"""


class AuditCallbackEvent(Event):
    """审核结果回调事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html#AuditCallback"""

    __type__ = EventType.AuditCallback
    audit_id: str
    """审核事件 id"""
    bot_tpl_id: str
    """机器人 id"""
    villa_id: int
    """大别野 ID"""
    room_id: int
    """房间 id（和审核接口调用方传入的值一致）"""
    user_id: int
    """用户 id（和审核接口调用方传入的值一致）"""
    pass_through: str
    """透传数据（和审核接口调用方传入的值一致）"""
    audit_result: AuditResult
    """审核结果"""


event_classes: Dict[int, Type[Event]] = {
    EventType.JoinVilla.value: JoinVillaEvent,
    EventType.SendMessage.value: SendMessageEvent,
    EventType.CreateRobot.value: CreateRobotEvent,
    EventType.DeleteRobot.value: DeleteRobotEvent,
    EventType.AddQuickEmoticon.value: AddQuickEmoticonEvent,
    EventType.AuditCallback.value: AuditCallbackEvent,
}


__all__ = [
    "Event",
    "JoinVillaEvent",
    "SendMessageEvent",
    "CreateRobotEvent",
    "DeleteRobotEvent",
    "AddQuickEmoticonEvent",
    "AuditCallbackEvent",
]
