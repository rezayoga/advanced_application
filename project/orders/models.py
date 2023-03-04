from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey

from project.database import Base


class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String, nullable=False)

    def __init__(self, question):
        self.question = question


class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey("polls.id"), nullable=False, index=True)
    option = Column(String, nullable=False)

    def __init__(self, poll_id, option):
        self.poll_id = poll_id
        self.option = option


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "option_id", "user_id", name="unique_vote"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, nullable=False, index=True)
    option_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    def __init__(self, poll_id, option_id, user_id):
        self.poll_id = poll_id
        self.option_id = option_id
        self.user_id = user_id


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

    def __init__(self, name):
        self.name = name
