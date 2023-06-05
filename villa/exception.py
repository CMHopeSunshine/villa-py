from .models import ApiResponse

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