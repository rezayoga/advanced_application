from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey, DateTime, func, text

from project.database import Base


class Poll(Base):
    __tablename__ = "polls"

    id = Column(String(128), primary_key=True, default=func.uuid_generate_v4())
    question = Column(String, nullable=False)

    def __init__(self, question):
        self.question = question


class Option(Base):
    __tablename__ = "options"

    id = Column(String(128), primary_key=True, default=func.uuid_generate_v4())
    poll_id = Column(String(128), ForeignKey("polls.id"), nullable=False, index=True)
    option = Column(String, nullable=False)

    def __init__(self, poll_id, option):
        self.poll_id = poll_id
        self.option = option


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="unique_vote"),
    )

    id = Column(String(128), primary_key=True, default=func.uuid_generate_v4())
    poll_id = Column(String(128), nullable=False, index=True)
    option_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    def __init__(self, id, poll_id, option_id, user_id):
        self.id = id
        self.poll_id = poll_id
        self.option_id = option_id
        self.user_id = user_id


class User(Base):
    __tablename__ = "users"

    id = Column(String(128), primary_key=True, default=func.uuid_generate_v4())
    name = Column(String, nullable=False)

    def __init__(self, name):
        self.name = name
