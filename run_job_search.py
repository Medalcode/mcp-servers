"""Job search + apply using browser client directly."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool, stop_browser, ensure_browser
from database.repos import profiles as profile_repo
from tools.auto_apply_tools import _smart_fill_form, _auto_click_apply

OFFERS = [
    ("FirstJob QA", "https://firstjob.me/oferta/55131/practica-profesional-qa"),
    ("FirstJob Datos", "https://firstjob.me/oferta/55120/practica-profesional-gobierno-de-datos"),
    ("GetOnBoard AgendaPro", "https://www.getonbrd.com/jobs/customer-support/ejecutivo-de-soporte-trainee-agendapro-santiago-b27f"),
    ("GetOnBoard BC Tech", "https://www.getonbrd.com/empleos/ingenieria-informatica/analista-de-automatizacion-y-datos-bc-tecnologia-santiago"),
]

async def safe(tool, args=None):
    r = await call_tool(tool, args or {})
    if not r or r.startswith("BrowserMCP failed"):
        return ""
    return r

async def try_apply(name, url):
    print(f"\n{'='*60}")
    print(f"📋 {name}")
    print(f"   {url}")
    print(f"{'='*60}")
    
    body = await safe("navigate", {"url": url})
    if not body:
        print("   ❌ Could not load page")
        return
    print("   ✅ Page loaded")
    
    # Extract page text
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"   Page text: {len(text)} chars")
    
    # Try clicking apply
    await _auto_click_apply()
    await asyncio.sleep(3)
    
    url2 = await safe("run_script", {"script": "return window.location.href"})
    print(f"   Current URL: {url2[:80]}")
    
    forms = await safe("forms", {})
    print(f"   Forms detected: {'✅' if forms and 'No forms' not in forms else '❌'}")
    if forms:
        print(f"   Forms: {forms[:400]}")
    
    # If login page, try login
    text2 = await safe("run_script", {"script": "return document.body.innerText"})
    if text2 and ("Iniciar Sesión" in text2 or "iniciar sesión" in text2.lower()):
        print("   🔐 Login/Register page detected")
        
        # Try "Iniciar Sesión" link
        await safe("click_by_text", {"text": "Iniciar Sesión"})
        await asyncio.sleep(3)
        
        url3 = await safe("run_script", {"script": "return window.location.href"})
        print(f"   Login URL: {url3}")
        
        forms2 = await safe("forms", {})
        print(f"   Login forms: {forms2[:400] if forms2 else 'none'}")
        
        # Auto-fill login if email/password fields detected
        if forms2 and "user[email]" in forms2:
            print("   🔑 Filling login...")
            email = os.getenv("GETONBOARD_EMAIL", "test@example.com")
            password = os.getenv("GETONBOARD_PASSWORD", "password")
            await safe("fill", {"selector": "input[name='user[email]']", "value": email})
            await asyncio.sleep(0.5)
            await safe("fill", {"selector": "input[name='user[password]']", "value": password})
            await asyncio.sleep(0.5)
            await safe("click", {"selector": "input[name='commit']"})
            await asyncio.sleep(4)
            
            text3 = await safe("run_script", {"script": "return document.body.innerText"})
            if text3 and "inválido" not in text3.lower() and "atención" not in text3.lower():
                print("   ✅ Login success! Returning to offer...")
                await safe("navigate", {"url": url})
                await asyncio.sleep(3)
                
                # Try applying again
                await _auto_click_apply()
                await asyncio.sleep(3)
                
                forms3 = await safe("forms", {})
                if forms3 and "No forms" not in forms3:
                    print("   ✅ Application form found!")
                    result = await _smart_fill_form(
                        lambda t, a: safe(t, a) or "",
                        forms3, profile_repo.get_default_profile(), submit=True
                    )
                    print(f"   Result: {result[:200]}")
                else:
                    print("   ❌ No form after login")
            else:
                print(f"   ❌ Login failed: {text3[:200] if text3 else 'no text'}")
    
    # If application form found directly
    elif forms and "No forms" not in forms:
        print("   ✅ Filling application form...")
        result = await _smart_fill_form(
            lambda t, a: safe(t, a) or "",
            forms, profile_repo.get_default_profile(), submit=True
        )
        print(f"   Result: {result[:200]}")
    
    await asyncio.sleep(2)

async def main():
    await ensure_browser()
    print("=== JOB APPLY BOT ===\n")
    
    for name, url in OFFERS:
        try:
            await try_apply(name, url)
        except Exception as e:
            print(f"   ❌ Error: {e}")
        await asyncio.sleep(2)
    
    await stop_browser()
    print("\n=== DONE ===")

asyncio.run(main())
