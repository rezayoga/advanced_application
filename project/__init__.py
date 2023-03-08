from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import HTMLResponse
from rich import inspect
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.endpoints import WebSocketEndpoint
from starlette.types import ASGIApp, Scope, Receive, Send

from project import database
from project.config import settings
from project.core import WebSocketManager
from project.database import get_session
from project.polls.models import User as UserModel
from project.schemas import Vote as VoteSchema

console = Console()
wm: WebSocketManager = None


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
	    </head>
	    <body>
	        <h1 id="h1-title">Users</h1>
	        <select user_id="select_id" style="width:30%" onchange="login_user(this)">
	          <option selected="selected" value="-">Select</option>
			  <option value="1">Foo</option>
			  <option value="2">Bar</option>
			  <option value="3">Baz</option>
			  <option value="4">Unknown</option>
			</select>
	        <hr />
	        <div id="messages"></div>
	        <script type="text/javascript">
	            var ws = null;
	            function login_user(select_object) {
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
		                };
	                    ws.onopen = function(event) {
	                        const d = new Date();
	                        ws.send(d.toLocaleTimeString());
                        };
	                }
	            }
	        </script>
	    </body>
	</html>
    """

    @app.get("/ws_client")
    async def get():
        return HTMLResponse(html)

    @app.websocket("/ws/{id}")
    async def websocket_endpoint(websocket: WebSocket, id: str):
        await websocket.accept()
        while True:
            user_connected = f"User {id} connected!"
            data = await websocket.receive_text()
            await websocket.send_text(f"{data} - {user_connected}")
            console.print(f"{data}")

    class DBConnectionService:
        def __init__(self, session: AsyncSession):
            self.session = session

        def get_connection(self):
            return self.session

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
            id_user = websocket.path_params['id']

            session = get_session()

            user = await session.execute(select(UserModel).where(UserModel.id == id_user))
            user = user.scalars().first()
            user_id = user.id
            console.print(f"User {user_id} connected!")
            if user is None:
                console.print(f"User {id_user} not found!")

        async def on_receive(self, websocket: WebSocket, vote: VoteSchema):
            await websocket.send_json({"type": "USER_JOIN", "data": vote})
            console.print(f"{vote}")

        async def on_disconnect(self, websocket: WebSocket, close_code: int):
            console.print(f"User disconnected!")

    return app
