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

</div>

## 特性

- 基于`FastAPI`和`Pydantic`，异步、快速、高性能！
- 完整的类型注解支持
- 便捷的消息构造和发送方法
- 丰富的消息段和完整的API支持
- ~~想不出来了~~

## 安装

- 使用pip: `pip install villa`
- 使用poetry: `poetry add villa`
- 使用pdm: `pdm add villa`

## 快速开始

首先你需要一个[米游社大别野](https://dby.miyoushe.com/chat)的Bot，如果没有请先到[机器人开发者社区](https://dby.miyoushe.com/chat/463/20020)(别野ID: OpenVilla)申请，取得`bot_id`、`bot_secret`

```python
from villa import Bot
from villa.event import SendMessageEvent

bot = Bot(bot_id="your_bot_id", bot_secret="your_bot_secret", callback_url="your_callback_url")
# 初始化Bot，填写你的bot_id、密钥以及回调地址

@bot.on_startswith("hello")
async def handler(event: SendMessageEvent):
    await event.send("world!")
    # 一个简单的处理函数，向你的Bot发送`@Bot hello`，它将会回复你`world`！


if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350)
    # 启动bot，注意，port端口号要和你的回调地址对上
```


## 使用说明

详见`example`文件夹：
- `single_bot.py`: 单Bot运行
- `multiple_bots.py`: 多Bot运行
- `handle_func.py`: 各种处理器介绍
- `send_message.py`: 各种消息发送方法介绍


## 反馈

目前无论是大别野Bot还是本SDK都在测试开发中，如遇问题请提出issue，感谢支持！

也欢迎来我的大别野【尘世闲游】进行交流~ 

- 大别野ID: wgiJNaU
- [Web端链接](https://dby.miyoushe.com/chat/1047/21652)

## 相关项目

- [NoneBot2](https://github.com/nonebot/nonebot2) 非常好用的Python跨平台机器人框架！
- [nonebot-adapter-villa](https://github.com/CMHopeSunshine/nonebot-adapter-villa) NoneBot2的大别野Bot适配器。

推荐有成熟Python开发经验但对NoneBot2不熟悉的小伙伴选择`本SDK`，

对NoneBot2熟悉或希望接触更成熟的生态的小伙伴选择`NoneBot2+Villa适配器`进行开发。