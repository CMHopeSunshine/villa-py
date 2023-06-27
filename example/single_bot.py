from villa import Bot

bot = Bot(
    bot_id="your_bot_id",
    bot_secret="your_bot_secret",
    callback_url="your_callback_url_endpoint",
)
# 初始化Bot，填写你的bot_id、密钥以及回调地址

if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350, log_level="DEBUG")
    # 使用fastapi+uvicorn来启动Bot
    # host: host地址
    # port: 端口，要和你的回调地址对上
    # log_level: 日志等级
