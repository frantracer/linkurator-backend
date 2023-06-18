from pydantic.main import BaseModel


class Message(BaseModel):
    """
    Message with information about the request
    """
    message: str

    def __init__(self, message: str):
        super().__init__(message=message)
