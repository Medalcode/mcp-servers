import asyncio
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def broadcast(self, message: str):
        try:
            loop = asyncio.get_running_loop()
            for connection in list(self.active_connections):
                loop.create_task(connection.send_text(message))
        except RuntimeError:
            pass

manager = ConnectionManager()
