"""Try to register/login on job portals and apply."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool, stop_browser, ensure_browser
from database.repos import profiles as profile_repo
from tools.auto_apply_tools import _smart_fill_form

EMAIL = "jonatthan.medalla@gmail.com"
PASSWORD = "Muneca1213."

async def safe(tool, args=None):
    r = await call_tool(tool, args or {})
    if not r or r.startswith("BrowserMCP failed"):
        return ""
    return r

async def register_trabajando():
    print("\n=== TRABAJANDO.COM - Register & Apply ===")
    
    # Go to login page
    await safe("navigate", {"url": "https://www.trabajando.cl/ingresa-a-tu-cuenta"})
    await asyncio.sleep(4)
    
    # Try login with known credentials
    print("  Trying login...")
    await safe("fill", {"selector": "input[name='email']", "value": EMAIL})
    await asyncio.sleep(1)
    await safe("fill", {"selector": "input[type='password']", "value": PASSWORD})
    await asyncio.sleep(1)
    
    # Click submit
    await safe("click", {"selector": "button[type='submit'], input[type='submit'], button:has-text('Ingresar')"})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    if text and "inválido" not in text.lower() and "error" not in text.lower()[:50]:
        print("  ✅ Login successful!")
    else:
        print(f"  ❌ Login failed: {text[:200] if text else 'no text'}")

async def try_geely():
    print("\n=== GEELY - Practicante TI (PUCV) ===")
    url = "https://empleosypracticas.pucv.cl/trabajar-en-geely-motor-chile/trabajos/practicante-ti-bi-automatizacion-e-integraciones/832561"
    
    await safe("navigate", {"url": url})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"  Page loaded ({len(text)} chars)")
    print(f"  Preview: {text[:300]}")
    
    await safe("click_by_text", {"text": "Postular ahora|Postular|Apply"})
    await asyncio.sleep(4)
    
    forms = await safe("forms", {})
    print(f"  Forms: {forms[:400] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        profile = profile_repo.get_default_profile()
        result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms, profile, submit=True)
        print(f"  Result: {result[:200] if result else 'empty'}")

async def try_nestle_firstjob():
    print("\n=== NESTLE (FirstJob) - Register & Apply ===")
    
    # Try registering on FirstJob
    await safe("navigate", {"url": "https://firstjob.me/usuarios/registro/nueva_cuenta"})
    await asyncio.sleep(4)
    
    forms = await safe("forms", {})
    print(f"  Register forms: {forms[:500] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        # Fill registration
        await safe("fill", {"selector": "input[name='user[email]']", "value": EMAIL})
        await asyncio.sleep(0.5)
        await safe("fill", {"selector": "input[name='user[password]']", "value": PASSWORD})
        await asyncio.sleep(0.5)
        await safe("fill", {"selector": "input[name='user[password_confirmation]']", "value": PASSWORD})
        await asyncio.sleep(0.5)
        
        # Check terms via JS
        await safe("run_script", {"script": """
            const cb = document.querySelector('input[name="user[terms]"]');
            if (cb) { cb.checked = true; cb.dispatchEvent(new Event('change', {bubbles: true})); }
        """})
        await asyncio.sleep(0.5)
        
        # Submit
        await safe("click", {"selector": "input[name='commit']"})
        await asyncio.sleep(5)
        
        url2 = await safe("run_script", {"script": "return window.location.href"})
        text2 = await safe("run_script", {"script": "return document.body.innerText"})
        print(f"  After register: {url2}")
        print(f"  Text: {text2[:300] if text2 else 'none'}")
        
        if "bienvenido" in (text2 or "").lower() or "confirmación" in (text2 or "").lower():
            print("  ✅ Registered!")
            # Now apply
            await safe("navigate", {"url": "https://firstjob.me/oferta/55080/practicante-de-informatica-y-procesos-digitales-nestle-cd-macul"})
            await asyncio.sleep(4)
            await safe("click_by_text", {"text": "Postular"})
            await asyncio.sleep(4)
            forms2 = await safe("forms", {})
            if forms2 and "No forms" not in forms2:
                profile = profile_repo.get_default_profile()
                result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms2, profile, submit=True)
                print(f"  Apply result: {result[:200]}")
        else:
            print("  ❌ Registration blocked (CAPTCHA or terms)")

async def main():
    await ensure_browser()
    print("=== JOB APPLY BOT ===\n")
    
    await register_trabajando()
    await try_geely()
    await try_nestle_firstjob()
    
    await stop_browser()
    print("\n=== DONE ===")

asyncio.run(main())
