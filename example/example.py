from villa import Bot
from villa.event import SendMessageEvent

bot = Bot(
    bot_id="your_bot_id",
    bot_secret="your_bot_secret",
    pub_key="......",
    callback_url="your_callback_url",
)
# 初始化Bot，填写你的bot_id、密钥以及回调地址


@bot.on_keyword("hello")
async def hello_handler(event: SendMessageEvent):
    await event.send("world!")
    # 一个简单的处理函数，向你的Bot发送包含`hello`的消息时，它将会回复你`world`！


@bot.on_startswith("你好")
async def hello_handler_cn(event: SendMessageEvent):
    await event.send("世界！")
    # 同样，向你的Bot发送以`你好`开头的消息时，它将会回复你`你好呀！`


if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350)
    # 启动bot，注意，port端口号要和你的回调地址对上
