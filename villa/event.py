from enum import IntEnum
import json
from typing import Any, Dict, Literal, Optional, Union

from .message import Message, MessageSegment
from .models import MessageContentInfoGet, Robot
from .store import get_bot
from .utils import escape_tag

from pydantic import BaseModel, root_validator


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

    robot: Robot
    """用户机器人访问凭证"""
    type: EventType
    """事件类型"""
    id: str
    """事件 id"""
    created_at: int
    """事件创建时间"""
    send_at: int
    """事件回调时间"""

    @property
    def bot_id(self) -> str:
        """机器人ID"""
        return self.robot.template.id

    def get_event_name(self) -> str:
        return f"<b><y>[{self.__class__.__name__}]</y></b>"

    def get_event_description(self) -> str:
        return escape_tag(str(self.dict()))


class JoinVillaEvent(Event):
    """新用户加入大别野事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###JoinVilla"""

    type: Literal[EventType.JoinVilla] = EventType.JoinVilla
    join_uid: int
    """用户ID"""
    join_user_nickname: str
    """用户昵称"""
    join_at: int
    """用户加入时间的时间戳"""

    @property
    def villa_id(self) -> int:
        """大别野ID"""
        return self.robot.villa_id

    def get_event_description(self) -> str:
        return escape_tag(
            f"User(nickname={self.join_user_nickname},"
            f"id={self.join_uid}) join Villa(id={self.villa_id})",
        )


class SendMessageEvent(Event):
    """用户@机器人发送消息事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###SendMessage"""

    type: Literal[EventType.SendMessage] = EventType.SendMessage
    content: MessageContentInfoGet
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

    message: Message
    """事件消息"""

    @property
    def villa_id(self) -> int:
        """大别野ID"""
        return self.robot.villa_id

    def get_event_description(self) -> str:
        return escape_tag(
            f"Message(id={self.msg_uid}) was sent from User(nickname={self.nickname},"
            f"id={self.from_user_id}) in Room(id={self.room_id}) of "
            f"Villa(id={self.villa_id}), content={repr(self.message)}",
        )

    @root_validator(pre=True)
    @classmethod
    def _(cls, data: Dict[str, Any]):
        if not data.get("content"):
            return data
        msg = Message()
        data["content"] = json.loads(data["content"])
        msg_content_info = data["content"]
        if quote := msg_content_info.get("quote"):
            msg.append(
                MessageSegment.quote(
                    message_id=quote["quoted_message_id"],
                    message_send_time=quote["quoted_message_send_time"],
                ),
            )

        content = msg_content_info["content"]
        text = content["text"]
        entities = content["entities"]
        if not entities:
            return Message(MessageSegment.plain_text(text))
        text = text.encode("utf-16")
        last_offset: int = 0
        last_length: int = 0
        for entity in entities:
            end_offset: int = last_offset + last_length
            offset: int = entity["offset"]
            length: int = entity["length"]
            entity_detail = entity["entity"]
            if offset != end_offset:
                msg.append(
                    MessageSegment.plain_text(
                        text[((end_offset + 1) * 2) : ((offset + 1) * 2)].decode(
                            "utf-16",
                        ),
                    ),
                )
            entity_text = text[(offset + 1) * 2 : (offset + length + 1) * 2].decode(
                "utf-16",
            )
            if entity_detail["type"] == "mentioned_robot":
                entity_detail["bot_name"] = entity_text.lstrip("@")[:-1]
                msg.append(
                    MessageSegment.mention_robot(
                        entity_detail["bot_id"],
                        entity_detail["bot_name"],
                    ),
                )
            elif entity_detail["type"] == "mentioned_user":
                entity_detail["user_name"] = entity_text.lstrip("@")[:-1]
                msg.append(
                    MessageSegment.mention_user(
                        int(entity_detail["user_id"]),
                        data["villa_id"],
                    ),
                )
            elif entity_detail["type"] == "mention_all":
                entity_detail["show_text"] = entity_text.lstrip("@")[:-1]
                msg.append(MessageSegment.mention_all(entity_detail["show_text"]))
            elif entity_detail["type"] == "villa_room_link":
                entity_detail["room_name"] = entity_text.lstrip("#")[:-1]
                msg.append(
                    MessageSegment.room_link(
                        int(entity_detail["villa_id"]),
                        int(entity_detail["room_id"]),
                    ),
                )
            else:
                entity_detail["show_text"] = entity_text
                msg.append(MessageSegment.link(entity_detail["url"], entity_text))
            last_offset = offset
            last_length = length
        end_offset = last_offset + last_length
        if last_text := text[(end_offset + 1) * 2 :].decode("utf-16"):
            msg.append(MessageSegment.plain_text(last_text))
        data["message"] = msg
        return data

    async def send(
        self,
        message: Union[str, MessageSegment, Message],
        mention_sender: bool = False,
        quote_message: bool = False,
    ) -> str:
        """对事件进行快速发送消息

        参数:
            message: 消息内容
            mention_sender: 是否@发送者. 默认为 False.
            quote_message: 是否引用事件消息. 默认为 False.

        异常:
            ValueError: 找不到 Bot 实例

        返回:
            str: 消息 ID
        """
        if (bot := get_bot(self.bot_id)) is None:
            raise ValueError(f"Bot {self.bot_id} not found. Cannot send message.")
        if isinstance(message, (str, MessageSegment)):
            message = Message(message)
        if mention_sender:
            message.insert(
                0,
                MessageSegment.mention_user(
                    self.from_user_id,
                    self.content.user.name,
                    self.villa_id,
                ),
            )
        if quote_message:
            message.append(MessageSegment.quote(self.msg_uid, self.send_at))
        return await bot.send(self.villa_id, self.room_id, message)


class CreateRobotEvent(Event):
    """大别野添加机器人实例事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###CreateRobot"""

    type: Literal[EventType.CreateRobot] = EventType.CreateRobot
    villa_id: int
    """大别野ID"""

    def get_event_description(self) -> str:
        return escape_tag(
            f"Bot(id={self.bot_id}) was added to Villa(id={self.villa_id})",
        )


class DeleteRobotEvent(Event):
    """大别野删除机器人实例事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###DeleteRobot"""

    type: Literal[EventType.DeleteRobot] = EventType.DeleteRobot
    villa_id: int
    """大别野ID"""

    def get_event_description(self) -> str:
        return escape_tag(
            f"Bot(id={self.bot_id}) was removed from Villa(id={self.villa_id})",
        )


class AddQuickEmoticonEvent(Event):
    """用户使用表情回复消息表态事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html#AddQuickEmoticon"""

    type: Literal[EventType.AddQuickEmoticon] = EventType.AddQuickEmoticon
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

    def get_event_description(self) -> str:
        return escape_tag(
            f"Emoticon(name={self.emoticon}, id={self.emoticon_id}) "
            f"was {'removed from' if self.is_cancel else 'added to'} "
            f"Message(id={self.msg_uid}) by User(id={self.uid}) in "
            f"Room(id=Villa(id={self.room_id}) of Villa(id={self.villa_id})",
        )

    async def send(
        self,
        message: Union[str, MessageSegment, Message],
        mention_sender: bool = False,
        quote_message: bool = False,
    ) -> str:
        """对事件进行快速发送消息

        参数:
            message: 消息内容
            mention_sender: 是否@发送者. 默认为 False.
            quote_message: 是否引用事件消息. 默认为 False.

        异常:
            ValueError: 找不到 Bot 实例

        返回:
            str: 消息 ID
        """
        if (bot := get_bot(self.bot_id)) is None:
            raise ValueError(f"Bot {self.bot_id} not found. Cannot send message.")
        if isinstance(message, (str, MessageSegment)):
            message = Message(message)
        if mention_sender:
            message.insert(
                0,
                MessageSegment.mention_user(self.uid, None, self.villa_id),
            )
        if quote_message:
            message.append(MessageSegment.quote(self.msg_uid, self.send_at))
        return await bot.send(self.villa_id, self.room_id, message)


class AuditCallbackEvent(Event):
    """审核结果回调事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html#AuditCallback"""

    type: Literal[EventType.AuditCallback] = EventType.AuditCallback
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

    def get_event_description(self) -> str:
        return escape_tag(
            f"Audit(id={self.audit_id},result={self.audit_result}) of "
            f"User(id={self.user_id}) in Room(id={self.room_id}) of "
            f"Villa(id={self.villa_id})",
        )


event_classes = Union[
    JoinVillaEvent,
    SendMessageEvent,
    CreateRobotEvent,
    DeleteRobotEvent,
    AddQuickEmoticonEvent,
    AuditCallbackEvent,
]


def pre_handle_event(payload: Dict[str, Any]):
    if (event_type := EventType._value2member_map_.get(payload["type"])) is None:
        raise ValueError(
            f"Unknown event type: {payload['type']} data={escape_tag(str(payload))}",
        )
    event_name = event_type.name
    if event_name not in payload["extend_data"]["EventData"]:
        raise ValueError("Cannot find event data for event type: {event_name}")
    payload |= payload["extend_data"]["EventData"][event_name]
    payload.pop("extend_data")
    return payload


__all__ = [
    "Event",
    "JoinVillaEvent",
    "SendMessageEvent",
    "CreateRobotEvent",
    "DeleteRobotEvent",
    "AddQuickEmoticonEvent",
    "AuditCallbackEvent",
]
