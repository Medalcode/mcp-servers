import json
import os
import re
from api.db import update_metric, add_log, update_task_status
from api.ws import manager

def _sanitize(msg: str) -> str:
    msg = re.sub(r"/home/\w+/[^\s:,)]+", "[REDACTED]", msg)
    return msg[:500]

async def log_with_ws(msg: str):
    await add_log(msg, manager.broadcast)

async def bg_search(task_id: str, req_query: str, req_location: str, req_remote_only: bool, req_filters: dict | None):
    from services.job_service import search_jobs_with_ai
    
    await log_with_ws(f"Starting job search for: {req_query}")
    profile = {"personalInfo": {"currentTitle": req_query, "summary": "Buscando oportunidades en " + req_query}}
    loc = req_location.strip() if req_location and req_location.strip() else "Chile"
    
    try:
        jobs = await search_jobs_with_ai(
            query=req_query,
            profile=profile,
            location=loc,
            remote_only=req_remote_only,
            use_new_engine=True,
            filters=req_filters
        )
        await update_metric("jobs_scanned", len(jobs))
        await log_with_ws(f"Found {len(jobs)} jobs for {req_query}")
        await update_task_status(task_id, 'success', json.dumps(jobs))
    except Exception as e:
        await log_with_ws(f"Error searching jobs: {_sanitize(str(e))}")
        await update_task_status(task_id, 'error', json.dumps({"message": _sanitize(str(e))}))

async def bg_register(task_id: str, urls: list[str]):
    from services.job_service import mass_register_sf
    await log_with_ws(f"Starting mass registration for {len(urls)} portals...")
    try:
        results = await mass_register_sf(urls)
        success_count = sum(1 for res in results.values() if res == "SUCCESS")
        await update_metric("accounts_created", success_count)
        await log_with_ws(f"Registration completed. Success: {success_count}/{len(urls)}")
        await update_task_status(task_id, 'success', json.dumps(results))
    except Exception as e:
        await log_with_ws(f"Error in mass registration: {_sanitize(str(e))}")
        await update_task_status(task_id, 'error', json.dumps({"message": _sanitize(str(e))}))

async def bg_batch_apply(task_id: str, queries: list[str], limit: int):
    from services.job_service import search_jobs_with_ai
    from tools.auto_apply_tools import _batch_apply_one
    from services.cv_service import parse_pdf, parse_cv_text
    
    await log_with_ws(f"Iniciando Batch Apply Masivo con queries: {queries}")
    profile = {"personalInfo": {"currentTitle": "Estudiante Informática", "summary": "Buscando oportunidades IT"}}
    try:
        cv_path = os.getenv("USER_CV_PATH", "")
        if not cv_path or not os.path.exists(cv_path):
            await log_with_ws(f"Aviso: USER_CV_PATH no configurado o archivo no encontrado: {cv_path}")
            pdf_data = None
        else:
            pdf_data = await parse_pdf(cv_path)
        if pdf_data and "text" in pdf_data:
            profile_data = parse_cv_text(pdf_data["text"])
            if profile_data:
                profile = profile_data
    except Exception as e:
        await log_with_ws(f"Aviso: No se pudo cargar el PDF del CV: {e}")

    all_jobs = []
    for q in queries:
        await log_with_ws(f"Buscando ofertas para: {q}")
        try:
            jobs = await search_jobs_with_ai(query=q, profile=profile, use_new_engine=True)
            all_jobs.extend(jobs)
        except Exception as e:
            await log_with_ws(f"Error buscando '{q}': {e}")
            
    unique_jobs = {j["url"]: j for j in all_jobs if j.get("url")}
    urls = list(unique_jobs.keys())
    urls = urls[:limit]
    
    await log_with_ws(f"Total ofertas únicas a procesar: {len(urls)}")
    
    success_count = 0
    for idx, url in enumerate(urls, 1):
        await log_with_ws(f"[{idx}/{len(urls)}] Postulando a: {url}")
        try:
            cv_path = os.getenv("USER_CV_PATH", "")
            res = await _batch_apply_one(url, profile, cv_path) if cv_path else {"success": False, "error": "USER_CV_PATH not set"}
            if res.get("success"):
                success_count += 1
                await update_metric("applications_sent", 1)
                await log_with_ws(f"Result: {res.get('title')} -> EXITO")
            else:
                await log_with_ws(f"Result: {res.get('title')} -> FAILED: {res.get('error')}")
        except Exception as e:
            await log_with_ws(f"Result: {url} -> FAILED: Excepción {e}")
            
    await log_with_ws(f"Batch Apply completado! Postulaciones exitosas: {success_count}/{len(urls)}")
    await update_task_status(task_id, 'success', json.dumps({"success": success_count, "total": len(urls)}))
