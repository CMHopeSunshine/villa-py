from villa import Bot
from villa.event import SendMessageEvent
from villa.message import Message, MessageSegment

bot = Bot(
    bot_id="your_bot_id",
    bot_secret="your_bot_secret",
    callback_url="your_callback_url_endpoint",
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
    msg = MessageSegment.plain_text("开头文字")  # 纯文本
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
    msg += MessageSegment.badge(
        "https://upload-bbs.mihoyo.com/vila_bot/bbs_origin_badge.png",
        "徽标",
        "https://mihoyo.com",
    )  # 消息下方带徽标
    msg += MessageSegment.preview_link(
        icon_url="https://www.bilibili.com/favicon.ico",
        image_url="https://i2.hdslb.com/bfs/archive/21b82856df6b8a2ae759dddac66e2c79d41fe6bc.jpg@672w_378h_1c_!web-home-common-cover.avif",
        is_internal_link=False,
        title="崩坏3第一偶像爱酱",
        content="「海的女儿」——《崩坏3》S级律者角色「死生之律者」宣传PV",
        url="https://www.bilibili.com/video/BV1Mh4y1M79t?spm_id_from=333.1007.tianma.2-2-5.click",
        source_name="哔哩哔哩",
    )  # 预览链接(卡片)

    # 也可以用 Message 进行链式调用
    msg = (
        Message("开头文字")  # 纯文本
        .quote(event.msg_uid, event.send_at)  # 引用消息
        .room_link(event.villa_id, event.room_id)  # 房间链接
        .mention_user(event.villa_id, event.from_user_id)  # @用户
        .mention_all()  # @全体成员
        .image("https://www.miyoushe.com/_nuxt/img/miHoYo_Game.2457753.png")  # 图片
        .link("https://www.miyoushe.com/")  # 链接
        .badge(
            "https://upload-bbs.mihoyo.com/vila_bot/bbs_origin_badge.png",
            "徽标",
            "https://mihoyo.com",
        )  # 消息下方带徽标
        .plain_text("结尾文字")  # 纯文本
    )

    # 可以转发米游社社区中的帖子
    msg = MessageSegment.post("https://www.miyoushe.com/ys/article/40391314")

    # 注意：
    # 帖子只能单独发送，和其他消息段时将被忽略
    # 如果在单次消息内，同时发送多张图片，或者和其他消息段拼接，那么图片将会在web端看不见，所以不建议这么做

    # 发送消息
    await event.send(msg)
    # 或者
    await bot.send(villa_id=event.villa_id, room_id=event.room_id, message=msg)


if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350, log_level="DEBUG")
