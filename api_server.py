import asyncio
import os
import re
import aiosqlite
from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from dotenv import load_dotenv
load_dotenv()

from services.job_service import search_jobs_with_ai, mass_register_sf


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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    def broadcast(self, message: str):
        try:
            loop = asyncio.get_running_loop()
            for connection in list(self.active_connections):
                loop.create_task(connection.send_text(message))
        except RuntimeError:
            pass

manager = ConnectionManager()

DB_PATH = "metrics.db"

async def update_metric(key: str, amount: int = 1):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("UPDATE metrics SET value = value + ? WHERE key = ?", (amount, key))
        await conn.commit()

async def get_metrics_dict():
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        async with conn.execute("SELECT key, value FROM metrics") as cursor:
            metrics = {row[0]: row[1] async for row in cursor}
        async with conn.execute("SELECT message FROM logs ORDER BY id DESC LIMIT 50") as cursor:
            logs = [row[0] async for row in cursor]
        metrics["recent_logs"] = logs[::-1]
        return metrics

async def add_log(msg: str):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO logs (message) VALUES (?)", (msg,))
        await conn.commit()
    manager.broadcast(msg)

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    location: str = Field(default="Chile", max_length=100)
    remote_only: bool = False
    filters: dict | None = None

class RegisterRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)

class ApplyRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000, pattern=r"^https?://")

class ModelRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=100)

class BatchApplyRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=20)
    limit: int = Field(default=50, ge=1, le=500)

@app.get("/api/metrics")
async def get_metrics():
    return JSONResponse(await get_metrics_dict())

@app.get("/api/models")
async def api_models():
    from router.engine import RouterEngine
    engine = RouterEngine()
    models = await engine.get_available_models()
    return {"models": [{"id": m.id, "name": m.name, "provider": m.provider} for m in models]}

API_TOKEN = os.environ.get("API_SECRET_TOKEN", "")


def _check_api_token(req):
    if not API_TOKEN:
        return True
    auth = req.headers.get("Authorization", "")
    return auth == f"Bearer {API_TOKEN}"


def _sanitize(msg: str) -> str:
    msg = re.sub(r"/home/\w+/[^\s:,)]+", "[REDACTED]", msg)
    return msg[:500]


@app.post("/api/settings/model")
async def api_set_model(req: Request, body: ModelRequest):
    if not _check_api_token(req):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    import os
    os.environ["AI_MODEL"] = body.model_id
    await add_log(f"Modelo IA principal cambiado a: {body.model_id}")
    return {"status": "success"}

WS_TOKEN = os.environ.get("WS_SECRET_TOKEN", "")


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

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    import json
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        async with conn.execute("SELECT status, data FROM task_results WHERE task_id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return JSONResponse({"status": "error", "message": "Task not found"}, status_code=404)
        return {"status": row[0], "data": json.loads(row[1]) if row[1] else None}

async def bg_search(task_id: str, req: SearchRequest):
    import json
    await add_log(f"Starting job search for: {req.query}")
    profile = {"personalInfo": {"currentTitle": req.query, "summary": "Buscando oportunidades en " + req.query}}
    loc = req.location.strip() if req.location and req.location.strip() else "Chile"
    
    try:
        jobs = await search_jobs_with_ai(
            query=req.query,
            profile=profile,
            location=loc,
            remote_only=req.remote_only,
            use_new_engine=True,
            filters=req.filters
        )
        await update_metric("jobs_scanned", len(jobs))
        await add_log(f"Found {len(jobs)} jobs for {req.query}")
        async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
            await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps(jobs), task_id))
            await conn.commit()
    except Exception as e:
        await add_log(f"Error searching jobs: {_sanitize(str(e))}")
        async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
            await conn.execute("UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?", (json.dumps({"message": _sanitize(str(e))}), task_id))
            await conn.commit()

@app.post("/api/search")
async def api_search(req: SearchRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))
        await conn.commit()
    bg_tasks.add_task(bg_search, task_id, req)
    return {"status": "accepted", "task_id": task_id}

async def bg_register(task_id: str, urls: list[str]):
    import json
    await add_log(f"Starting mass registration for {len(urls)} portals...")
    try:
        results = await mass_register_sf(urls)
        success_count = sum(1 for res in results.values() if res == "SUCCESS")
        await update_metric("accounts_created", success_count)
        await add_log(f"Registration completed. Success: {success_count}/{len(urls)}")
        async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
            await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps(results), task_id))
            await conn.commit()
    except Exception as e:
        await add_log(f"Error in mass registration: {_sanitize(str(e))}")
        async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
            await conn.execute("UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?", (json.dumps({"message": _sanitize(str(e))}), task_id))
            await conn.commit()

@app.post("/api/register")
async def api_register(req: RegisterRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))
        await conn.commit()
    bg_tasks.add_task(bg_register, task_id, req.urls)
    return {"status": "accepted", "task_id": task_id}

async def bg_batch_apply(task_id: str, queries: list[str], limit: int):
    import json
    from services.job_service import search_jobs_with_ai
    from tools.auto_apply_tools import _batch_apply_one
    from services.cv_service import parse_pdf, parse_cv_text
    import os
    
    await add_log(f"Iniciando Batch Apply Masivo con queries: {queries}")
    profile = {"personalInfo": {"currentTitle": "Estudiante Informática", "summary": "Buscando oportunidades IT"}}
    try:
        cv_path = os.getenv("USER_CV_PATH", "")
        if not cv_path or not os.path.exists(cv_path):
            await add_log(f"Aviso: USER_CV_PATH no configurado o archivo no encontrado: {cv_path}")
            pdf_data = None
        else:
            pdf_data = await parse_pdf(cv_path)
        if pdf_data and "text" in pdf_data:
            profile_data = parse_cv_text(pdf_data["text"])
            if profile_data:
                profile = profile_data
    except Exception as e:
        await add_log(f"Aviso: No se pudo cargar el PDF del CV: {e}")

    all_jobs = []
    for q in queries:
        await add_log(f"Buscando ofertas para: {q}")
        try:
            jobs = await search_jobs_with_ai(query=q, profile=profile, use_new_engine=True)
            all_jobs.extend(jobs)
        except Exception as e:
            await add_log(f"Error buscando '{q}': {e}")
            
    unique_jobs = {j["url"]: j for j in all_jobs if j.get("url")}
    urls = list(unique_jobs.keys())
    urls = urls[:limit]
    
    await add_log(f"Total ofertas únicas a procesar: {len(urls)}")
    
    success_count = 0
    for idx, url in enumerate(urls, 1):
        await add_log(f"[{idx}/{len(urls)}] Postulando a: {url}")
        try:
            cv_path = os.getenv("USER_CV_PATH", "")
            res = await _batch_apply_one(url, profile, cv_path) if cv_path else {"success": False, "error": "USER_CV_PATH not set"}
            if res.get("success"):
                success_count += 1
                await update_metric("applications_sent", 1)
                await add_log(f"Result: {res.get('title')} -> EXITO")
            else:
                await add_log(f"Result: {res.get('title')} -> FAILED: {res.get('error')}")
        except Exception as e:
            await add_log(f"Result: {url} -> FAILED: Excepción {e}")
            
    await add_log(f"Batch Apply completado! Postulaciones exitosas: {success_count}/{len(urls)}")
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps({"success": success_count, "total": len(urls)}), task_id))
        await conn.commit()

@app.post("/api/batch-apply")
async def api_batch_apply(req: BatchApplyRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))
        await conn.commit()
    bg_tasks.add_task(bg_batch_apply, task_id, req.queries, req.limit)
    return {"status": "accepted", "task_id": task_id}

@app.post("/api/apply")
async def api_apply(req: ApplyRequest):
    await add_log(f"Iniciando postulación a: {req.url}")
    engine = None
    try:
        from engines.selenium_engine import SeleniumEngine
        from services.auto_login import attempt_auto_login
        from services.profile_sync import ProfileSyncEngine
        from services.cv_service import parse_pdf, parse_cv_text
        
        engine = SeleniumEngine()
        
        cv_path = os.getenv("USER_CV_PATH", "")
        if not cv_path or not os.path.exists(cv_path):
            return JSONResponse({"status": "error", "message": "USER_CV_PATH not configured or file not found"}, status_code=400)
        pdf_res = await parse_pdf(cv_path)
        profile_data = parse_cv_text(pdf_res["text"])
        
        async def caller(tool_name, args):
            func = getattr(engine, tool_name)
            return await asyncio.to_thread(func, **args)
            
        await add_log("Autenticando en el portal...")
        await asyncio.to_thread(engine.navigate, req.url)
        await asyncio.sleep(3)
        await attempt_auto_login(caller, req.url)
        
        await add_log("Sincronizando y verificando perfil pre-vuelo...")
        sync_engine = ProfileSyncEngine(engine, profile_data)
        is_synced = await sync_engine.ensure_profile_complete(req.url)
        
        if not is_synced:
            await add_log("Sincronización fallida o incompleta. ABORTANDO postulación para proteger reputación.")
            return JSONResponse({"status": "error", "message": "Profile incomplete"}, status_code=400)
            
        await add_log("Volviendo a la página de la oferta...")
        await asyncio.to_thread(engine.navigate, req.url)
        await asyncio.sleep(3)
        
        from services.form_filler import FormFillerAgent
        import hashlib
        
        # Pre-flight click to ensure any "Easy Apply" or "Postular" modal is open
        await add_log("Abriendo modal de postulación...")
        await asyncio.to_thread(engine.run_script, """
        const btns = document.querySelectorAll('button, a, span');
        btns.forEach(btn => {
            const txt = (btn.innerText || '').toLowerCase();
            if(txt.includes('postular') || txt.includes('apply') || txt.includes('solicitar')) {
                btn.click();
            }
        });
        """)
        await asyncio.sleep(4)
        
        job_id = hashlib.md5(req.url.encode()).hexdigest()[:10]
        
        # Iniciar agente inteligente
        agent = FormFillerAgent(engine, profile_data, add_log_func=add_log)
        success = await agent.execute(job_id)
        
        if success:
            await add_log("Proceso de postulación con agente finalizado y exitoso.")
            await update_metric("applications_sent", 1)
            return {"status": "success", "message": "Postulación completada por la IA"}
        else:
            await add_log("El agente no pudo completar la postulación con éxito.")
            return {"status": "error", "message": "El agente no pudo enviar la postulación"}
    except Exception as e:
        await add_log(f"Error en postulación: {_sanitize(str(e))}")
        return JSONResponse({"status": "error", "message": _sanitize(str(e))}, status_code=500)
    finally:
        if engine is not None:
            engine.close()

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
