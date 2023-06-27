"""
使用vercel的serverless进行部署的示例
vercel支持FastAPI的serverless部署，只需要暴露fastapi的app实例
这里仅给出主体代码，具体部署方法请参考vercel官方文档
"""
from villa import Bot
from villa.store import get_app
from villa.event import SendMessageEvent

bot = Bot(
    bot_id="your_bot_id",
    bot_secret="your_bot_secret",
    callback_url="your_callback_url_endpoint",
)
# 初始化Bot，填写你的bot_id、密钥以及回调地址


@bot.on_keyword("hello")
async def hello_handler(event: SendMessageEvent):
    await event.send("world!(send by serverless)")
    # 一个简单的关键词回复处理函数


app = get_app()
# 获取fastapi的app实例

bot.init_app(app)
# 将bot注册到app中
