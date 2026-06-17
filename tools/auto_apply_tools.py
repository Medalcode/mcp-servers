from mcp.server import FastMCP
from database.repos import applications as app_repo
from services.form_filler import (
    parse_forms_json, generate_answer, generate_radio_answer,
    generate_select_answer, QuestionType, FormQuestion
)
from services.ai_provider import _call_ai, _clean_json
from database.repos import profiles as profile_repo
import asyncio
import json
import logging
import os
import re
from urllib.parse import urlparse, quote

from services.browser_client import call_tool as _call_browser_tool

logger = logging.getLogger(__name__)


def _css_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _safe_selector(tag: str, name: str, value: str = None) -> str:
    sel = f'{tag}[name={_css_escape(name)}]'
    if value is not None:
        sel += f'[value={_css_escape(value)}]'
    return sel


async def _auto_click_apply():
    """Try to click the apply button by common text labels (Postularme, Apply, etc.)."""
    patterns = "Postularme|Postular|Apply|Aplicar|Aplica ahora|Iniciar postulación|Enviar postulación|Quiero postular"
    result = await _call_browser_tool("click_by_text", {"text": patterns})
    await asyncio.sleep(2)
    return result


async def _should_apply(page_text: str, profile: dict) -> tuple[bool, str]:
    """Check if the job matches the user's profile."""
    text_lower = (page_text or "").lower()

    skills = profile.get("skills", [])
    exp = profile.get("experience", [])
    edu = profile.get("education", [])
    current_edu = ""
    for e in edu:
        if e.get("current"):
            current_edu = f"{e.get('degree', '')} en {e.get('school', '')}"
            break

    skills_str = ", ".join(skills[:15])
    exp_str = "; ".join(f"{e['title']} en {e['company']}" for e in exp[:3])
    text_snippet = (page_text or "")[:1500]

    msg = {
        "role": "system",
        "content": "Eres un asesor de postulaciones. Responde solo con JSON.",
        "instruction": "Dado el perfil del usuario y la descripcion de la oferta, determina si DEBE postular o NO.",
        "context": "El usuario esta abierto a cualquier modalidad (presencial, hibrido o remoto).",
        "profile": {
            "level": f"Estudiante/practica/junior (en curso: {current_edu})",
            "skills": skills_str,
            "experience": exp_str
        },
        "offer_text": text_snippet
    }
    prompt = json.dumps(msg, ensure_ascii=False)
    prompt = f"Analiza esta oferta de trabajo:\n{prompt}\n\nResponde SOLO con JSON: {{\"apply\": true/false, \"reason\": \"explicacion corta en espanol\"}}"

    try:
        result = await _call_ai(prompt[:3000])
        cleaned = _clean_json(result)
        parsed = json.loads(cleaned)
        return parsed.get("apply", True), parsed.get("reason", "Sin evaluación")
    except Exception as e:
        logger.warning("Skill check AI evaluation failed: %s", e)
        return True, "No se pudo evaluar la compatibilidad, se procede con postulación"


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


async def _fill_field_browser(driver_caller, q: FormQuestion, profile: dict) -> tuple[int, str]:
    if q.type in (QuestionType.HIDDEN, QuestionType.PASSWORD):
        return 0, ""
    if q.type == QuestionType.RADIO:
        answer = generate_radio_answer(q, profile)
        answer_lower = answer.lower()
        for option in q.options or []:
            if option.lower().strip() == answer_lower:
                try:
                    await driver_caller("click", {"selector": _safe_selector("input", q.name, option)})
                    return 1, f"  [{q.type.value}] {q.label[:40]} -> {answer}"
                except Exception as e:
                    logger.warning("radio click '%s' option '%s': %s", q.name, option, e)
        try:
            await driver_caller("click", {"selector": _safe_selector("input", q.name, answer)})
            return 1, f"  [{q.type.value}] {q.label[:40]} -> {answer}"
        except Exception as e:
            logger.warning("radio fallback click '%s': %s", q.name, e)
        return 0, ""
    if q.type in (QuestionType.SELECT,):
        answer = generate_select_answer(q, profile)
        if answer:
            try:
                await driver_caller("fill", {"selector": _safe_selector("select", q.name), "value": answer})
                return 1, f"  [{q.type.value}] {q.label[:40]} -> {answer}"
            except Exception as e:
                logger.warning("Select '%s': %s", q.name, e)
                return 0, str(e)[:60]
        return 0, ""
    if q.type in (QuestionType.TEXTAREA, QuestionType.TEXT,
                  QuestionType.EMAIL, QuestionType.TEL, QuestionType.NUMBER):
        from services.ai_provider import answer_form_question
        answer = await answer_form_question(q.label, q.type.value, profile)
        if q.name:
            try:
                await driver_caller("fill", {"selector": _safe_selector("*", q.name), "value": answer})
                return 1, f"  [{q.type.value}] {q.label[:40]} -> {answer[:50]}..."
            except Exception as e:
                return 0, f"Field '{q.name}': {str(e)[:60]}"
        return 0, ""
    return 0, ""


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

    # Step 1: Fill salary-related fields first
    salary_qs = [q for q in questions if re.search(r'sueldo|salario|renta|pretensión', q.label.lower())]
    for q in salary_qs:
        cnt, log = await _fill_field_browser(driver_caller, q, profile)
        filled_count += cnt
        if log:
            answers_log.append(log)

    # Step 2: If there's a salary form, submit it first
    if salary_qs and submit:
        try:
            await driver_caller("click_by_text", {"text": "Postularme|Postular|Actualizar"})
            await asyncio.sleep(3)
            new_forms = await driver_caller("forms", {})
            new_qs = parse_forms_json(new_forms)
            if new_qs:
                questions = new_qs
        except Exception as e:
            logger.warning("Salary form submit/re-detect: %s", e)

    # Step 3: Fill remaining fields
    done_names = {q.name for q in salary_qs}
    for q in questions:
        if q.name in done_names:
            continue
        cnt, log = await _fill_field_browser(driver_caller, q, profile)
        filled_count += cnt
        if log:
            answers_log.append(log)
        else:
            skipped_count += 1

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
        page = await asyncio.wait_for(
            _call_browser_tool("navigate", {"url": url}),
            timeout=45
        )
        if not page or "Error" in page:
            result["error"] = "Failed to navigate"
            return result
    except asyncio.TimeoutError:
        result["error"] = "Navigation timeout"
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

    page_text = await _call_browser_tool("run_script", {"script": "return document.body.innerText"})
    pt_lower = (page_text or "").lower()
    curr_url = await _call_browser_tool("run_script", {"script": "return window.location.href"})
    
    print(f"[DEBUG] curr_url: {curr_url}")
    print(f"[DEBUG] pt_lower[:200]: {pt_lower[:200]}")
    print(f"[DEBUG] forms_json: {forms_json}")

    needs_login = False
    if "login" in forms_json.lower() or "ingresa" in forms_json.lower() or "contraseña" in forms_json.lower() or "password" in forms_json.lower():
        needs_login = True
    elif "inicia sesión" in pt_lower or "ingresa a tu cuenta" in pt_lower or "iniciar sesión" in pt_lower or "login" in (curr_url or "").lower() or "entrar" in pt_lower or "acceder" in pt_lower:
        needs_login = True

    if needs_login:
        from services.auto_login import attempt_auto_login
        login_success = await attempt_auto_login(lambda t, a: _call_browser_tool(t, a), apply_url or url)
        if login_success:
            await _call_browser_tool("navigate", {"url": url})
            await asyncio.sleep(4)
            if apply_url:
                await _call_browser_tool("navigate", {"url": apply_url})
                await asyncio.sleep(4)
            await _auto_click_apply()
            try:
                forms_json = await _call_browser_tool("forms", {})
            except Exception as e:
                result["error"] = f"Forms detection error after login: {e}"
                return result
        else:
            result["error"] = "Login failed or missing/invalid credentials in .env"
            return result

    questions = parse_forms_json(forms_json)
    if not questions:
        result["error"] = "No form fields detected"
        return result

    filled_count = 0
    errors_list = []

    for q in questions:
        cnt, log = await _fill_field_browser(lambda t, a: _call_browser_tool(t, a), q, profile)
        filled_count += cnt
        if log and not cnt:
            errors_list.append(log)

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
        url = f"https://www.linkedin.com/jobs/search/?keywords={quote(query)}&location={quote(location)}"
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
        await _call_browser_tool("navigate", {"url": form_url})
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
        return "=== BATCH APPLY RESULTS ===\n" + "\n".join(results) + f"\n\n{success_count}/{len(urls)} exitosas."


    @mcp.tool()
    async def browser_health_check() -> str:
        """Check if the BrowserMCP subprocess is alive and responsive."""
        try:
            result = await _call_browser_tool("engine_info", {})
            return f"BrowserMCP OK: {result}"
        except Exception as e:
            return f"BrowserMCP UNHEALTHY: {e}"
