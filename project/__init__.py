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
	        <title>Websocket Subscriber Simulator</title>
	    </head>
	    <body onload="add_user(event)">
	        <h1 id="h1-title">Clients</h1>
	        <select user_id="select_token" style="width:30%" onchange="add_user(this)">
	          <option selected="selected" value="-">Select Token</option>
			  <option value="B_r6qBs8S8eWwK9FOltCyA">Token #1 (Valid - B_r6qBs8S8eWwK9FOltCyA)</option>
			  <option value="jfD6puH8TnKLbxBtopU8RQ">Token #2 (Valid - jfD6puH8TnKLbxBtopU8RQ)</option>
			  <option value="GLBHlkW3QSqSDgZV3sKZmA">Token #3 (Valid - GLBHlkW3QSqSDgZV3sKZmA)</option>
			  <option value="4a8a08f09d37b73795649038408b5f33">Token #4 (Invalid - 4a8a08f09d37b73795649038408b5f33)</option>
			  <option value="123/undefined">Token #5 (Invalid - 123/undefined)</option>
			</select>
	        <hr />
	        <div id="token"></div>
	        <div id="message"></div>
	        <script>
	            var ws = null;
	            var token = null;
	            function add_user(select_object) {
	                var token = select_object.value;
	                if (token !== undefined) {
		                const ws_url = '/notification/' + token;
					    const ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://notification.coster.id' + ws_url);
		                ws.onmessage = function(event) {
		                    console.log(event.data);
		                    document.getElementById('message').innerHTML = document.getElementById('message').innerHTML 
		                    + "<hr />" + event.data;
		                };
	                    document.getElementById('token').innerHTML = token;
	                }
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
            console.print(f"Message text was: {data}")

    return app
