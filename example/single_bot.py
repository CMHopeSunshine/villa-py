from villa import Bot

bot = Bot(
    bot_id="your_bot_id",  # 你的bot_id
    bot_secret="your_bot_secret",  # 你的bot_secret
    callback_url="your_callback_url_endpoint",  # 你的bot的回调地址
    api_timeout=10,  # api超时时间，单位秒
    wait_util_complete=False,  # 是否等待处理函数全部完成后再返回响应，默认为False
)
# 初始化Bot

if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350, log_level="DEBUG")
    # 使用fastapi+uvicorn来启动Bot
    # host: host地址
    # port: 端口，要和你的回调地址对上
    # log_level: 日志等级
