import json
from typing import List, Any

from pydantic import BaseModel, validator


class User(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True


class VoteCount(BaseModel):
    count: int
    poll_id: int

    class Config:
        orm_mode = True


class Vote(BaseModel):
    id: int
    poll_id: int
    option_id: int
    user_id: int

    class Config:
        orm_mode = True


class VoteNotification(BaseModel):
    poll_id: str
    question: str
    votes: List[Any]


class Notification(BaseModel):
    broadcast: bool = False
    recipients: List[str] = []
    message: Any = None

    @validator("recipients")
    def recipients_must_be_list(cls, v):
        if not isinstance(v, list):
            raise ValueError("recipients must be a list")
        return v

    @validator("message")
    def message_must_be_json_serializable(cls, v):
        try:
            json.dumps(v)
        except TypeError:
            raise ValueError("message must be JSON serializable")
        return v

    @validator('message')
    def prevent_none(cls, v):
        assert v is not None, 'message may not be None'
        return v

    @validator("broadcast")
    def broadcast_must_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("broadcast must be a boolean")
        return v

    class Config:
        schema_extra = {
            "example": {
                "broadcast": True,
                "recipients": ["555c29ce-f878-4296-8776-b8f928cdc61e",
                               "937e41aa-0513-4e3f-8e00-f559acb5af7d",
                               "0a1ed18d-eab2-43bf-a844-206bbc93d572"],
                "message": {"data": [
                    {"type": "text", "text": "Hello World"},
                    {"type": "image", "url": "https://example.com/image.png"},
                    {"type": "button", "text": "Click Me", "url": "https://example.com"},
                    {"type": "image", "url": "https://example.com/image2.png"},
                ]}
            }
        }
