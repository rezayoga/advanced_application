from typing import Dict, Optional, Any

from starlette.websockets import WebSocket

from project.schemas import User, VoteCount


class WebSocketManager:

    def __init__(self):
        self._users: Dict[User, WebSocket] = {}

    def __len__(self) -> int:
        return len(self._users)

    def add_user(self, user: User, websocket: WebSocket):
        if user in self._users:
            self.remove_user(user)
        self._users[user] = websocket

    def remove_user(self, user: User):
        if user in self._users:
            self._users.pop(user)

    def get_user(self, user: User) -> Optional[User]:
        """Get metadata on a user.
        """
        return self._users.get(user)

    async def broadcast_by_user(self, user: User, message: Any):
        """Broadcast message to all connected users.
        """
        # m = VoteCount.parse_obj(message)
        if message:
            await self._users[user].send_json(message.dict())

    async def broadcast_user_joined(self, user: User):
        """Broadcast message to all connected users.
        """
        if user:
            await self._users[user].send_json(user.dict())

    async def broadcast_user_left(self, user: User):
        """Broadcast message to all connected users.
        """
        if user:
            await self._users[user].send_json(user.dict())

    async def broadcast_all_users(self, message: Any):
        """Broadcast message to all connected users.
        """
        # m = VoteCount.parse_obj(message)
        if message:
            for websocket in self._users.values():
                await websocket.send_json(message.dict())
