<div align="center">

# Villa

_✨ 米游社大别野Bot Python SDK ✨_

</div>

## 说明

开发ing...

可通过`pip install git+https://github.com/CMHopeSunshine/villa-py.git@main` 安装使用。

## 使用示例

```python
from villa import Bot, SendMessageEvent


bot = Bot(bot_id="your_bot_id", bot_secret="your_bot_secret", callback_url="your_callback_url")

@bot.on_message()
async def handler(bot: Bot, event: SendMessageEvent):
    if "hello" in event.content.content.text:
        await bot.send_msg(event.villa_id, event.room_id, "world")  # 暂时只支持纯文本


if __name__ == "__main__":
    bot.run()
```
向你的Bot发送`@Bot hello`，它将会回复你`world`！

## 进度

- [ ] 富文本消息
- [ ] API补全
- [ ] 更便捷的消息处理方法