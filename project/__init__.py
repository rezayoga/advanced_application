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
                    }
                }
                
                function vote(vote) {
                    ws.send(JSON.stringify({
                        "vote": vote
                    }));        
                }
	        </script>
	    </head>
	    <body>
	        <h1 id="h1-title">Users</h1>
	        <select user_id="select_id" style="width:30%" onchange="login(this)">
	          <option selected="selected" value="-">Select</option>
			  <option value="555c29ce-f878-4296-8776-b8f928cdc61e">Foo</option>
			  <option value="937e41aa-0513-4e3f-8e00-f559acb5af7d">Bar</option>
			  <option value="0a1ed18d-eab2-43bf-a844-206bbc93d572">Baz</option>
			  <option value="0123456789">Unknown</option>
			</select>
	        <hr />
	        <button id="btn-vote-1" disabled onclick="vote(1)">Vote 1</button>
	        <div id="messages"></div>
	    </body>
	</html>
    """

    @app.get("/ws_client")
    async def ws_client(session: AsyncSession = Depends(get_session)):

        """ Select poll with all options """
        polls = await session.execute(
            text("SELECT p.id as p_id, p.question as question, o.id as o_id, o.option as option"
                 " FROM polls AS p JOIN options AS o ON p.id = o.poll_id"))
        p = polls.fetchall()

        if p:
            console.print(p)

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
                    # user_id = user.id
                    # console.print(f"User {user_id} - {user.name} connected!")
                    # self.user_id = user_id
                    # await self.websocket_manager.broadcast_json(
                    #     {"type": "USER_JOIN", "data": u.dict()}
                    # )

                    if user is not None:
                        self.websocket_manager.add_user(u.id, u.name, websocket)
                        await self.websocket_manager.broadcast_all_users(
                            {"type": "USER_JOIN", "data": u.name}
                        )

                        user_id = user.id
                        self.user_id = user_id
                        console.print(f"User {user_id} - {user.name} connected!")

        async def on_receive(self, websocket: WebSocket, message: Any):
            await websocket.send_json({"type": "USER_JOIN", "data": message})
            console.print(f"{message}")

        async def on_disconnect(self, websocket: WebSocket, close_code: int):
            console.print(f"User disconnected!")

    return app
