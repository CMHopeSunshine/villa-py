import asyncio
from functools import partial, wraps
import re
from typing import Callable, Coroutine, TypeVar
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def escape_tag(s: str) -> str:
    """用于记录带颜色日志时转义 `<tag>` 类型特殊标签

    参考: [loguru color 标签](https://loguru.readthedocs.io/en/stable/api/logger.html#color)

    参数:
        s: 需要转义的字符串
    """
    return re.sub(r"</?((?:[fb]g\s)?[^<>\s]*)>", r"\\\g<0>", s)


def run_sync(call: Callable[P, R]) -> Callable[P, Coroutine[None, None, R]]:
    """一个用于包装 sync function 为 async function 的装饰器

    参数:
        call: 被装饰的同步函数
    """

    @wraps(call)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        loop = asyncio.get_running_loop()
        pfunc = partial(call, *args, **kwargs)
        return await loop.run_in_executor(None, pfunc)

    return _wrapper


def format_pub_key(pub_key: str) -> str:
    """格式化公钥字符串

    参数:
        pub_key: 公钥字符串
    """
    pub_key = pub_key.strip()
    if pub_key.startswith("-----BEGIN PUBLIC KEY-----"):
        pub_key = pub_key[26:]
    if pub_key.endswith("-----END PUBLIC KEY-----"):
        pub_key = pub_key[:-24]
    pub_key = pub_key.replace(" ", "\n")
    if pub_key[0] != "\n":
        pub_key = "\n" + pub_key
    if pub_key[-1] != "\n":
        pub_key += "\n"
    return "-----BEGIN PUBLIC KEY-----" + pub_key + "-----END PUBLIC KEY-----\n"
