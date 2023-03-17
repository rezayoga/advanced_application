import json
import uuid
from typing import Dict, Optional, Any

import aio_pika
import pika
from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustConnection
from fastapi.encoders import jsonable_encoder
from rich.console import Console
from starlette.websockets import WebSocket

from project.schemas import User

console = Console()


class WebSocketManager:

    def __init__(self):
        self._users: Dict[str, WebSocket] = {}
        self._user_meta: Dict[str, User] = {}

    def __len__(self) -> int:
        return len(self._users)

    def add_user(self, user_id: str, user_name: str, websocket: WebSocket):
        if user_id in self._users:
            self.remove_user(user_id)
        self._users[user_id] = websocket
        self._user_meta[user_id] = User(
            id=user_id, name=user_name
        )

    def remove_user(self, user_id: str):
        if user_id in self._users:
            self._users.pop(user_id)
            self._user_meta.pop(user_id)

    def get_user(self, user_id: str) -> Optional[User]:
        """Get metadata on a user.
        """
        return self._user_meta.get(user_id)

    async def broadcast_by_user_id(self, user_id: str, payload: Any):
        """Broadcast message to all connected users.
        """
        await self._users[user_id].send_json(jsonable_encoder(payload))

    async def broadcast_all_users(self, payload: Any):
        """Broadcast message to all connected users.
        """
        for user_id, websocket in self._users.items():
            await websocket.send_json(jsonable_encoder(payload))


class PikaClient:
    def __init__(self, process_callable):
        self.connection = None
        self.process_callable = process_callable

    async def init_connection(self) -> AbstractRobustConnection:
        """Initiate connection to RabbitMQ"""
        self.connection = await connect_robust("amqp://reza:reza@rezayogaswara.com:5672")

        return self.connection

    async def consume(self, loop, queue_name):
        """Setup message listener with the current running loop"""
        connection = await connect_robust(host='rezayogaswara.com', port=5672, login='reza', password='reza', loop=loop)
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, durable=True, auto_delete=False)
        await queue.consume(self.process_incoming_message, no_ack=False)
        return connection

    async def process_incoming_message(self, message):
        """Processing incoming message from RabbitMQ"""
        # await message.ack()
        # body = message.body.decode()
        # console.print(body)
        # if body:
        #     self.process_callable(json.loads(body))
        pass

    async def publish_async(self, message: dict, queue_name: str):
        """Method to publish message to RabbitMQ"""
        async with self.connection:
            channel = await self.connection.channel()
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue_name
            )

    def publish(self, message: dict):
        """Method to publish message to RabbitMQ"""
        self.channel.basic_publish(
            exchange='',
            routing_key=self.publish_queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=str(uuid.uuid4())
            ),
            body=json.dumps(message)
        )

    def close(self):
        """Close connection to RabbitMQ"""
        self.connection.close()
