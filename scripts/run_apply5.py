"""Carefully apply to Trabajando.com job."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool, stop_browser, ensure_browser
from database.repos import profiles as profile_repo
from tools.auto_apply_tools import _smart_fill_form

async def safe(tool, args=None):
    r = await call_tool(tool, args or {})
    if not r or r.startswith("BrowserMCP failed"):
        return ""
    return r

async def main():
    await ensure_browser()
    
    # Login first
    print("=== LOGIN TRABAJANDO ===")
    await safe("navigate", {"url": "https://www.trabajando.cl/ingresa-a-tu-cuenta"})
    await asyncio.sleep(3)
    await safe("fill", {"selector": "input[name='email']", "value": "jonatthan.medalla@gmail.com"})
    await asyncio.sleep(0.5)
    await safe("fill", {"selector": "input[type='password']", "value": "Muneca1213."})
    await asyncio.sleep(0.5)
    await safe("run_script", {"script": "document.querySelector('button[type=\"submit\"]')?.click()"})
    await asyncio.sleep(4)
    
    # Check login
    text = await safe("run_script", {"script": "return document.body.innerText"})
    logged_in = "inválido" not in (text or "").lower()
    print(f"Status: {'✅ Logged in' if logged_in else '❌ Failed'}")
    if not logged_in:
        return
    
    # Go to job
    print("\n=== APPLYING ===")
    await safe("navigate", {"url": "https://www.trabajando.cl/trabajo/6044587-ingeniero-trainee-proteccion-de-datos"})
    await asyncio.sleep(5)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Page has 'Postula ahora': {'postula ahora' in (text or '').lower()}")
    
    # Find and click Postula ahora
    result = await safe("run_script", {"script": """
        // Try multiple strategies
        const buttons = document.querySelectorAll('a, button, span');
        for (const el of buttons) {
            const t = el.textContent.trim().toLowerCase();
            if (t === 'postula ahora' || t.includes('postula ahora')) {
                el.scrollIntoView({block: 'center'});
                el.click();
                return 'Found exact: ' + el.outerHTML.substring(0, 200);
            }
        }
        // Try partial
        for (const el of buttons) {
            const t = el.textContent.trim().toLowerCase();
            if (t.includes('postul')) {
                el.scrollIntoView({block: 'center'});
                el.click();
                return 'Found partial: ' + el.outerHTML.substring(0, 200);
            }
        }
        return 'No button found. Page HTML start: ' + document.body.innerHTML.substring(0, 500);
    """})
    print(f"Click result:\n{result}")
    await asyncio.sleep(5)
    
    url2 = await safe("run_script", {"script": "return window.location.href"})
    print(f"URL now: {url2}")
    
    text2 = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Text after click: {text2[:500] if text2 else 'none'}")
    
    forms = await safe("forms", {})
    print(f"\nForms: {forms[:500] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        profile = profile_repo.get_default_profile()
        result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms, profile, submit=True)
        print(f"Result: {result[:300] if result else 'empty'}")
        await asyncio.sleep(3)
        verify = await safe("run_script", {"script": "return document.body.innerText"})
        if verify and any(x in verify.lower() for x in ["postulaste", "gracias", "recibida", "enviada", "éxito"]):
            print("✅ APPLIED!")
    
    await stop_browser()

asyncio.run(main())
