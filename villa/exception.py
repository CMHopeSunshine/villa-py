from typing import TYPE_CHECKING

from .models import ApiResponse

if TYPE_CHECKING:
    from .handle import EventHandler


class ActionFailed(Exception):
    def __init__(self, status_code: int, response: ApiResponse):
        self.status_code = status_code
        self.response = response

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: {self.status_code}, "
            f"retcode={self.response.retcode}, "
            f"message={self.response.message}, "
            f"data={self.response.data}>"
        )

    def __str__(self):
        return self.__repr__()


class UnknownServerError(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(-502, response)


class InvalidRequest(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(-1, response)


class InsufficientPermission(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(10318001, response)


class BotNotAdded(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(10322002, response)


class PermissionDenied(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(10322003, response)


class InvalidMemberBotAccessToken(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(10322004, response)


class InvalidBotAuthInfo(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(10322005, response)


class UnsupportedMsgType(ActionFailed):
    def __init__(self, response: ApiResponse):
        super().__init__(10322006, response)


class StopPropagation(Exception):
    def __init__(self, handler: "EventHandler", *args) -> None:
        self.handler = handler
        super().__init__(*args)
