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
            f"<ActionFailed: {self.status_code}, retcode={self.response.retcode}, "
            f"message={self.response.message}, data={self.response.data}>"
        )

    def __str__(self):
        return self.__repr__()


class StopPropagation(Exception):
    def __init__(self, handler: "EventHandler", *args) -> None:
        self.handler = handler
        super().__init__(*args)
