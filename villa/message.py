from abc import ABC
import re
from typing import Iterable, Iterator, List, Literal, Optional, overload, Tuple, Union
from typing_extensions import Self

from pydantic import BaseModel, Field, root_validator
from pydantic.utils import get_args  # type: ignore

MessageType = Literal[
    "text",
    "mention_user",
    "mention_all",
    "mention_robot",
    "room_link",
    "link",
    "image",
    "quote",
    "post",
    "preview_link",
    "badge",
]


class MessageSegment(ABC, BaseModel):
    type: MessageType
    """消息段基类"""

    @staticmethod
    def plain_text(text: str) -> "Text":
        return Text(content=text)

    @staticmethod
    def mention_robot(bot_id: str, bot_name: str) -> "MentionRobot":
        return MentionRobot(bot_id=bot_id, bot_name=bot_name)

    @staticmethod
    def mention_user(
        user_id: int,
        user_name: Optional[str] = None,
        villa_id: Optional[int] = None,
    ) -> "MentionUser":
        return MentionUser(user_id=user_id, user_name=user_name, villa_id=villa_id)

    @staticmethod
    def mention_all(show_text: str = "全体成员") -> "MentionAll":
        return MentionAll(show_text=show_text)

    @staticmethod
    def room_link(villa_id: int, room_id: int) -> "RoomLink":
        return RoomLink(villa_id=villa_id, room_id=room_id)

    @staticmethod
    def link(
        url: str,
        show_text: Optional[str] = None,
        requires_bot_access_token: bool = False,
    ) -> "Link":
        return Link(
            url=url,
            show_text=show_text or url,
            requires_bot_access_token=requires_bot_access_token,
        )

    @staticmethod
    def post(post_id: str) -> "Post":
        return Post(post_id=post_id)

    @staticmethod
    def image(
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
    ) -> "Image":
        return Image(url=url, width=width, height=height, file_size=file_size)

    @staticmethod
    def quote(message_id: str, message_send_time: int) -> "Quote":
        return Quote(
            quoted_message_id=message_id,
            quoted_message_send_time=message_send_time,
            original_message_id=message_id,
            original_message_send_time=message_send_time,
        )

    @staticmethod
    def preview_link(
        icon_url: str,
        image_url: str,
        is_internal_link: bool,
        title: str,
        content: str,
        url: str,
        source_name: str,
    ) -> "PreviewLink":
        return PreviewLink(
            icon_url=icon_url,
            image_url=image_url,
            is_internal_link=is_internal_link,
            title=title,
            content=content,
            url=url,
            source_name=source_name,
        )

    @staticmethod
    def badge(icon_url: str, text: str, url: str) -> "Badge":
        return Badge(icon_url=icon_url, text=text, url=url)

    def __add__(self, other: Union[str, "MessageSegment", "Message"]) -> "Message":
        if isinstance(other, str):
            return Message([self, MessageSegment.plain_text(other)])
        if isinstance(other, MessageSegment):
            return Message([self, other])
        if isinstance(other, Message):
            return Message([self, *other.__root__])
        raise TypeError(f"unsupported type: {type(other)}")

    def __radd__(self, other: Union[str, "MessageSegment", "Message"]) -> "Message":
        return self.__add__(other)

    def __iadd__(self, other: Union[str, "MessageSegment", "Message"]) -> "Message":
        return self.__add__(other)


class Text(MessageSegment):
    """文本消息段"""

    type: Literal["text"] = Field(default="text", repr=False)
    content: str


class MentionRobot(MessageSegment):
    """@机器人消息段"""

    type: Literal["mention_robot"] = Field(default="mention_robot", repr=False)
    bot_id: str
    bot_name: str


class MentionUser(MessageSegment):
    """@用户消息段"""

    type: Literal["mention_user"] = Field(default="mention_user", repr=False)
    user_id: int
    user_name: Optional[str] = None
    villa_id: Optional[int] = None

    @root_validator
    @classmethod
    def _(cls, values):
        if values.get("user_name") is None and values.get("villa_id") is None:
            raise ValueError("user_name和villa_id必须至少有一个不为None")
        return values


class MentionAll(MessageSegment):
    """@全体成员消息段"""

    type: Literal["mention_all"] = Field(default="mention_all", repr=False)
    show_text: str = "全体成员"


class RoomLink(MessageSegment):
    """房间链接消息段"""

    type: Literal["room_link"] = Field(default="room_link", repr=False)
    villa_id: int
    room_id: int


class Link(MessageSegment):
    """链接消息段"""

    type: Literal["link"] = Field(default="link", repr=False)
    url: str
    show_text: str
    requires_bot_access_token: bool


class Image(MessageSegment):
    """图片消息段"""

    type: Literal["image"] = Field(default="image", repr=False)
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None


class Quote(MessageSegment):
    """引用消息段"""

    type: Literal["quote"] = Field(default="quote", repr=False)
    quoted_message_id: str
    quoted_message_send_time: int
    original_message_id: str
    original_message_send_time: int


class Post(MessageSegment):
    """帖子消息段"""

    type: Literal["post"] = Field(default="post", repr=False)
    post_id: str


class PreviewLink(MessageSegment):
    """预览链接(卡片)消息段"""

    type: Literal["preview_link"] = Field(default="preview_link", repr=False)
    icon_url: str
    image_url: str
    is_internal_link: bool
    title: str
    content: str
    url: str
    source_name: str


class Badge(MessageSegment):
    """徽标消息段

    用于在消息下方显示徽标，不支持单独发送"""

    type: Literal["badge"] = Field(default="badge", repr=False)
    icon_url: str
    text: str
    url: str


class Message(BaseModel):
    __root__: List[MessageSegment] = Field(default_factory=list)

    def __init__(
        self,
        message: Union[
            str,
            MessageSegment,
            Iterable[MessageSegment],
            "Message",
            None,
        ] = None,
    ):
        """消息类

        参数:
            message: 消息内容. 默认为 None.

        异常:
            TypeError: 不支持该类型的消息
        """
        if message is None:
            message = []
        elif isinstance(message, str):
            message = Text(content=message)
        if isinstance(message, MessageSegment):
            message = [message]
        elif isinstance(message, Message):
            message = message.__root__
        elif not isinstance(message, Iterable):
            raise TypeError(f"unsupported type: {type(message)}")
        super().__init__(__root__=message)

    def plain_text(self, content: str) -> Self:
        """纯文本消息

        参数:
            content: 文本内容

        返回:
            Self: 消息对象

        用法:
            ```python
            message = Message().text("hello world")
            ```
        """
        self.__root__.append(Text(content=content))
        return self

    def mention_user(
        self,
        user_id: int,
        user_name: Optional[str] = None,
        villa_id: Optional[int] = None,
    ) -> Self:
        """提及(@at)消息

        参数:
            villa_id: 要提及的用户所在的大别野ID
            user_id: 要提及的用户ID

        返回:
            Self: 消息对象
        """
        self.__root__.append(
            MentionUser(user_id=user_id, user_name=user_name, villa_id=villa_id),
        )
        return self

    def mention_all(self) -> Self:
        """提及(@at)全体成员消息

        返回:
            Self: 消息对象
        """
        self.__root__.append(MentionAll())
        return self

    def mention_robot(self, bot_id: str, bot_name: str) -> Self:
        """提及(@at)机器人消息

        参数:
            bot_id: 机器人ID
            bot_name: 机器人名称

        返回:
            Self: 消息对象
        """
        self.__root__.append(MentionRobot(bot_id=bot_id, bot_name=bot_name))
        return self

    def room_link(self, villa_id: int, room_id: int) -> Self:
        """房间链接消息

        参数:
            villa_id: 大别野ID
            room_id: 房间ID

        返回:
            Self: 消息对象
        """
        self.__root__.append(RoomLink(villa_id=villa_id, room_id=room_id))
        return self

    def link(
        self,
        url: str,
        show_text: Optional[str] = None,
        requires_bot_access_token: bool = False,
    ) -> Self:
        """说明

        详细说明

        参数:
            url: 链接地址
            show_text: 链接显示的文本. 为 None 时与地址保持一致.
            requires_bot_access_token: 访问时是否需要带上含有用户信息的token.

        返回:
            Self: 返回说明
        """
        self.__root__.append(
            Link(
                url=url,
                show_text=show_text or url,
                requires_bot_access_token=requires_bot_access_token,
            ),
        )
        return self

    def image(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
    ) -> Self:
        """图片消息

        参数:
            url: 图片链接
            width: 图片宽度. 默认为 None.
            height: 图片高度. 默认为 None.
            file_size: 图片大小. 默认为 None.

        返回:
            Self: 消息对象
        """
        self.__root__.append(
            Image(url=url, width=width, height=height, file_size=file_size),
        )
        return self

    def quote(self, message_id: str, message_send_time: int) -> Self:
        """引用消息

        参数:
            message_id: 被引用的消息ID
            message_send_time: 被引用消息的发送时间

        返回:
            Self: 消息对象
        """
        self.__root__.append(
            Quote(
                quoted_message_id=message_id,
                quoted_message_send_time=message_send_time,
                original_message_id=message_id,
                original_message_send_time=message_send_time,
            ),
        )
        return self

    def post(self, post_id: str) -> Self:
        """帖子转发消息

        参数:
            post_id: 帖子ID

        返回:
            Self: 消息对象
        """
        self.__root__.append(Post(post_id=post_id))
        return self

    def preview_link(
        self,
        icon_url: str,
        image_url: str,
        is_internal_link: bool,
        title: str,
        content: str,
        url: str,
        source_name: str,
    ) -> Self:
        """预览链接(卡片)消息

        参数:
            icon_url: 参数说明
            image_url: 参数说明
            is_internal_link: 参数说明
            title: 参数说明
            content: 参数说明
            url: 参数说明
            source_name: 参数说明

        返回:
            Self: 返回说明
        """
        self.__root__.append(
            PreviewLink(
                icon_url=icon_url,
                image_url=image_url,
                is_internal_link=is_internal_link,
                title=title,
                content=content,
                url=url,
                source_name=source_name,
            ),
        )
        return self

    def badge(self, icon_url: str, text: str, url: str) -> Self:
        self.__root__.append(Badge(icon_url=icon_url, text=text, url=url))
        return self

    def insert(self, index: int, segment: Union[str, MessageSegment]):
        """在指定位置插入消息段

        参数:
            index: 插入位置
            segment: 消息段

        返回:
            Self: 消息对象
        """
        if isinstance(segment, str):
            segment = Text(content=segment)
        self.__root__.insert(index, segment)

    def append(self, segment: Union[str, MessageSegment]):
        """在消息末尾添加消息段

        参数:
            segment: 消息段

        返回:
            Self: 消息对象
        """
        if isinstance(segment, str):
            segment = Text(content=segment)
        self.__root__.append(segment)

    def get_plain_text(self) -> str:
        """获取纯文本消息内容"""
        return "".join(
            [segment.content for segment in self.__root__ if isinstance(segment, Text)],
        )

    def __contains__(self, item: str) -> bool:
        """检查消息的纯文本内容是否包含指定字符串"""
        return item in self.get_plain_text()

    def __len__(self) -> int:
        return len(self.__root__)

    def __add__(self, other: Union[str, "MessageSegment", "Message"]) -> "Message":
        result = self.copy(deep=True)
        if isinstance(other, str):
            other = Text(content=other)
        if isinstance(other, MessageSegment):
            result.__root__.append(other)
        elif isinstance(other, Message):
            result.__root__.extend(other.__root__)
        else:
            raise TypeError(f"unsupported type: {type(other)}")
        return result

    def __radd__(self, other: Union[str, "MessageSegment", "Message"]) -> "Message":
        return self.__add__(other)

    def __iadd__(self, other: Union[str, "MessageSegment", "Message"]) -> Self:
        if isinstance(other, str):
            other = Text(content=other)
        if isinstance(other, MessageSegment):
            self.__root__.append(other)
        elif isinstance(other, Message):
            self.__root__.extend(other.__root__)
        else:
            raise TypeError(f"unsupported type: {type(other)}")
        return self

    def __iter__(self) -> Iterator[MessageSegment]:
        return iter(self.__root__)

    def __repr__(self) -> str:
        return f"Message({repr(self.__root__)})"

    def has_segment_type(self, segment_type: MessageType) -> bool:
        """判断消息是否包含指定类型的消息段

        参数:
            segment_type: 消息段类型

        返回:
            bool: 是否包含指定类型的消息段
        """
        return any(seg.type == segment_type for seg in self.__root__)

    def startswith(self, text: Union[str, Tuple[str, ...]]) -> bool:
        """判断消息的纯文本部分是否以指定字符串开头

        参数:
            text: 指定字符串

        返回:
            bool: 是否以指定字符串开头
        """
        return self.get_plain_text().startswith(text)

    def endswith(self, text: Union[str, Tuple[str, ...]]) -> bool:
        """判断消息的纯文本部分是否以指定字符串结尾

        参数:
            text: 指定字符串

        返回:
            bool: 是否以指定字符串结尾
        """
        return self.get_plain_text().endswith(text)

    def match(self, pattern: Union[str, re.Pattern]) -> Optional[re.Match]:
        """使用正则表达式匹配消息的纯文本部分

        参数:
            pattern: 正则表达式

        返回:
            Optional[re.Match]: 匹配结果
        """
        return re.match(pattern, self.get_plain_text())

    def search(self, pattern: Union[str, re.Pattern]) -> Optional[re.Match]:
        """使用正则表达式搜索消息的纯文本部分

        参数:
            pattern: 正则表达式

        返回:
            Optional[re.Match]: 匹配结果
        """
        return re.search(pattern, self.get_plain_text())

    @overload
    def __getitem__(self, __args: int) -> MessageSegment:
        """
        参数:
            __args: 索引

        返回:
            MessageSegment: 第 `__args` 个消息段
        """
        ...

    @overload
    def __getitem__(self, __args: slice) -> "Message":
        """
        参数:
            __args: 切片

        返回:
            Message: 消息切片 `__args`
        """
        ...

    @overload
    def __getitem__(self, __args: MessageType) -> "Message":
        """
        参数:
            __args: 消息类型

        返回:
            Message: 消息段类型为 `__args` 的消息
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[MessageType, slice]) -> "Message":
        """
        参数:
            __args: 消息段类型, 切片

        返回:
            Message: 消息段类型为 `__args` 的消息切片
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[Literal["text"], int]) -> Optional[Text]:
        """
        参数:
            __args: text消息段

        返回:
            Text: 消息段类型为text的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(
        self,
        __args: Tuple[Literal["mention_user"], int],
    ) -> Optional[MentionUser]:
        """
        参数:
            __args: mention_user消息段

        返回:
            MentionUser: 消息段类型为mention_user的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(
        self,
        __args: Tuple[Literal["mention_all"], int],
    ) -> Optional[MentionAll]:
        """
        参数:
            __args: mention_all消息段

        返回:
            MentionAll: 消息段类型为mention_all的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(
        self,
        __args: Tuple[Literal["mention_robot"], int],
    ) -> Optional[MentionRobot]:
        """
        参数:
            __args: mention_robot消息段

        返回:
            MentionRobot: 消息段类型为mention_robot的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(
        self,
        __args: Tuple[Literal["room_link"], int],
    ) -> Optional[RoomLink]:
        """
        参数:
            __args: room_link消息段

        返回:
            RoomLink: 消息段类型为room_link的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[Literal["link"], int]) -> Optional[Link]:
        """
        参数:
            __args: link消息段

        返回:
            Link: 消息段类型为link的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[Literal["image"], int]) -> Optional[Image]:
        """
        参数:
            __args: image消息段

        返回:
            Image: 消息段类型为image的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[Literal["quote"], int]) -> Optional[Quote]:
        """
        参数:
            __args: quote消息段

        返回:
            Quote: 消息段类型为quote的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[Literal["post"], int]) -> Optional[Post]:
        """
        参数:
            __args: post消息段

        返回:
            Post: 消息段类型为post的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(
        self,
        __args: Tuple[Literal["preview_link"], int],
    ) -> Optional[PreviewLink]:
        """
        参数:
            __args: preview_link消息段

        返回:
            PreviewLink: 消息段类型为preview_link的第 `__args[1]` 个消息段
        """
        ...

    @overload
    def __getitem__(self, __args: Tuple[Literal["badge"], int]) -> Optional[Badge]:
        """
        参数:
            __args: badge消息段

        返回:
            Badge: 消息段类型为badge的第 `__args[1]` 个消息段
        """
        ...

    def __getitem__(
        self,
        args: Union[int, slice, MessageType, Tuple[MessageType, Union[int, slice]]],
    ) -> Union[MessageSegment, "Message", None]:
        arg1, arg2 = args if isinstance(args, tuple) else (args, None)
        if isinstance(arg1, int) and arg2 is None:
            return self.__root__.__getitem__(arg1)
        if isinstance(arg1, slice) and arg2 is None:
            return Message(self.__root__.__getitem__(arg1))
        if isinstance(arg1, str) and arg1 in get_args(MessageType):  # type: ignore
            if arg2 is None:
                return Message([seg for seg in self.__root__ if seg.type == arg1])
            if isinstance(arg2, int):
                try:
                    return [seg for seg in self.__root__ if seg.type == arg1][arg2]
                except IndexError:
                    return None
            elif isinstance(arg2, slice):
                return Message([seg for seg in self.__root__ if seg.type == arg1][arg2])
            else:
                raise ValueError("Incorrect arguments to slice")
        else:
            raise ValueError("Incorrect arguments to slice")
