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
import re
from urllib.parse import urlparse, quote
from enum import Enum

from services.browser_client import call_tool as _call_browser_tool
from services.apply_service import _should_apply, _auto_click_apply, _smart_fill_form, _batch_apply_one


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

        # Skill check (use job_description if provided, otherwise scrape page)
        await _call_browser_tool("navigate", {"url": form_url})
        await asyncio.sleep(3)

        check_text = job_description if job_description.strip() else await _call_browser_tool("run_script", {"script": "return (document.body.textContent || '').slice(0, 3000)"})
        should, reason = await _should_apply(check_text, profile)
        if not should:
            return f"=== OFERTA RECHAZADA ===\n{reason}\n\nNo se postuló automáticamente."

        letter = await generate_cover_letter(profile, job_title, company, job_description, tone)

        # Try to click apply button if form isn't visible yet
        await _auto_click_apply()

        forms_info = await _call_browser_tool("forms", {})

        from services.cv_service import tailor_cv_pdf
        import uuid
        app_id = str(uuid.uuid4())[:8]
        tailored_cv_path = await tailor_cv_pdf(profile, check_text, f"/tmp/opencode/cv_{app_id}.pdf")

        fill_result = await _smart_fill_form(
            lambda t, a: _call_browser_tool(t, a),
            forms_info, profile, submit=True, tailored_cv_path=tailored_cv_path
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
            from services.cv_service import tailor_cv_pdf
            import uuid
            app_id = str(uuid.uuid4())[:8]
            # Fast check
            try:
                jd_text = await _call_browser_tool("run_script", {"script": "return (document.body.innerText || '').slice(0, 2000)"})
            except Exception:
                jd_text = ""
            tailored_cv_path = await tailor_cv_pdf(profile, jd_text, f"/tmp/opencode/cv_{app_id}.pdf")
            res = await _batch_apply_one(url, profile, tailored_cv_path)
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
