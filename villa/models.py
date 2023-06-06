import sys
import json
import inspect
from enum import Enum, IntEnum
from typing import Any, List, Union, Literal, Optional

from pydantic import Field, BaseModel, validator, root_validator


class ApiResponse(BaseModel):
    retcode: int
    message: str
    data: Any


class BotAuth(BaseModel):
    bot_id: str
    bot_secret: str


# http事件回调部分
# see https://webstatic.mihoyo.com/vila/bot/doc/callback.html
class RobotCommand(BaseModel):
    name: str
    desc: str


class RobotTemplate(BaseModel):
    id: str
    name: str
    desc: str
    icon: str
    commands: Optional[List[RobotCommand]] = None


class Robot(BaseModel):
    villa_id: int
    template: RobotTemplate


class Payload(BaseModel):
    robot: Robot
    type: int
    id: str
    created_at: int
    send_at: int
    extend_data: dict

    @root_validator(pre=True)
    def _add_villa_id_to_extend_data(cls, values: dict):
        """把villa_id和bot_id添加到extend_data中，方便使用"""
        if values.get("type") == 2 and "SendMessage" in values.get(
            "extend_data", {}
        ).get("EventData", {}):
            if (
                "villa_id" in values.get("robot", {})
                and "villa_id" not in values["extend_data"]["EventData"]["SendMessage"]
            ):
                values["extend_data"]["EventData"]["SendMessage"]["villa_id"] = values[
                    "robot"
                ]["villa_id"]
            if (
                "id" in values.get("robot", {}).get("template", {})
                and "bot_id" not in values["extend_data"]["EventData"]["SendMessage"]
            ):
                values["extend_data"]["EventData"]["SendMessage"]["bot_id"] = values[
                    "robot"
                ]["template"]["id"]
        return values


## 鉴权部分
## see https://webstatic.mihoyo.com/vila/bot/doc/auth_api/
class BotMemberAccessInfo(BaseModel):
    uid: int
    villa_id: int
    member_access_token: str
    bot_tpl_id: str


class CheckMemberBotAccessTokenReturn(BaseModel):
    access_info: BotMemberAccessInfo
    member: "Member"


# 大别野部分
# see https://webstatic.mihoyo.com/vila/bot/doc/villa_api/
class Villa(BaseModel):
    villa_id: int
    name: str
    villa_avatar_url: str
    onwer_uid: int
    is_official: bool
    introduce: str
    category_id: int
    tags: List[str]


# 用户部分
# see https://webstatic.mihoyo.com/vila/bot/doc/member_api/
class MemberBasic(BaseModel):
    uid: int
    nickname: str
    introduce: str
    avatar: int
    avatar_url: str


class Member(BaseModel):
    basic: MemberBasic
    role_id_list: List[int]
    joined_at: int
    role_list: List["MemberRole"]


class MemberListReturn(BaseModel):
    list: List[Member]
    next_offset: int


# 消息部分
# see https://webstatic.mihoyo.com/vila/bot/doc/message_api/
class MentionType(IntEnum):
    ALL = 1
    PART = 2

    def __repr__(self) -> str:
        return self.name


class MentionedRobot(BaseModel):
    type: Literal["mentioned_robot"] = "mentioned_robot"
    bot_id: str


class MentionedUser(BaseModel):
    type: Literal["mentioned_user"] = "mentioned_user"
    user_id: str


class MentionedAll(BaseModel):
    type: Literal["mention_all"] = "mention_all"


class VillaRoomLink(BaseModel):
    type: Literal["villa_room_link"] = "villa_room_link"
    villa_id: str
    room_id: str


class Link(BaseModel):
    type: Literal["link"] = "link"
    url: str


class TextEntity(BaseModel):
    offset: int
    length: int
    entity: Union[MentionedRobot, MentionedUser, MentionedAll, VillaRoomLink, Link]


class ImageSize(BaseModel):
    width: int
    height: int


class Image(BaseModel):
    url: str
    size: Optional[ImageSize] = None
    file_size: Optional[int] = None


class MessageContent(BaseModel):
    text: str
    entities: List[TextEntity] = Field(default_factory=list)
    images: Optional[List[Image]] = None


class MentionedInfo(BaseModel):
    type: MentionType
    user_id_list: List[str] = Field(default_factory=list, alias="userIdList")


class QuoteInfo(BaseModel):
    quoted_message_id: str
    quoted_message_send_time: int
    original_message_id: str
    original_message_send_time: int


class User(BaseModel):
    portrait_uri: str = Field(alias="portraitUri")
    extra: dict
    name: str
    alias: str
    id: str
    portrait: str

    @validator("extra", pre=True)
    def extra_str_to_dict(cls, v: Any):
        if isinstance(v, str):
            return json.loads(v)
        return v


class Trace(BaseModel):
    visual_room_version: str
    app_version: str
    action_type: int
    bot_msg_id: str
    client: str
    rong_sdk_version: str


class MessageContentInfo(BaseModel):
    content: MessageContent
    mentioned_info: Optional[MentionedInfo] = Field(None, alias="mentionedInfo")
    quote: Optional[QuoteInfo] = None
    user: Optional[User] = None
    trace: Optional[Trace] = None


# 房间部分
# see https://webstatic.mihoyo.com/vila/bot/doc/room_api/
class Room(BaseModel):
    room_id: int
    room_name: str
    room_type: "RoomType"
    group_id: int
    room_default_notify_type: "RoomDefaultNotifyType"
    send_msg_auth_range: "SendMsgAuthRange"


class RoomType(str, Enum):
    CHAT = "BOT_PLATFORM_ROOM_TYPE_CHAT_ROOM"
    POST = "BOT_PLATFORM_ROOM_TYPE_POST_ROOM"
    SCENE = "BOT_PLATFORM_ROOM_TYPE_SCENE_ROOM"
    INVALID = "BOT_PLATFORM_ROOM_TYPE_INVALID"

    def __repr__(self) -> str:
        return self.name


class RoomDefaultNotifyType(str, Enum):
    NOTIFY = "BOT_PLATFORM_DEFAULT_NOTIFY_TYPE_NOTIFY"
    IGNORE = "BOT_PLATFORM_DEFAULT_NOTIFY_TYPE_IGNORE"
    INVALID = "BOT_PLATFORM_DEFAULT_NOTIFY_TYPE_INVALID"

    def __repr__(self) -> str:
        return self.name


class SendMsgAuthRange(BaseModel):
    is_all_send_msg: bool
    roles: List[int]


class GroupRoom(BaseModel):
    group_id: int
    group_name: str
    room_list: "ListRoom"


class ListRoomType(IntEnum):
    CHAT = 1
    POST = 2
    SCENE = 3

    def __repr__(self) -> str:
        return self.name


class CreateRoomType(IntEnum):
    CHAT = 1
    POST = 2
    SCENE = 3

    def __repr__(self) -> str:
        return self.name


class CreateRoomDefaultNotifyType(IntEnum):
    NOTIFY = 1
    IGNORE = 2

    def __repr__(self) -> str:
        return self.name


class ListRoom(BaseModel):
    room_id: int
    room_name: str
    room_type: ListRoomType
    group_id: int


class Group(BaseModel):
    group_id: int
    group_name: str


class RoomSort(BaseModel):
    room_id: int
    group_id: int


# 身份组部分
# see https://webstatic.mihoyo.com/vila/bot/doc/role_api/
class MemberRole(BaseModel):
    id: int
    name: str
    villa_id: int
    color: str
    web_color: str
    permissions: Optional[List["Permission"]] = None
    role_type: "RoleType"


class PermissionDetail(BaseModel):
    key: str
    name: str
    describe: str


class MemberRoleDetail(BaseModel):
    id: int
    name: str
    color: str
    villa_id: int
    role_type: "RoleType"
    member_num: int
    permissions: Optional[List[PermissionDetail]] = None


class RoleType(str, Enum):
    ALL_MEMBER = "MEMBER_ROLE_TYPE_ALL_MEMBER"
    ADMIN = "MEMBER_ROLE_TYPE_ADMIN"
    OWNER = "MEMBER_ROLE_TYPE_OWNER"
    CUSTOM = "MEMBER_ROLE_TYPE_CUSTOM"
    UNKNOWN = "MEMBER_ROLE_TYPE_UNKNOWN"

    def __repr__(self) -> str:
        return self.name


class Permission(str, Enum):
    MENTION_ALL = "mention_all"
    RECALL_MESSAGE = "recall_message"
    PIN_MESSAGE = "pin_message"
    MANAGE_MEMBER_ROLE = "manage_member_role"
    EDIT_VILLA_INFO = "edit_villa_info"
    MANAGE_GROUP_AND_ROOM = "manage_group_and_room"
    VILLA_SILENCE = "villa_silence"
    BLACK_OUT = "black_out"
    HANDLE_APPLY = "handle_apply"
    MANAGE_CHAT_ROOM = "manage_chat_room"
    VIEW_DATA_BOARD = "view_data_board"
    MANAGE_CUSTOM_EVENT = "manage_custom_event"
    LIVE_ROOM_ORDER = "live_room_order"
    MANAGE_SPOTLIGHT_COLLECTION = "manage_spotlight_collection"

    def __repr__(self) -> str:
        return self.name


class Color(str, Enum):
    GREY = "#6173AB"
    PINK = "#F485D8"
    RED = "#F47884"
    ORANGE = "#FFA54B"
    GREEN = "#7ED321"
    BLUE = "#59A1EA"
    PURPLE = "#977EE1"


# 表态表情部分
# see https://webstatic.mihoyo.com/vila/bot/doc/emoticon_api/
class Emoticon(BaseModel):
    emoticon_id: int
    describe_text: str
    icon: str


for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and issubclass(obj, BaseModel):
        obj.update_forward_refs()


__all__ = [
    "ApiResponse",
    "BotAuth",
    "RobotCommand",
    "RobotTemplate",
    "Robot",
    "Payload",
    "BotMemberAccessInfo",
    "CheckMemberBotAccessTokenReturn",
    "Villa",
    "MemberBasic",
    "Member",
    "MemberListReturn",
    "MentionType",
    "MentionedRobot",
    "MentionedUser",
    "MentionedAll",
    "VillaRoomLink",
    "Link",
    "TextEntity",
    "MessageContent",
    "MentionedInfo",
    "QuoteInfo",
    "User",
    "Trace",
    "ImageSize",
    "Image",
    "MessageContentInfo",
    "Room",
    "RoomType",
    "RoomDefaultNotifyType",
    "SendMsgAuthRange",
    "GroupRoom",
    "ListRoomType",
    "CreateRoomType",
    "CreateRoomDefaultNotifyType",
    "ListRoom",
    "Group",
    "RoomSort",
    "MemberRole",
    "PermissionDetail",
    "MemberRoleDetail",
    "RoleType",
    "Permission",
    "Color",
    "Emoticon",
]
