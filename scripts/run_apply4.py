"""Apply to Trabajando.com - we're logged in now."""
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

async def apply_trabajando():
    print("=== TRABAJANDO.COM - Trainee Protección Datos ===")
    url = "https://www.trabajando.cl/trabajo/6044587-ingeniero-trainee-proteccion-de-datos"
    
    await safe("navigate", {"url": url})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Page loaded ({len(text)} chars)")
    print(f"Preview: {text[:400]}")
    
    # Click "Postula ahora" via JS
    await safe("run_script", {"script": """
        const btns = document.querySelectorAll('a, button');
        for (const btn of btns) {
            if (btn.textContent.trim().toLowerCase().includes('postula ahora')) {
                btn.click();
                return 'Clicked';
            }
        }
        return 'Not found';
    """})
    await asyncio.sleep(4)
    
    url2 = await safe("run_script", {"script": "return window.location.href"})
    print(f"URL after postular: {url2}")
    
    forms = await safe("forms", {})
    print(f"Forms: {forms[:500] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        profile = profile_repo.get_default_profile()
        result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms, profile, submit=True)
        print(f"Result: {result[:300] if result else 'empty'}")
        
        await asyncio.sleep(3)
        verify = await safe("run_script", {"script": "return document.body.innerText"})
        if verify and any(x in verify.lower() for x in ["postulaste", "gracias", "recibida", "enviada", "éxito"]):
            print("\n✅ APPLIED SUCCESSFULLY!")
        else:
            print("\n❓ May need manual check")
    
    # Also try the Nestle offer on FirstJob - but we need to login
    # Let's try applying directly
    
async def apply_direct(url, name):
    print(f"\n=== {name} ===")
    await safe("navigate", {"url": url})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Page loaded ({len(text)} chars)")
    
    # Click postular
    await safe("click_by_text", {"text": "Postular ahora|Postular|Apply|Aplicar|Iniciar postulación"})
    await asyncio.sleep(4)
    
    forms = await safe("forms", {})
    print(f"Forms: {forms[:400] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        profile = profile_repo.get_default_profile()
        result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms, profile, submit=True)
        print(f"Result: {result[:200] if result else 'empty'}")

async def main():
    await ensure_browser()
    
    # First login to Trabajando
    await safe("navigate", {"url": "https://www.trabajando.cl/ingresa-a-tu-cuenta"})
    await asyncio.sleep(3)
    await safe("fill", {"selector": "input[name='email']", "value": "jonatthan.medalla@gmail.com"})
    await asyncio.sleep(0.5)
    await safe("fill", {"selector": "input[type='password']", "value": "Muneca1213."})
    await asyncio.sleep(0.5)
    # Click submit button via JS
    await safe("run_script", {"script": """
        const btn = document.querySelector('button[type="submit"], input[type="submit"]');
        if (btn) { btn.click(); return 'Clicked'; }
        return 'Not found';
    """})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Login: {'✅' if 'inválido' not in (text or '').lower() else '❌'}")
    
    # Apply to Trainee job
    await apply_trabajando()
    
    await stop_browser()
    print("\n=== DONE ===")

asyncio.run(main())
