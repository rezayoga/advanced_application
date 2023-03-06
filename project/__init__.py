from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from rich.console import Console

console = Console()


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
	        <title>Websocket Polling App</title>
	    </head>
	    <body onload="login_user(event)">
	        <h1 id="h1-title">Users</h1>
	        <select user_id="select_id" style="width:30%" onchange="login_user(this)">
	          <option selected="selected" value="-">Select</option>
			  <option value="1">Foo</option>
			  <option value="2">Bar</option>
			  <option value="3">Baz</option>
			  <option value="4">Unknown</option>
			</select>
	        <hr />
	        <div id="id"></div>
	        <div id="messages"></div>
	        <script>
	            var ws = null;
	            var id = null;
	            function login_user(select_object) {
	                var id = select_object.value;
	                if (id !== undefined) {
		                const ws_url = '/ws/' + id;
					    const ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://app.rezayogaswara.dev' + ws_url);
		                ws.onmessage = function(event) {
		                    console.log(event.data);
		                    document.getElementById('messages').innerHTML = document.getElementById('message').innerHTML 
		                    + "<hr />" + event.data;
		                };
	                    document.getElementById('id').innerHTML = id;
	                }
	            }
	            ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
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
            console.print(f"User {id} connected!")
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
            console.print(f"Message text was: {data}")

    return app
