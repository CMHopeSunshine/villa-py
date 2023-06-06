from villa import Bot
from villa.event import SendMessageEvent
from villa.message import Message, MessageSegment

bot = Bot(
    bot_id="your_bot_id", bot_secret="your_bot_secret", callback_url="your_callback_url"
)


@bot.on_keyword("hello")
async def keyword_handler(event: SendMessageEvent):
    await event.send("world!")  # 对事件进行快捷回复
    await event.send("world!", quote_message=True)  # 并对事件进行引用回复
    await event.send("world!", mention_sender=True)  # 并@消息发送者


@bot.on_keyword("你好")
async def keyword_handler2(event: SendMessageEvent):
    # 各种消息段可以通过 + 进行拼接
    msg = (
        MessageSegment.image(
            "https://www.miyoushe.com/_nuxt/img/miHoYo_Game.2457753.png"
        )
        + MessageSegment.mention_all()
    )

    # 也可以通过 += 进行拼接
    msg = MessageSegment.text("开头文字")  # 纯文本
    msg += MessageSegment.quote(event.msg_uid, event.send_at)  # 引用消息
    msg += MessageSegment.room_link(
        villa_id=event.villa_id, room_id=event.room_id
    )  # 房间链接
    msg += MessageSegment.mention_user(event.villa_id, event.from_user_id)  # @用户
    msg += MessageSegment.mention_all()  # @全体成员
    msg += MessageSegment.image(
        "https://www.miyoushe.com/_nuxt/img/miHoYo_Game.2457753.png"
    )  # 图片
    msg += MessageSegment.link("https://www.miyoushe.com/")  # 链接

    # 也可以用 Message 进行链式调用
    msg = (
        Message("开头文字")  # 纯文本
        .quote(event.msg_uid, event.send_at)  # 引用消息
        .room_link(event.villa_id, event.room_id)  # 房间链接
        .mention_user(event.villa_id, event.from_user_id)  # @用户
        .mention_all()  # @全体成员
        .image("https://www.miyoushe.com/_nuxt/img/miHoYo_Game.2457753.png")  # 图片
        .link("https://www.miyoushe.com/")  # 链接
        .text("结尾文字")  # 纯文本
    )

    # 发送消息
    await event.send(msg)
    # 或者
    await bot.send(villa_id=event.villa_id, room_id=event.room_id, message=msg)


if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350, log_level="DEBUG")
