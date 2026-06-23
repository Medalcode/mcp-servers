"""Log into FirstJob and apply."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool as browser, ensure_browser
from database.repos import profiles as profile_repo
from tools.auto_apply_tools import _smart_fill_form

async def click_postular():
    result = await browser("run_script", {"script": """
        const els = document.querySelectorAll('a, button, span, div, input');
        for (const el of els) {
            if (el.textContent.trim() === 'Postular' && el.offsetParent !== null) {
                el.scrollIntoView({behavior: 'instant', block: 'center'});
                el.click();
                return 'Clicked: ' + el.tagName;
            }
        }
        // Try partial match
        for (const el of els) {
            if (el.textContent.trim().toLowerCase().includes('postular') && el.offsetParent !== null) {
                el.scrollIntoView({behavior: 'instant', block: 'center'});
                el.click();
                return 'Clicked (partial): ' + el.tagName + ' - ' + el.textContent.trim().substring(0,50);
            }
        }
        return 'Not found';
    """})
    print(f"  {result}")
    return "Clicked" in (result or "")

async def main():
    profile = profile_repo.get_default_profile()
    if not profile:
        print("No profile found")
        return

    await ensure_browser()

    print("=== FIRSTJOB AUTO APPLY ===")
    print("[1] Navigating to login...")
    await browser("navigate", {"url": "https://firstjob.me/usuarios/ingresar"})
    await asyncio.sleep(3)

    print("[2] Filling login form...")
    await browser("fill", {"selector": "input[name='user[email]']", "value": "jonatthan.medalla@gmail.com"})
    await asyncio.sleep(1)
    await browser("fill", {"selector": "input[name='user[password]']", "value": "Muneca1213."})
    await asyncio.sleep(1)
    await browser("click", {"selector": "input[name='commit']"})
    await asyncio.sleep(4)

    text = await browser("run_script", {"script": "return document.body.innerText"})
    if "Bienvenid" in text:
        # Check for error messages
        print(f"  Login result:\n{text[:400]}")
        
        if "email o contraseña" in text.lower() or "inválido" in text.lower():
            print("  LOGIN FAILED - wrong credentials")
            # Maybe the user doesn't have an account yet
            print("[3] Trying to register instead...")
            await browser("navigate", {"url": "https://firstjob.me/usuarios/registro"})
            await asyncio.sleep(3)
            reg_text = await browser("run_script", {"script": "return document.body.innerText"})
            print(f"  Register page:\n{reg_text[:500]}")
            forms = await browser("forms", {})
            print(f"  Register forms: {forms[:800] if forms else 'NONE'}")
    else:
        print("  Login seems successful!")
    
    # Try the offer
    print("\n[3] Navigating to offer...")
    await browser("navigate", {"url": "https://firstjob.me/oferta/55131/practica-profesional-qa"})
    await asyncio.sleep(4)

    print("[4] Clicking Postular...")
    await click_postular()
    await asyncio.sleep(4)

    url = await browser("run_script", {"script": "return window.location.href"})
    text = await browser("run_script", {"script": "return document.body.innerText"})
    print(f"  URL: {url}")
    print(f"  Text snippet: {text[:500]}")

    forms = await browser("forms", {})
    print(f"  Forms: {forms[:800] if forms else 'NONE'}")
    
    if forms and "NONE" not in forms:
        print("\n[5] Filling application form...")
        result = await _smart_fill_form(
            lambda t, a: browser(t, a),
            forms, profile, submit=True
        )
        print(f"  Fill result: {result[:300] if result else 'empty'}")
        
        await asyncio.sleep(3)
        verify = await browser("run_script", {"script": "return document.body.innerText"})
        success = any(x in verify.lower() for x in ["postulaste", "gracias", "recibida", "enviada"])
        print(f"\n{'✅ APPLIED!' if success else '❌ May need manual check'}")

    print("\n=== DONE ===")

asyncio.run(main())
