from villa import Bot, run_bots
from villa.event import SendMessageEvent

bot_1 = Bot(
    bot_id="your_bot_id_1",
    bot_secret="your_bot_secret_1",
    pub_key="-----BEGIN PUBLIC KEY-----\nyour_pub_key_1\n-----END PUBLIC KEY-----\n",
    callback_url="your_callback_url_endpoint_1",
)
bot_2 = Bot(
    bot_id="your_bot_id_2",
    bot_secret="your_bot_secret_2",
    pub_key="-----BEGIN PUBLIC KEY-----\nyour_pub_key_2\n-----END PUBLIC KEY-----\n",
    callback_url="your_callback_url_endpoint_2",
)
# 初始化多个Bot


@bot_1.on_message()
async def bot_1_handler(event: SendMessageEvent):
    """只属于 bot_1 的消息处理函数"""
    ...


@bot_2.on_message()
async def bot_2_handler(event: SendMessageEvent):
    """只属于 bot_2 的消息处理函数"""
    ...


@bot_1.on_message()
@bot_2.on_message()
async def bot_1_and_2_handler(event: SendMessageEvent):
    """同时属于 bot_1 和 bot_2 的消息处理函数"""
    ...


if __name__ == "__main__":
    run_bots(bots=[bot_1, bot_2], host="127.0.0.1", port=13350, log_level="DEBUG")
    # 使用run_bots来启动多个Bot
