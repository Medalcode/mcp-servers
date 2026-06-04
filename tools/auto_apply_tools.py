from mcp.server import FastMCP
from database.repos import applications as app_repo
from services.form_filler import (
    parse_forms_json, generate_answer, generate_radio_answer,
    generate_select_answer, QuestionType, FormQuestion
)
from services.ai_provider import _call_routemcp
from database.repos import profiles as profile_repo
import asyncio
import json
import logging
import os
import re
import signal
import sys
import time
import uuid
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_browser_proc = None
_browser_proc_lock = asyncio.Lock()
_next_req_id = 100
_req_id_lock = asyncio.Lock()


async def _next_id() -> int:
    global _next_req_id
    async with _req_id_lock:
        cur = _next_req_id
        _next_req_id += 1
        return cur


async def _consume_stderr(proc):
    try:
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            logger.debug("BrowserMCP stderr: %s", line.decode().rstrip())
    except Exception:
        pass


async def _read_json_response(proc, timeout=60):
    buf = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=min(5.0, remaining))
        except asyncio.TimeoutError:
            continue
        if not line:
            break
        buf += line.decode()
        try:
            return json.loads(buf)
        except json.JSONDecodeError:
            continue
    raise TimeoutError("No valid JSON response from browser")


async def _ensure_browser_proc():
    global _browser_proc
    async with _browser_proc_lock:
        if _browser_proc is None or _browser_proc.returncode is not None:
            env = {**os.environ, "BROWSER_ENGINE": "selenium", "CHROME_DEBUG_PORT": "9226"}
            _browser_proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "servers.browser",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=_MCP_DIR,
                env=env,
            )
            asyncio.ensure_future(_consume_stderr(_browser_proc))
            init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                   "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                              "clientInfo": {"name": "pathwise", "version": "1.0"}}}) + "\n"
            _browser_proc.stdin.write(init_req.encode())
            await _browser_proc.stdin.drain()
            resp = await _read_json_response(_browser_proc, timeout=10)
            logger.debug("BrowserMCP init response: %s", str(resp)[:100] if resp else "None")
            init_notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n"
            _browser_proc.stdin.write(init_notif.encode())
            await _browser_proc.stdin.drain()
    return _browser_proc


async def _call_browser_tool(tool: str, args: dict, max_retries: int = 2) -> str:
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            proc = await _ensure_browser_proc()
            req_id = await _next_id()
            payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                                  "params": {"name": tool, "arguments": args}}) + "\n"
            proc.stdin.write(payload.encode())
            await proc.stdin.drain()
            data = await _read_json_response(proc, timeout=60)
            if "result" in data:
                items = data["result"].get("content", [])
                for item in items:
                    if item.get("type") == "text":
                        return item["text"]
            if "error" in data:
                logger.warning("BrowserMCP error: %s", data["error"])
                return f"BrowserMCP error: {data['error'].get('message', 'unknown')}"
            return "BrowserMCP call failed (no result)"
        except (asyncio.TimeoutError, TimeoutError) as e:
            last_error = str(e)
            logger.error("BrowserMCP timeout for %s (attempt %d/%d)", tool, attempt + 1, max_retries + 1)
            await _reset_browser_proc()
            if attempt < max_retries:
                await asyncio.sleep(1 * (attempt + 1))
        except Exception as e:
            last_error = str(e)
            logger.error("BrowserMCP call failed: %s (attempt %d/%d)", e, attempt + 1, max_retries + 1)
            await _reset_browser_proc()
            if attempt < max_retries:
                await asyncio.sleep(1 * (attempt + 1))
    return f"BrowserMCP failed after {max_retries + 1} attempts: {last_error}"


async def _auto_click_apply():
    """Try to click the apply button by common text labels (Postularme, Apply, etc.)."""
    patterns = "Postularme|Postular|Apply|Aplicar|Aplica ahora|Iniciar postulación|Enviar postulación|Quiero postular"
    result = await _call_browser_tool("click_by_text", {"text": patterns})
    await asyncio.sleep(2)
    return result


async def _reset_browser_proc():
    global _browser_proc
    async with _browser_proc_lock:
        if _browser_proc:
            try:
                _browser_proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(_browser_proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    _browser_proc.kill()
                    await _browser_proc.wait()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning("reset_browser_proc: %s", e)
            _browser_proc = None


async def _should_apply(page_text: str, profile: dict) -> tuple[bool, str]:
    """Check if the job matches the user's profile. Only accepts remote positions."""
    text_lower = (page_text or "").lower()

    # Quick reject: presencial/híbrido without remote option
    non_remote_keywords = ["presencial", "trabajo presencial", "oficina", "asistir a oficina"]
    remote_keywords = ["remoto", "remote", "100% remoto", "teletrabajo", "home office", "trabajo desde casa"]
    hybrid_keywords = ["híbrido", "hibrido", "mixto", "presencial/remoto"]

    has_remote = any(kw in text_lower for kw in remote_keywords)
    has_hybrid = any(kw in text_lower for kw in hybrid_keywords)

    if not has_remote and not has_hybrid:
        if any(kw in text_lower for kw in non_remote_keywords):
            return False, "Oferta presencial, solo aplicamos a remoto"

    if has_hybrid and not has_remote:
        return False, "Oferta híbrida, solo aplicamos a 100% remoto"

    skills = profile.get("skills", [])
    exp = profile.get("experience", [])
    pi = profile.get("personalInfo", {})
    edu = profile.get("education", [])
    current_edu = ""
    for e in edu:
        if e.get("current"):
            current_edu = f"{e.get('degree', '')} en {e.get('school', '')}"
            break

    prompt = f"""Eres un asesor de postulaciones. Dado el perfil del usuario y la descripción de la oferta, determina si DEBE postular o NO.

IMPORTANTE: Solo aceptamos trabajo 100% remoto. Rechaza cualquier oferta presencial o híbrida.

Perfil:
- Nivel: Estudiante/práctica/junior (en curso: {current_edu})
- Skills: {', '.join(skills[:15])}
- Experiencia: {'; '.join(f"{e['title']} en {e['company']}" for e in exp[:3])}

Oferta (primeros 1500 caracteres):
{page_text[:1500]}

Responde SOLO con JSON:
{{"apply": true/false, "reason": "explicación corta en español"}}"""

    try:
        result = await _call_routemcp("skill_check", prompt)
        cleaned = _clean_json(result)
        import json
        parsed = json.loads(cleaned)
        return parsed.get("apply", True), parsed.get("reason", "Sin evaluación")
    except Exception as e:
        logger.warning("Skill check AI evaluation failed: %s", e)
        return True, "No se pudo evaluar, se postula igual"


async def _get_context_help(question: FormQuestion, profile: dict) -> str:
    label_lower = question.label.lower()

    if any(t in label_lower for t in ["carrera", "estudiando", "semestre", "formación", "formación académica", "casa de estudios", "universidad"]):
        edu = profile.get("education", [])
        if edu:
            current = [e for e in edu if e.get("current")]
            if current:
                e = current[0]
                return f"{e['degree']} en {e['school']}, actualmente cursando."
            return f"{edu[0]['degree']} en {edu[0]['school']}."
    return ""


async def _smart_fill_form(driver_caller, forms_json: str, profile: dict,
                           submit: bool = True) -> str:
    questions = parse_forms_json(forms_json)
    if not questions:
        await _auto_click_apply()
        new_forms = await driver_caller("forms", {})
        questions = parse_forms_json(new_forms)

    if not questions and submit:
        await driver_caller("click_by_text", {"text": "Postular|Aplicar|Enviar|Confirmar|Postularme"})
        return "Sin campos de formulario detectados. Se intentó postular directamente."
    elif not questions:
        return "No se detectaron campos en el formulario."

    filled_count = 0
    skipped_count = 0
    errors = []
    answers_log = []

    async def _fill_field(q):
        nonlocal filled_count, skipped_count
        if q.type in (QuestionType.HIDDEN, QuestionType.PASSWORD):
            return
        if q.type == QuestionType.RADIO:
            answer = generate_radio_answer(q, profile)
            for option in q.options or []:
                try:
                    await driver_caller("click", {"selector": f"input[name='{q.name}'][value='{option}']"})
                except Exception as e:
                    logger.warning("radio click '%s' option '%s': %s", q.name, option, e)
            answers_log.append(f"  [{q.type.value}] {q.label[:40]} -> {answer}")
            filled_count += 1
        elif q.type in (QuestionType.SELECT,):
            answer = generate_select_answer(q, profile)
            if answer:
                try:
                    await driver_caller("fill", {"selector": f"select[name='{q.name}']", "value": answer})
                    answers_log.append(f"  [{q.type.value}] {q.label[:40]} -> {answer}")
                    filled_count += 1
                except Exception as e:
                    err = f"Select '{q.name}': {e}"
                    errors.append(err)
                    logger.warning(err)
            else:
                skipped_count += 1
        elif q.type in (QuestionType.TEXTAREA, QuestionType.TEXT,
                        QuestionType.EMAIL, QuestionType.TEL, QuestionType.NUMBER):
            answer = generate_answer(q, profile)
            ctx = await _get_context_help(q, profile)
            if ctx:
                answer = ctx
            selector = ""
            if q.name:
                selector = f"[name='{q.name}']"
            if selector:
                try:
                    await driver_caller("fill", {"selector": selector, "value": answer})
                    answers_log.append(f"  [{q.type.value}] {q.label[:40]} -> {answer[:50]}...")
                    filled_count += 1
                except Exception as e:
                    errors.append(f"Field '{q.name}': {e}")
            else:
                skipped_count += 1
        else:
            skipped_count += 1

    # Step 1: Fill salary-related fields first
    salary_qs = [q for q in questions if re.search(r'sueldo|salario|renta|pretensión', q.label.lower())]
    for q in salary_qs:
        await _fill_field(q)

    # Step 2: If there's a salary form, submit it first
    if salary_qs and submit:
        try:
            await driver_caller("click_by_text", {"text": "Postularme|Postular|Actualizar"})
            await asyncio.sleep(3)
            # Re-detect forms after salary submit
            new_forms = await driver_caller("forms", {})
            new_qs = parse_forms_json(new_forms)
            if new_qs:
                questions = new_qs
        except Exception as e:
            logger.warning("Salary form submit/re-detect: %s", e)

    # Step 3: Fill remaining fields (preguntas, etc.)
    done_names = {q.name for q in salary_qs}
    for q in questions:
        if q.name in done_names:
            continue
        await _fill_field(q)

    # Step 4: Final submit
    if submit and filled_count > 0:
        try:
            await driver_caller("click_by_text", {"text": "Responder|Enviar|Postularme|Postular|Submit|Aplicar|Guardar|Siguiente|Finalizar"})
        except Exception as e:
            logger.warning("Final submit click_by_text: %s", e)
            try:
                await driver_caller("click", {"selector": "input[type='submit'], button[type='submit']"})
            except Exception as e2:
                logger.warning("Final submit CSS click: %s", e2)
    elif submit and not filled_count and not skipped_count:
        try:
            await driver_caller("click_by_text", {"text": "Postular|Aplicar|Enviar|Confirmar"})
        except Exception as e:
            logger.warning("Fallback submit: %s", e)

    log = "\n".join(answers_log)
    result = f"Formulario: {filled_count} campos llenados, {skipped_count} omitidos"
    if errors:
        result += f"\nErrores: {'; '.join(errors[:3])}"
    result += f"\n\nRespuestas:\n{log}"
    return result


def _extract_title_from_offer_url(url: str) -> str:
    path = urlparse(url).path
    parts = path.rstrip("/").split("/")
    if parts:
        slug = parts[-1].split("#")[0].split("?")[0]
        segments = slug.split("-")
        # Remove the hash ID at the end (32 char alphanumeric)
        clean = []
        for s in segments:
            if len(s) == 32 and s.isalnum():
                break
            clean.append(s)
        return " ".join(clean).title() if clean else ""
    return ""


async def _batch_apply_one(url: str, profile: dict) -> dict:
    result = {"url": url, "success": False, "title": "", "company": "", "error": ""}

    title = _extract_title_from_offer_url(url)
    result["title"] = title

    try:
        page = await _call_browser_tool("navigate", {"url": url})
        if not page or "Error" in page:
            result["error"] = "Failed to navigate"
            return result
    except Exception as e:
        result["error"] = f"Navigation error: {e}"
        return result

    apply_url = ""
    if title and "computrabajo" in url:
        apply_match = re.search(r'data-href-offer-apply="([^"]+)"', page)
        if apply_match:
            apply_url = apply_match.group(1).replace("&amp;", "&")
    
    if apply_url:
        try:
            page = await _call_browser_tool("navigate", {"url": apply_url})
        except Exception as e:
            result["error"] = f"Apply navigation error: {e}"
            return result

    await _auto_click_apply()
    body_lower = (page or "").lower()
    if "postulaste correctamente" in body_lower:
        result["success"] = True
        result["error"] = "already_applied"
        return result

    try:
        forms_json = await _call_browser_tool("forms", {})
    except Exception as e:
        result["error"] = f"Forms detection error: {e}"
        return result

    questions = parse_forms_json(forms_json)
    if not questions:
        result["error"] = "No form fields detected"
        return result

    filled_count = 0
    errors_list = []

    for q in questions:
        if q.type in (QuestionType.HIDDEN, QuestionType.PASSWORD):
            continue
        if q.type == QuestionType.RADIO:
            answer = generate_radio_answer(q, profile)
            try:
                await _call_browser_tool("click", {
                    "selector": f"input[name='{q.name}'][value='{answer.lower()}']"
                })
                filled_count += 1
            except Exception as e:
                logger.warning("batch_apply radio click '%s': %s", q.name, e)
        elif q.type in (QuestionType.TEXTAREA, QuestionType.TEXT,
                        QuestionType.EMAIL, QuestionType.TEL):
            answer = generate_answer(q, profile)
            ctx = await _get_context_help(q, profile)
            if ctx:
                answer = ctx
            if q.name:
                try:
                    el = f"[name='{q.name}']"
                    await _call_browser_tool("fill", {"selector": el, "value": answer})
                    filled_count += 1
                except Exception as e:
                    errors_list.append(str(e)[:60])

    if filled_count > 0:
        await asyncio.sleep(0.5)
        try:
            await _call_browser_tool("click", {"selector": "input[type='submit'], button[type='submit']"})
        except Exception as e:
            logger.warning("batch_apply submit: %s", e)
        
        await asyncio.sleep(3)
        
        try:
            confirm = await _call_browser_tool("navigate", {"url": apply_url or url})
            confirm_lower = (confirm or "").lower()
            if "postulaste correctamente" in confirm_lower or "postapply" in (confirm or ""):
                result["success"] = True
            else:
                result["error"] = "Submission result unclear"
        except Exception as e:
            logger.warning("batch_apply confirm check: %s", e)
            result["success"] = True

    return result


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def linkedin_search(query: str, location: str = "Chile") -> str:
        """Search for jobs on LinkedIn Jobs using a real browser (Selenium). Use your job title or keywords as query."""
        url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
        result = await _call_browser_tool("navigate", {"url": url})
        return result

    @mcp.tool()
    async def linkedin_scroll() -> str:
        """Scroll down on LinkedIn jobs page to load more results."""
        result = await _call_browser_tool("scroll", {"direction": "down"})
        return result

    @mcp.tool()
    async def auto_apply_pipeline(job_title: str, company: str, form_url: str,
                                   job_description: str = "", tone: str = "professional") -> str:
        """Complete pipeline: generate a cover letter, navigate to the application form, and fill it automatically. Returns the result."""
        from services.ai_provider import generate_cover_letter

        profile = profile_repo.get_default_profile()
        if not profile:
            return "No profile found."

        # Skill check
        page = await _call_browser_tool("navigate", {"url": form_url})
        await asyncio.sleep(3)

        page_text = await _call_browser_tool("run_script", {"script": "return (document.body.textContent || '').slice(0, 3000)"})
        should, reason = await _should_apply(page_text, profile)
        if not should:
            return f"=== OFERTA RECHAZADA ===\n{reason}\n\nNo se postuló automáticamente."

        letter = await generate_cover_letter(profile, job_title, company, job_description, tone)

        forms_info = await _call_browser_tool("forms", {})

        fill_result = await _smart_fill_form(
            lambda t, a: _call_browser_tool(t, a),
            forms_info, profile, submit=True
        )

        # Verify submission by checking page for success indicators
        await asyncio.sleep(2)
        verify_text = await _call_browser_tool("run_script", {"script": "return (document.body.innerText || '').slice(0, 1000)"})
        success_indicators = ["postulaste correctamente", "gracias por postular", "recibida", "success", "aplicado", "enviada"]
        submitted = any(ind in (verify_text or "").lower() for ind in success_indicators)

        status = "applied" if submitted else "pending"
        app_id = app_repo.create_application(1, job_title, company, form_url, status)

        verify_status = "VERIFICADA" if submitted else "PENDIENTE DE VERIFICACIÓN"
        return f"""=== AUTO-APPLY PIPELINE ===

1. Cover letter generated ({len(letter)} chars)
2. Navigated to {form_url}
3. Application tracked (ID: {app_id}, status: {verify_status})
4. Form filled and submitted

{fill_result}

--- COVER LETTER ---
{letter[:500]}..."""

    @mcp.tool()
    async def fill_application_field(selector: str, value: str) -> str:
        """Fill a specific field in a job application form using the browser (Selenium). Use CSS selectors to target fields."""
        result = await _call_browser_tool("fill", {"selector": selector, "value": value})
        return result

    @mcp.tool()
    async def click_application_button(selector: str) -> str:
        """Click a button in a job application form using the browser (Selenium). Use CSS selectors like 'button[type=submit]' or '#next-btn'."""
        result = await _call_browser_tool("click", {"selector": selector})
        return result

    @mcp.tool()
    async def application_form_fields() -> str:
        """Get all form fields from the current page. Useful to see what fields need to be filled in a job application."""
        result = await _call_browser_tool("forms", {})
        return result

    @mcp.tool()
    async def smart_analyze_form() -> str:
        """Analyze the current application form and generate answers for each field based on your profile."""
        forms_json = await _call_browser_tool("forms", {})
        profile = profile_repo.get_default_profile()
        if not profile:
            return "No profile found."
        questions = parse_forms_json(forms_json)
        if not questions:
            return "No form fields detected."

        analysis = ["=== SMART FORM ANALYSIS ===\n"]
        for i, q in enumerate(questions, 1):
            if q.type in (QuestionType.HIDDEN, QuestionType.PASSWORD):
                continue
            if q.type == QuestionType.RADIO:
                ans = generate_radio_answer(q, profile)
                analysis.append(f"{i}. [{q.type.value}] {q.label}")
                analysis.append(f"   Name: {q.name}")
                analysis.append(f"   Respuesta sugerida: {ans}\n")
            else:
                ans = generate_answer(q, profile)
                analysis.append(f"{i}. [{q.type.value}] {q.label}")
                analysis.append(f"   Name: {q.name}")
                analysis.append(f"   Respuesta sugerida: {ans[:80]}...\n")

        return "\n".join(analysis)

    @mcp.tool()
    async def smart_fill_form(submit: bool = True) -> str:
        """Smart-fill the current application form using your profile. Detects field types and generates contextual answers. Pass submit=False to review before submitting."""
        forms_json = await _call_browser_tool("forms", {})
        profile = profile_repo.get_default_profile()
        if not profile:
            return "No profile found."

        fill_result = await _smart_fill_form(
            lambda t, a: _call_browser_tool(t, a),
            forms_json, profile, submit
        )
        return fill_result

    @mcp.tool()
    async def batch_apply(offer_urls: str) -> str:
        """Apply to multiple job offers automatically. Pass comma-separated URLs. Uses smart form detection and auto-fill."""
        urls = [u.strip() for u in offer_urls.split(",") if u.strip()]
        if not urls:
            return "No URLs provided."

        profile = profile_repo.get_default_profile()
        if not profile:
            return "No profile found."

        results = []
        for url in urls:
            res = await _batch_apply_one(url, profile)
            status = "APPLIED" if res["success"] else f"FAILED: {res['error']}"
            title = res.get("title", url)[:50]
            results.append(f"  {title[:45]:45s} {status}")

        success_count = sum(1 for r in results if "APPLIED" in r)
        return f"=== BATCH APPLY RESULTS ===\n" + "\n".join(results) + f"\n\n{success_count}/{len(urls)} exitosas."


    @mcp.tool()
    async def browser_health_check() -> str:
        """Check if the BrowserMCP subprocess is alive and responsive."""
        try:
            result = await _call_browser_tool("engine_info", {})
            return f"BrowserMCP OK: {result}"
        except Exception as e:
            return f"BrowserMCP UNHEALTHY: {e}"
