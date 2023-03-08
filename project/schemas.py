from pydantic import BaseModel

#======

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