from typing import Dict, Optional, Any

from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from project.schemas import User, VoteCount


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
        for websocket in self._users.values():
            await websocket.send_json(jsonable_encoder(payload))


