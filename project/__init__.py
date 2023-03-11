from typing import Any

from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import HTMLResponse
from rich import inspect
from rich.console import Console
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.endpoints import WebSocketEndpoint
from starlette.types import ASGIApp, Scope, Receive, Send

from project import database
from project.config import settings
from project.core import WebSocketManager
from project.database import get_session
from project.polls.models import User as UserModel
from project.schemas import Vote as VoteSchema, User as UserSchema

console = Console()
wm: WebSocketManager = None
engine = database.engine


def create_app() -> FastAPI:
    app = FastAPI()

    from project.polls import polls_router  # new
    app.include_router(polls_router)  # new

    @app.on_event("startup")
    async def startup_event():
        # inspect(settings.DATABASE_URL, methods=True)
        # Perform connection
        console.print("=====================================")
        console.print("Connecting to database...", style="bold red")
        inspect(settings.DATABASE_URL, methods=True)
        console.print("=====================================")
        # send_external_message_sync(queue_name, "Chatbot Webhook API is running")
        await database.connect()

    @app.on_event("shutdown")
    async def shutdown_event():
        await database.disconnect()

    class WebSocketManagerEventMiddleware:  # pylint: disable=too-few-public-methods
        """Middleware to add the websocket_manager to the scope."""

        def __init__(self, app: ASGIApp):
            self._app = app
            self._websocket_manager = WebSocketManager()

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            if scope["type"] in ("lifespan", "http", "websocket"):
                scope["websocket_manager"] = self._websocket_manager
            await self._app(scope, receive, send)

    app.add_middleware(WebSocketManagerEventMiddleware)

    @app.get("/")
    async def root():
        return {"message": "Hello World!"}

    @app.get("/ws_client")
    async def ws_client(session: AsyncSession = Depends(get_session)):

        html = """
            <!DOCTYPE html>
        	<html>
        	    <head>
        	        <title>Websocket Polling App</title>
        	        <script type="text/javascript">
        	            var ws = null;
                        function login(select_object) {
                            var id = select_object.value;
                            const ws_url = '/ws_vote/' + id;
                            ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://app.rezayogaswara.dev' + ws_url);
                            if (id !== undefined) {
                                ws.onmessage = function(event) {
                                    console.log(event.data);
                                    var messages = document.getElementById('messages');
                                    var message = document.createElement('li');
                                    var content = document.createTextNode(event.data);
                                    message.appendChild(content);
                                    messages.appendChild(message);
                                    document.getElementById("btn-vote-1").disabled = false;
                                };
                                
                                select_object.disabled = true;
                            }
                        }

                        function vote(vote) {
                            ws.send(JSON.stringify({
                                "vote": vote
                            }));        
                        }
        	        </script>
        	    </head>
        	    <body>"""

        """ Select users """
        users = await session.execute(select(UserModel))
        users = users.scalars().all()
        if users:
            html += """
                                <h1 id="h1-title">Users</h1>
                                <select user_id="select_id" style="width:30%" onchange="login(this)">
                                <option selected="selected" value="-">Select</option>
                                """
            for user in users:
                html += f"""
                                  <option value="{user.id}">{user.name}</option>
                                    """

        html += """
                			</select>
                			"""

        html += """<hr />
                	        <button id="btn-vote-1" disabled onclick="vote(1)">Vote 1</button>
                	        <div id="messages"></div>
                	    </body>
                	</html>
                    """

        """ Select poll with all options """
        polls = await session.execute(
            text("SELECT p.id as p_id, p.question as question, o.id as o_id, o.option as option"
                 " FROM polls AS p JOIN options AS o ON p.id = o.poll_id"))
        polls = polls.fetchall()
        if polls:
            data = [_._asdict() for _ in polls]
            console.print(data)

        return HTMLResponse(html)

    @app.websocket("/ws/{id}")
    async def websocket_endpoint(websocket: WebSocket, id: str):
        await websocket.accept()
        while True:
            user_connected = f"User {id} connected!"
            data = await websocket.receive_text()
            await websocket.send_text(f"{data} - {user_connected}")
            console.print(f"{data}")

    @app.websocket_route("/ws_vote/{id}", name="ws_vote")
    class VoteApp(WebSocketEndpoint):
        encoding = "json"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.websocket_manager: WebSocketManager = None
            self.user_id: str = None

        async def on_connect(self, websocket: WebSocket):
            global wm
            _wm = self.scope.get("websocket_manager")
            if _wm is None:
                raise RuntimeError(f"Global `WebSocketManager` instance unavailable!")
            self.websocket_manager = _wm
            wm = self.websocket_manager
            await websocket.accept()
            id_ = websocket.path_params['id']

            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(conn)
                    user = await session.execute(select(UserModel).where(UserModel.id == id_))
                    user = user.scalars().first()
                    u = UserSchema.from_orm(user)

                    if user is not None:
                        self.websocket_manager.add_user(u.id, u.name, websocket)

                        console.print("====================================")
                        console.print(self.websocket_manager.__len__())
                        console.print("====================================")

                        await self.websocket_manager.broadcast_all_users(
                            {"type": "user_join", "data": u.name}
                        )

                        user_id = user.id
                        self.user_id = user_id
                        console.print(f"User {user_id} - {user.name} connected!")
                    else:
                        await websocket.send_json({"type": "error", "data": "User not found!"})
                        await websocket.close()

        async def on_receive(self, websocket: WebSocket, message: Any):
            if self.user_id is None:
                raise RuntimeError("WebSocketManager.on_receive() called without a valid user_id")

        async def on_disconnect(self, websocket: WebSocket, close_code: int):
            if self.user_id is not None:
                # await self.websocket_manager.broadcast_all_users(
                #     {"type": "user_leave", "data": self.user_id}
                # )
                self.websocket_manager.remove_user(self.user_id)
                console.print(f"User {self.user_id} disconnected!")
                websocket.close()

    return app
