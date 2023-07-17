<div align="center">

# Villa

_✨ 米游社大别野Bot Python SDK ✨_

<a href="https://cdn.jsdelivr.net/gh/CMHopeSunshine/villa-py@master/LICENSE">
    <img src="https://img.shields.io/github/license/CMHopeSunshine/villa-py" alt="license">
</a>
<img src="https://img.shields.io/pypi/v/villa" alt="version">
<img src="https://img.shields.io/badge/Python-3.8+-yellow" alt="python">
<a href="https://pypi.python.org/pypi/villa">
  <img src="https://img.shields.io/pypi/dm/villa" alt="pypi download">
</a>
<a href="https://wakatime.com/badge/user/eed3f89c-5d65-46e6-ab19-78dcc4b62b3f/project/d3b88a99-17c2-4c98-bbc2-c1949ce7c078">
  <img src="https://wakatime.com/badge/user/eed3f89c-5d65-46e6-ab19-78dcc4b62b3f/project/d3b88a99-17c2-4c98-bbc2-c1949ce7c078.svg" alt="wakatime">
</a>
<a href="https://github.com/astral-sh/ruff">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>

</div>

## 特性

- 基于`FastAPI`和`Pydantic`，异步优先、快速、高性能！
- 完整的类型注解支持，便于开发。
- 便捷的消息构造和发送方法。
- 完整的消息段和API支持。
- `Serverless`云函数支持。
- More ~~想不出来了~~

## 安装

- 使用 pip: `pip install villa`
- 使用 poetry: `poetry add villa`
- 使用 pdm: `pdm add villa`

## 快速开始

你需要一个[米游社大别野](https://dby.miyoushe.com/chat)的 Bot，可前往大别野[「机器人开发者社区」](https://dby.miyoushe.com/chat/463/20020)(ID: `OpenVilla`)申请，取得`bot_id`、`bot_secret`和`pub_key`。

```python
from villa import Bot
from villa.event import SendMessageEvent

bot = Bot(
    bot_id="your_bot_id",
    bot_secret="your_bot_secret",
    pub_key="-----BEGIN PUBLIC KEY-----\nyour_pub_key\n-----END PUBLIC KEY-----\n",
    callback_url="your_callback_url_endpoint",
)
# 初始化Bot，填写你的bot_id、密钥、pub_key以及回调地址endpoint
# 举例：若申请时提供的回调地址为https://域名/callback，这里的callback_url就填`/callback`

@bot.on_startswith("hello")
async def handler(event: SendMessageEvent):
    await event.send("world!")
    # 一个简单的处理函数，向你的Bot发送包含`hello`关键词的消息，它将会回复你`world`！


if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350)
    # 启动bot，注意，port端口号要和你所使用的回调地址端口对上
```


## 示例

详见 [example](https://github.com/CMHopeSunshine/villa-py/tree/main/example) 文件夹：

- [单 Bot 运行](https://github.com/CMHopeSunshine/villa-py/blob/main/example/single_bot.py)
- [多 Bot 运行](https://github.com/CMHopeSunshine/villa-py/blob/main/example/multiple_bots.py)
- [处理器介绍](https://github.com/CMHopeSunshine/villa-py/blob/main/example/handle_func.py)
- [消息发送方法](https://github.com/CMHopeSunshine/villa-py/blob/main/example/send_message.py)
- [vercel serverless 部署](https://github.com/CMHopeSunshine/villa-py/blob/main/example/vercel.py)

## 交流、建议和反馈

> 注意：本SDK并非官方SDK

大别野 Bot 和本 SDK 均为开发测试中，如遇问题请提出 [issue](https://github.com/CMHopeSunshine/villa-py/issues) ，感谢支持！

也欢迎来我的大别野[「尘世闲游」]((https://dby.miyoushe.com/chat/1047/21652))(ID: `wgiJNaU`)进行交流~

## 相关项目

- [NoneBot2](https://github.com/nonebot/nonebot2) 非常好用的 Python 跨平台机器人框架！
- [nonebot-adapter-villa](https://github.com/CMHopeSunshine/nonebot-adapter-villa) NoneBot2 的大别野 Bot 适配器。
- [Herta-villa-SDK](https://github.com/MingxuanGame/Herta-villa-SDK) 另一个大别野 Python SDK。
