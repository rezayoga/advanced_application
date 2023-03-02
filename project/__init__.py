from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse


def create_app() -> FastAPI:
    app = FastAPI()

    from project.orders import orders_router  # new
    app.include_router(orders_router)  # new

    @app.get("/")
    async def root():
        return {"message": "Hello World!"}

    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Chat App</title>
        </head>
        <body>
            <h1>WebSocket Chat</h1>
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" id="messageText" autocomplete="off"/>
                <button>Send</button>
            </form>
            <ul id='messages'>
            </ul>
            <script>
                var ws = new WebSocket("wss://app.rezayogaswara.dev/ws");
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                function sendMessage(event) {
                    var input = document.getElementById("messageText")
                    ws.send(input.value)
                    input.value = ''
                    event.preventDefault()
                }
            </script>
        </body>
    </html>
    """

    @app.get("/ws_client")
    async def get():
        return HTMLResponse(html)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")

    return app
