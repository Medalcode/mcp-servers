import asyncio
import os
import uuid
import json
import hashlib
from fastapi import APIRouter, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from api.schemas import SearchRequest, RegisterRequest, ApplyRequest, ModelRequest, BatchApplyRequest
from api.db import get_metrics_dict, create_task, get_task
from api.ws import manager
from api.tasks import bg_search, bg_register, bg_batch_apply, log_with_ws, _sanitize

router = APIRouter()

API_TOKEN = os.environ.get("API_SECRET_TOKEN", "")
WS_TOKEN = os.environ.get("WS_SECRET_TOKEN", "")

def _check_api_token(req: Request):
    if not API_TOKEN:
        return True
    auth = req.headers.get("Authorization", "")
    return auth == f"Bearer {API_TOKEN}"

@router.get("/metrics")
async def get_metrics():
    return JSONResponse(await get_metrics_dict())

@router.get("/models")
async def api_models():
    from router.engine import RouterEngine
    engine = RouterEngine()
    models = await engine.get_available_models()
    return {"models": [{"id": m.id, "name": m.name, "provider": m.provider} for m in models]}

@router.post("/settings/model")
async def api_set_model(req: Request, body: ModelRequest):
    if not _check_api_token(req):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    os.environ["AI_MODEL"] = body.model_id
    await log_with_ws(f"Modelo IA principal cambiado a: {body.model_id}")
    return {"status": "success"}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    row = await get_task(task_id)
    if not row:
        return JSONResponse({"status": "error", "message": "Task not found"}, status_code=404)
    return {"status": row[0], "data": json.loads(row[1]) if row[1] else None}

@router.post("/search")
async def api_search(req: SearchRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await create_task(task_id)
    bg_tasks.add_task(bg_search, task_id, req.query, req.location, req.remote_only, req.filters)
    return {"status": "accepted", "task_id": task_id}

@router.post("/register")
async def api_register(req: RegisterRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await create_task(task_id)
    bg_tasks.add_task(bg_register, task_id, req.urls)
    return {"status": "accepted", "task_id": task_id}

@router.post("/batch-apply")
async def api_batch_apply(req: BatchApplyRequest, bg_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await create_task(task_id)
    bg_tasks.add_task(bg_batch_apply, task_id, req.queries, req.limit)
    return {"status": "accepted", "task_id": task_id}

@router.post("/apply")
async def api_apply(req: ApplyRequest):
    await log_with_ws(f"Iniciando postulación a: {req.url}")
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
            
        await log_with_ws("Autenticando en el portal...")
        await asyncio.to_thread(engine.navigate, req.url)
        await asyncio.sleep(3)
        await attempt_auto_login(caller, req.url)
        
        await log_with_ws("Sincronizando y verificando perfil pre-vuelo...")
        sync_engine = ProfileSyncEngine(engine, profile_data)
        is_synced = await sync_engine.ensure_profile_complete(req.url)
        
        if not is_synced:
            await log_with_ws("Sincronización fallida o incompleta. ABORTANDO postulación para proteger reputación.")
            return JSONResponse({"status": "error", "message": "Profile incomplete"}, status_code=400)
            
        await log_with_ws("Volviendo a la página de la oferta...")
        await asyncio.to_thread(engine.navigate, req.url)
        await asyncio.sleep(3)
        
        from services.form_filler import FormFillerAgent
        
        await log_with_ws("Abriendo modal de postulación...")
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
        
        agent = FormFillerAgent(engine, profile_data, add_log_func=log_with_ws)
        success = await agent.execute(job_id)
        
        if success:
            await log_with_ws("Proceso de postulación con agente finalizado y exitoso.")
            from api.db import update_metric
            await update_metric("applications_sent", 1)
            return {"status": "success", "message": "Postulación completada por la IA"}
        else:
            await log_with_ws("El agente no pudo completar la postulación con éxito.")
            return {"status": "error", "message": "El agente no pudo enviar la postulación"}
    except Exception as e:
        await log_with_ws(f"Error en postulación: {_sanitize(str(e))}")
        return JSONResponse({"status": "error", "message": _sanitize(str(e))}, status_code=500)
    finally:
        if engine is not None:
            engine.close()
