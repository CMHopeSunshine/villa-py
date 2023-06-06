from typing import Union

from villa import Bot
from villa.event import Event, JoinVillaEvent, SendMessageEvent, AddQuickEmoticonEvent

bot = Bot(
    bot_id="your_bot_id", bot_secret="your_bot_secret", callback_url="your_callback_url"
)

"""通过bot上的各种处理器来处理事件"""


@bot.on_event(SendMessageEvent, AddQuickEmoticonEvent, JoinVillaEvent)
async def event_handler(
    event: Union[SendMessageEvent, AddQuickEmoticonEvent, JoinVillaEvent]
):
    """处理指定事件"""
    ...


@bot.on_event(Event)
async def all_event_handler(event: Event):
    """也可以写基类事件来达到处理所有事件的目的"""
    ...


@bot.on_message()
async def message_handler(event: SendMessageEvent):
    """处理消息事件"""
    ...


@bot.on_message(block=True, priority=1)
async def message_handler2(event: SendMessageEvent):
    """所有处理器都有两个参数：block(是否阻止更低优先级的处理函数执行) priority(优先级，数字越小优先级越高)"""
    ...


@bot.on_keyword("hello", "Hello", "HELLO")
async def keyword_handler(event: SendMessageEvent):
    """处理包含这些关键词的消息事件"""
    ...


@bot.on_startswith("Hello", "hello", prefix={"/", ""})
async def startswith_handler(event: SendMessageEvent):
    """
    处理以这些关键词开头的消息事件

    prefix为可选参数，用于指定消息开头的前缀

    例如在这里话就会所有以Hello、/Hello、hello、/hello开头的消息事件
    """


@bot.on_endswith("world", "World", "WORLD")
async def endswith_handler(event: SendMessageEvent):
    """处理以这些关键词结尾的消息事件"""
    ...


@bot.on_regex(r"hello\s+world")
async def regex_handler(event: SendMessageEvent):
    """处理与正则匹配的消息事件"""
    ...


"""注意：无论是on_keyword、on_startswith、on_endswith还是on_regex
都只对事件消息的纯文本部分进行匹配，不包括@、图片等其他内容"""

if __name__ == "__main__":
    bot.run(host="127.0.0.1", port=13350, log_level="DEBUG")
