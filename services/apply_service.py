from database.repos import applications as app_repo
from services.form_filler import (
    parse_forms_json, generate_answer, generate_radio_answer,
    generate_select_answer, QuestionType, FormQuestion
)
from services.ai_provider import _call_ai, _clean_json
import asyncio
import json
import logging
import re
from urllib.parse import urlparse, quote
from enum import Enum

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
        "content": "Eres un asistente de postulaciones muy optimista. Tu objetivo es postular al usuario a la mayor cantidad de ofertas posibles. Responde SOLO con JSON.",
        "instruction": "Determina si el usuario DEBE postular. APLICA a menos que la oferta requiera EXPLÍCITAMENTE una profesión totalmente distinta (ej: Medicina, Minería Pesada, Leyes, Ventas Retail, Comida Rápida).",
        "rules": [
            "Si la oferta es de TI, Software, Datos, Soporte o Tecnología -> apply: true",
            "Si la oferta no tiene suficiente información o es muy corta -> apply: true",
            "Si la oferta es genérica (ej. 'Trainee', 'Práctica') sin especificar área -> apply: true",
            "Si el usuario no cumple todos los requisitos pero es del área de TI -> apply: true",
            "Solo rechaza (apply: false) si claramente pide algo como 'Ingeniero Civil en Obras', 'Médico', 'Mecánico', 'Vendedor de tienda', etc."
        ],
        "profile": {
            "level": f"Estudiante/practica/junior (en curso: {current_edu})",
            "skills": skills_str,
            "experience": exp_str
        },
        "offer_text": text_snippet
    }
    prompt = json.dumps(msg, ensure_ascii=False)
    prompt = f"Analiza esta oferta de trabajo y decide si postular:\n{prompt}\n\nResponde SOLO con un JSON válido con este formato exacto:\n{{\"apply\": true/false, \"reason\": \"explicacion corta de maximo 10 palabras\"}}"

    try:
        result = await _call_ai(prompt[:3000])
        cleaned = _clean_json(result)
        parsed = json.loads(cleaned)
        return parsed.get("apply", True), parsed.get("reason", "Sin evaluación")
    except Exception as e:
        logger.warning("Skill check AI evaluation failed: %s", e)
        return True, "No se pudo evaluar la compatibilidad, se procede con postulación"


async def _fill_field_browser(driver_caller, q: FormQuestion, profile: dict, tailored_cv_path: str = None) -> tuple[int, str]:
    if q.type in (QuestionType.HIDDEN, QuestionType.PASSWORD):
        return 0, ""
    if q.type == QuestionType.FILE:
        if tailored_cv_path and q.name:
            try:
                await driver_caller("fill", {"selector": _safe_selector("input", q.name), "value": tailored_cv_path})
                return 1, f"  [{q.type.value}] {q.label[:40]} -> Uploaded CV"
            except Exception as e:
                return 0, f"File upload '{q.name}': {str(e)[:60]}"
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
                           submit: bool = True, tailored_cv_path: str = None) -> str:
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
        cnt, log = await _fill_field_browser(driver_caller, q, profile, tailored_cv_path)
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
        cnt, log = await _fill_field_browser(driver_caller, q, profile, tailored_cv_path)
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


class ApplyState(Enum):
    INIT = "INIT"
    NAVIGATING = "NAVIGATING"
    CHECK_APPLY_BTN = "CHECK_APPLY_BTN"
    DETECT_FORMS = "DETECT_FORMS"
    LOGIN = "LOGIN"
    FILL = "FILL"
    VERIFY = "VERIFY"
    END_SUCCESS = "END_SUCCESS"
    END_FAIL = "END_FAIL"


async def _batch_apply_one(url: str, profile: dict, tailored_cv_path: str = None) -> dict:
    result = {"url": url, "success": False, "title": _extract_title_from_offer_url(url), "company": "", "error": ""}
    state = ApplyState.INIT
    apply_url = ""
    forms_json = ""
    
    max_transitions = 20
    transitions = 0
    
    while state not in (ApplyState.END_SUCCESS, ApplyState.END_FAIL) and transitions < max_transitions:
        transitions += 1
        try:
            if state == ApplyState.INIT:
                state = ApplyState.NAVIGATING

            elif state == ApplyState.NAVIGATING:
                page = await asyncio.wait_for(_call_browser_tool("navigate", {"url": url}), timeout=45)
                if not page or "Error" in page:
                    result["error"] = "Failed to navigate"
                    state = ApplyState.END_FAIL
                    continue
                
                if "computrabajo" in url:
                    apply_match = re.search(r'data-href-offer-apply="([^"]+)"', page)
                    if apply_match:
                        apply_url = apply_match.group(1).replace("&amp;", "&")
                        await _call_browser_tool("navigate", {"url": apply_url})
                
                state = ApplyState.CHECK_APPLY_BTN

            elif state == ApplyState.CHECK_APPLY_BTN:
                # IMPORTANT: Read the job description BEFORE clicking Apply, 
                # because clicking Apply might redirect to a login screen.
                page_text = await _call_browser_tool("run_script", {"script": "return document.body.innerText"})
                
                should, reason = await _should_apply((page_text or "")[:3000], profile)
                if not should:
                    result["error"] = f"Job rejected by AI: {reason}"
                    state = ApplyState.END_FAIL
                    continue
                
                if "postulaste correctamente" in (page_text or "").lower():
                    result["error"] = "already_applied"
                    result["success"] = True
                    state = ApplyState.END_SUCCESS
                    continue

                # Now that AI approved, click apply
                await _auto_click_apply()
                
                state = ApplyState.DETECT_FORMS
            
            elif state == ApplyState.DETECT_FORMS:
                forms_json = await _call_browser_tool("forms", {})
                page_text = await _call_browser_tool("run_script", {"script": "return document.body.innerText"})
                curr_url = await _call_browser_tool("run_script", {"script": "return window.location.href"})
                pt_lower = (page_text or "").lower()
                
                needs_login = False
                if any(k in forms_json.lower() for k in ["login", "ingresa", "contraseña", "password"]):
                    needs_login = True
                elif any(k in pt_lower for k in ["inicia sesión", "ingresa a tu cuenta", "iniciar sesión", "entrar", "acceder"]) or "login" in str(curr_url).lower():
                    needs_login = True
                
                if needs_login:
                    state = ApplyState.LOGIN
                else:
                    state = ApplyState.FILL

            elif state == ApplyState.LOGIN:
                from services.auto_login import attempt_auto_login
                login_success = await attempt_auto_login(lambda t, a: _call_browser_tool(t, a), apply_url or url)
                if login_success:
                    await _call_browser_tool("navigate", {"url": url})
                    await asyncio.sleep(4)
                    if apply_url:
                        await _call_browser_tool("navigate", {"url": apply_url})
                        await asyncio.sleep(4)
                    state = ApplyState.CHECK_APPLY_BTN
                else:
                    result["error"] = "Login failed"
                    state = ApplyState.END_FAIL

            elif state == ApplyState.FILL:
                questions = parse_forms_json(forms_json)
                if not questions:
                    result["error"] = "No form fields detected"
                    state = ApplyState.END_FAIL
                    continue

                filled_count = 0
                for q in questions:
                    cnt, log = await _fill_field_browser(lambda t, a: _call_browser_tool(t, a), q, profile, tailored_cv_path)
                    filled_count += cnt

                if filled_count > 0:
                    await asyncio.sleep(0.5)
                    try:
                        await _call_browser_tool("click", {"selector": "input[type='submit'], button[type='submit']"})
                    except Exception as e:
                        logger.warning("submit err: %s", e)
                    await asyncio.sleep(3)
                state = ApplyState.VERIFY

            elif state == ApplyState.VERIFY:
                confirm = await _call_browser_tool("navigate", {"url": apply_url or url})
                confirm_lower = (confirm or "").lower()
                if "postulaste correctamente" in confirm_lower or "postapply" in (confirm or ""):
                    result["success"] = True
                else:
                    result["error"] = "Submission result unclear"
                    result["success"] = True # Partial success
                state = ApplyState.END_SUCCESS

        except Exception as e:
            logger.warning("State %s error: %s", state, e)
            result["error"] = f"Error in {state.name}: {e}"
            state = ApplyState.END_FAIL

    return result
