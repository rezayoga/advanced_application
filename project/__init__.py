import asyncio
import uuid
from typing import Any

from fastapi import FastAPI, WebSocket, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from pydantic import parse_obj_as
from rich import inspect
from rich.console import Console
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.endpoints import WebSocketEndpoint
from starlette.types import ASGIApp, Scope, Receive, Send

from project import database
from project.config import settings
from project.core import WebSocketManager, PikaClient
from project.database import get_session
from project.polls.models import User as UserModel, Vote as VoteModel
from project.schemas import Vote as VoteSchema, User as UserSchema, Notification as NotificationSchema, \
    VoteNotification as VoteNotificationSchema

console = Console()
wm: WebSocketManager = None
engine = database.engine
loop = asyncio.get_event_loop()
rabbitmq_queue_name = "first_queue"


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

        await pika_client.init_connection()
        task = loop.create_task(pika_client.consume(loop, rabbitmq_queue_name))
        await task

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
        return {"data": "Hello World!"}

    @app.get("/ws_client")
    async def ws_client(session: AsyncSession = Depends(get_session)):
        """ Select users """
        users = await session.execute(select(UserModel))
        users = users.scalars().all()

        """ Select polls """
        polls = await session.execute(
            text("SELECT p.id as p_id, p.question as question, o.id as o_id, o.option as option"
                 " FROM polls AS p JOIN options AS o ON p.id = o.poll_id"))
        polls = polls.fetchall()

        html = """
            <!DOCTYPE html>
        	<html>
        	    <head>
        	        <title>Polling Websocket App</title>
        	        <script type="text/javascript">
        	            var ws = null;
        	            var id = null;
                        function login(select_object) {
                            var id = select_object.value;
                            const ws_url = '/ws_vote/' + id;
                            ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://app.rezayogaswara.dev' + ws_url);
                            if (id !== undefined) {
                                ws.onmessage = function(event) {
                                    console.log(event.data);
                                    var messages = document.getElementById('messages');
                                    var data = document.createElement('li');
                                    var content = document.createTextNode(event.data);
                                    data.appendChild(content);
                                    messages.appendChild(data);
                                    
                                    m = JSON.parse(event.data);
                                    if (m.type === "voter_join") {
                                        document.getElementById(\"btn-vote\").disabled = false;
                                        document.getElementById(\"select-poll\").disabled = false;
                                    }
                                    
                                    document.getElementById(\"btn-vote\").onclick = function() {
                                        vote();
                                    };                           
                                };
                                
                                select_object.disabled = true;
                            }
                        }

                        function vote() {
                            document.getElementById(\"btn-vote\").disabled = true;
                            document.getElementById(\"select-poll\").disabled = true;
                            ws.send(JSON.stringify({ "type": "vote", "poll_id": document.getElementById(\"poll_id\").value, "option_id": document.getElementById(\"select-poll\").value }));
                        }
        	        </script>
        	    </head>
        	    <body>"""

        if users:
            html += """
                    <h3 id="h1-title">Users</h3>
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

        html += """<hr />"""

        if polls:
            data = [_._asdict() for _ in polls]
            html += f"<h3 id=\"h1-title\">{data[0]['question']}</h3>"
            html += f"<input type=\"hidden\" id=\"poll_id\" value=\"{data[0]['p_id']}\">"
            html += "<select id=\"select-poll\" disabled style=\"width:100%\">"
            for poll in data:
                html += f"""<option value="{poll['o_id']}">{poll['option']}</option>"""

            html += """</select>"""

        html += """<hr />"""
        html += """<button id=\"btn-vote\" disabled>Vote!</button><br />"""

        html += """
                	        <div id="messages"></div>
                	    </body>
                	</html>
                    """

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
                            {"type": "voter_join", "data": u.name, "user_id": u.id}
                        )

                        user_id = user.id
                        self.user_id = user_id
                        console.print(f"User {user_id} - {user.name} connected!")
                    else:
                        await websocket.send_json({"type": "error", "data": "User not found!"})
                        await websocket.close()

        async def on_receive(self, websocket: WebSocket, data: Any):
            if self.user_id is None:
                raise RuntimeError("WebSocketManager.on_receive() called without a valid user_id")
            else:

                if data['type'] is not None:

                    async with engine.connect() as conn:
                        async with conn.begin():
                            session = AsyncSession(conn)
                            try:
                                vote = VoteModel(id=str(uuid.uuid4()), user_id=self.user_id, poll_id=data['poll_id'],
                                                 option_id=data['option_id'])

                                session.add(vote)
                                await session.commit()

                                await self.websocket_manager.broadcast_by_user_id(self.user_id, data)
                                console.print(f"User {self.user_id} - {data['option_id']} voted!")

                                vote_count = await get_vote_count(session, data['poll_id'])

                                if vote_count:
                                    data = [_._asdict() for _ in vote_count]
                                    votes = []
                                    for v in data:
                                        votes.append({
                                            "option": v['option'],
                                            "total": v['total']
                                        })

                                    vote_notification = VoteNotificationSchema(
                                        poll_id=data[0]['poll_id'],
                                        question=data[0]['question'],
                                        votes=votes
                                    )

                                await pika_client.init_connection()
                                await pika_client.publish_async(queue_name=rabbitmq_queue_name, message={
                                    "broadcast": False,
                                    "recipients": [
                                        "8fd67538-521c-403b-97b4-542ec7d3fb7f",
                                        "67afb393-a8f4-44b1-9566-a7711734f77d"
                                    ],
                                    "message": jsonable_encoder(vote_notification.dict())
                                })

                            except Exception as e:
                                inspect(e, methods=True)
                                await session.rollback()

                                await self.websocket_manager.broadcast_by_user_id(self.user_id, {"type": "error",
                                                                                                 "data": "Vote failed, already voted!"})
                                console.print(f"User {self.user_id} - {data['option_id']} vote failed!")
                                raise e

        async def on_disconnect(self, websocket: WebSocket, close_code: int):
            if self.user_id is not None:
                # await self.websocket_manager.broadcast_all_users(
                #     {"type": "voter_leave", "data": self.user_id}
                # )
                self.websocket_manager.remove_user(self.user_id)
                console.print(f"User {self.user_id} disconnected!")
                websocket.close()

    def log_incoming_message(message: dict):
        console.print(f"Message received: {message}")
        if wm is not None:
            users = wm.users.keys()
            notification = parse_obj_as(NotificationSchema, message)

            # console.print(f"Users: {users}")

            if notification.broadcast is True:
                loop.create_task(wm.broadcast_all_users(jsonable_encoder(notification.message)))
            else:
                r = sorted(notification.recipients)
                active_user_in_websocket = sorted(users)
                intersection = set(r).intersection(set(active_user_in_websocket))
                if len(intersection) > 0:
                    for user_id in intersection:
                        loop.create_task(wm.broadcast_by_user_id(user_id, jsonable_encoder(notification.message)))

    async def get_vote_count(session: AsyncSession, poll_id: str):
        vote_count = await session.execute(
            text(f"""select count(*) as total, v.poll_id, o.option, p.question
    from votes v join options o on v.option_id = o.id
    join polls p on o.poll_id = p.id where v.poll_id = '{poll_id}'
    group by v.poll_id, o.option, p.question;"""))
        return vote_count.fetchall()

    pika_client = PikaClient(log_incoming_message)
    app.pika_client = pika_client
    return app
