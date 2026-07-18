import aiosqlite
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from dotenv import load_dotenv
load_dotenv()

from api.db import DB_PATH
from api.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute('''CREATE TABLE IF NOT EXISTS metrics (
                            key TEXT PRIMARY KEY,
                            value INTEGER
                        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS task_results (
                            task_id TEXT PRIMARY KEY,
                            status TEXT,
                            data TEXT
                        )''')
        defaults = {"jobs_scanned": 0, "successful_logins": 0, "accounts_created": 0, "applications_sent": 0}
        for k, v in defaults.items():
            await conn.execute("INSERT OR IGNORE INTO metrics (key, value) VALUES (?, ?)", (k, v))
        
        # Clear previous logs to start fresh
        await conn.execute("DELETE FROM logs")
        
        await conn.commit()
    yield

app = FastAPI(title="Pathwise UI Dashboard", lifespan=lifespan)

app.include_router(api_router, prefix="/api", tags=["API"], include_in_schema=True)

from fastapi import WebSocket, WebSocketDisconnect
from api.ws import manager
from api.endpoints import WS_TOKEN

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    if WS_TOKEN:
        token = websocket.query_params.get("token", "")
        if token != WS_TOKEN:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    reload_mode = os.environ.get("API_RELOAD", "false").lower() == "true"
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=reload_mode)
