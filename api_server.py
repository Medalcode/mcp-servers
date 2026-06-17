import asyncio
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from dotenv import load_dotenv
load_dotenv()

from services.job_service import search_jobs_with_ai, mass_register_sf

app = FastAPI(title="Pathwise UI Dashboard")

# Global metrics store (in a real app, use a DB)
metrics = {
    "jobs_scanned": 0,
    "successful_logins": 0,
    "accounts_created": 0,
    "applications_sent": 0,
    "recent_logs": []
}

def add_log(msg: str):
    metrics["recent_logs"].append(msg)
    if len(metrics["recent_logs"]) > 50:
        metrics["recent_logs"].pop(0)

class SearchRequest(BaseModel):
    query: str
    location: str = "Chile"
    remote_only: bool = False
    filters: dict = None

class RegisterRequest(BaseModel):
    urls: list[str]

class ApplyRequest(BaseModel):
    url: str

# API Endpoints
@app.get("/api/metrics")
async def get_metrics():
    return JSONResponse(metrics)

@app.post("/api/search")
async def api_search(req: SearchRequest):
    add_log(f"Starting job search for: {req.query}")
    # We use empty profile for fast scanning
    profile = {"personalInfo": {"currentTitle": req.query, "summary": "Buscando oportunidades en " + req.query}}
    try:
        jobs = await search_jobs_with_ai(
            query=req.query,
            profile=profile,
            location=req.location,
            remote_only=req.remote_only,
            use_new_engine=True
        )
        metrics["jobs_scanned"] += len(jobs)
        add_log(f"Found {len(jobs)} jobs for {req.query}")
        return {"status": "success", "data": jobs}
    except Exception as e:
        add_log(f"Error searching jobs: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/register")
async def api_register(req: RegisterRequest):
    add_log(f"Starting mass registration for {len(req.urls)} portals...")
    try:
        results = await mass_register_sf(req.urls)
        
        success_count = sum(1 for res in results.values() if res == "SUCCESS")
        metrics["accounts_created"] += success_count
        add_log(f"Registration completed. Success: {success_count}/{len(req.urls)}")
        
        return {"status": "success", "data": results}
    except Exception as e:
        add_log(f"Error in mass registration: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/apply")
async def api_apply(req: ApplyRequest):
    add_log(f"Iniciando postulación a: {req.url}")
    from engines.selenium_engine import SeleniumEngine
    from services.auto_login import attempt_auto_login
    from services.profile_sync import ProfileSyncEngine
    from services.cv_service import CVService
    
    engine = SeleniumEngine()
    try:
        # Load CV Profile
        cv_service = CVService()
        profile_data = cv_service.parse_pdf("/home/medalcode/Escritorio/Opencode Sources/CV_06_2026.pdf")
        
        async def caller(tool_name, args):
            func = getattr(engine, tool_name)
            return await asyncio.to_thread(func, **args)
            
        # 1. Login
        add_log("Autenticando en el portal...")
        engine.navigate(req.url)
        await asyncio.sleep(3)
        await attempt_auto_login(caller, req.url)
        
        # 2. Profile Sync
        add_log("Sincronizando y verificando perfil pre-vuelo...")
        sync_engine = ProfileSyncEngine(engine, profile_data)
        is_synced = await sync_engine.ensure_profile_complete(req.url)
        
        if not is_synced:
            add_log("Sincronización fallida o incompleta. ABORTANDO postulación para proteger reputación.")
            return JSONResponse({"status": "error", "message": "Profile incomplete"}, status_code=400)
            
        add_log("Perfil verificado 100%. Procediendo con la postulación...")
        # 3. Simulate apply 
        engine.navigate(req.url)
        await asyncio.sleep(5)
        
        # Fallback click "Apply" logic
        engine.run_script("""
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
        metrics["applications_sent"] += 1
        return {"status": "success"}
    except Exception as e:
        add_log(f"Error en postulación: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    finally:
        engine.close()

# Serve static frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
