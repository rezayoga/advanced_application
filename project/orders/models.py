from sqlalchemy import Column, Integer, String

from project.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String, nullable=False)

    def __init__(self, user_id, product_id, quantity, price, status):
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity
        self.price = price
        self.status = status
