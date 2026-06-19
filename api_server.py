import asyncio
import sqlite3
import uuid
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from dotenv import load_dotenv
load_dotenv()

from services.job_service import search_jobs_with_ai, mass_register_sf

app = FastAPI(title="Pathwise UI Dashboard")

DB_PATH = "metrics.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS metrics (
                            key TEXT PRIMARY KEY,
                            value INTEGER
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS task_results (
                            task_id TEXT PRIMARY KEY,
                            status TEXT,
                            data TEXT
                        )''')
        defaults = {"jobs_scanned": 0, "successful_logins": 0, "accounts_created": 0, "applications_sent": 0}
        for k, v in defaults.items():
            conn.execute("INSERT OR IGNORE INTO metrics (key, value) VALUES (?, ?)", (k, v))
init_db()

def update_metric(key: str, amount: int = 1):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE metrics SET value = value + ? WHERE key = ?", (amount, key))

def get_metrics_dict():
    with sqlite3.connect(DB_PATH) as conn:
        metrics = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM metrics")}
        logs = [row[0] for row in conn.execute("SELECT message FROM logs ORDER BY id DESC LIMIT 50")]
        metrics["recent_logs"] = logs[::-1]
        return metrics

def add_log(msg: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO logs (message) VALUES (?)", (msg,))

class SearchRequest(BaseModel):
    query: str
    location: str = "Chile"
    remote_only: bool = False
    filters: dict = None

class RegisterRequest(BaseModel):
    urls: list[str]

class ApplyRequest(BaseModel):
    url: str

@app.get("/api/metrics")
async def get_metrics():
    return JSONResponse(get_metrics_dict())

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    import json
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT status, data FROM task_results WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            return JSONResponse({"status": "error", "message": "Task not found"}, status_code=404)
        return {"status": row[0], "data": json.loads(row[1]) if row[1] else None}

async def bg_search(task_id: str, req: SearchRequest):
    import json
    add_log(f"Starting job search for: {req.query}")
    profile = {"personalInfo": {"currentTitle": req.query, "summary": "Buscando oportunidades en " + req.query}}
    try:
        jobs = await search_jobs_with_ai(
            query=req.query,
            profile=profile,
            location=req.location,
            remote_only=req.remote_only,
            use_new_engine=True
        )
        update_metric("jobs_scanned", len(jobs))
        add_log(f"Found {len(jobs)} jobs for {req.query}")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps(jobs), task_id))
    except Exception as e:
        add_log(f"Error searching jobs: {str(e)}")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?", (json.dumps({"message": str(e)}), task_id))

@app.post("/api/search")
async def api_search(req: SearchRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))
    bg_tasks.add_task(bg_search, task_id, req)
    return {"status": "accepted", "task_id": task_id}

async def bg_register(task_id: str, urls: list[str]):
    import json
    add_log(f"Starting mass registration for {len(urls)} portals...")
    try:
        results = await mass_register_sf(urls)
        success_count = sum(1 for res in results.values() if res == "SUCCESS")
        update_metric("accounts_created", success_count)
        add_log(f"Registration completed. Success: {success_count}/{len(urls)}")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps(results), task_id))
    except Exception as e:
        add_log(f"Error in mass registration: {str(e)}")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?", (json.dumps({"message": str(e)}), task_id))

@app.post("/api/register")
async def api_register(req: RegisterRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))
    bg_tasks.add_task(bg_register, task_id, req.urls)
    return {"status": "accepted", "task_id": task_id}

@app.post("/api/apply")
async def api_apply(req: ApplyRequest):
    add_log(f"Iniciando postulación a: {req.url}")
    from engines.selenium_engine import SeleniumEngine
    from services.auto_login import attempt_auto_login
    from services.profile_sync import ProfileSyncEngine
    from services.cv_service import CVService
    
    engine = SeleniumEngine()
    try:
        cv_service = CVService()
        profile_data = cv_service.parse_pdf("/home/medalcode/Escritorio/Opencode Sources/CV_06_2026.pdf")
        
        async def caller(tool_name, args):
            func = getattr(engine, tool_name)
            return await asyncio.to_thread(func, **args)
            
        add_log("Autenticando en el portal...")
        await asyncio.to_thread(engine.navigate, req.url)
        await asyncio.sleep(3)
        await attempt_auto_login(caller, req.url)
        
        add_log("Sincronizando y verificando perfil pre-vuelo...")
        sync_engine = ProfileSyncEngine(engine, profile_data)
        is_synced = await sync_engine.ensure_profile_complete(req.url)
        
        if not is_synced:
            add_log("Sincronización fallida o incompleta. ABORTANDO postulación para proteger reputación.")
            return JSONResponse({"status": "error", "message": "Profile incomplete"}, status_code=400)
            
        add_log("Perfil verificado 100%. Procediendo con la postulación...")
        await asyncio.to_thread(engine.navigate, req.url)
        await asyncio.sleep(5)
        
        await asyncio.to_thread(engine.run_script, """
        const btns = document.querySelectorAll('button, a');
        btns.forEach(btn => {
            const txt = btn.innerText.toLowerCase();
            if(txt.includes('postular') || txt.includes('apply')) {
                btn.click();
            }
        });
        """)
        await asyncio.sleep(5)
        
        add_log("Postulación completada exitosamente.")
        update_metric("applications_sent", 1)
        return {"status": "success"}
    except Exception as e:
        add_log(f"Error en postulación: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    finally:
        engine.close()

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
