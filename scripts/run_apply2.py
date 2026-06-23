"""Apply to Laborum Genesys and other active jobs."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool, stop_browser, ensure_browser
from database.repos import profiles as profile_repo
from tools.auto_apply_tools import _smart_fill_form, _auto_click_apply

async def safe(tool, args=None):
    r = await call_tool(tool, args or {})
    if not r or r.startswith("BrowserMCP failed"):
        return ""
    return r

async def try_laborum():
    print("\n=== LABORUM - Genesys Practicante ===")
    url = "https://www.laborum.cl/empleos/practicante-informatico-ia-area-atraccion-talentos-genesys-1118333309.html"
    
    await safe("navigate", {"url": url})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Page loaded ({len(text)} chars)")
    
    # Look for apply button
    await _auto_click_apply()
    await asyncio.sleep(4)
    
    url2 = await safe("run_script", {"script": "return window.location.href"})
    print(f"URL after click: {url2[:100]}")
    
    forms = await safe("forms", {})
    print(f"Forms: {forms[:400] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        profile = profile_repo.get_default_profile()
        print("  ✅ Filling form...")
        result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms, profile, submit=True)
        print(f"  Result: {result[:200] if result else 'empty'}")

async def try_trabajando():
    print("\n=== TRABAJANDO.COM - Trainee Protección Datos ===")
    url = "https://www.trabajando.cl/trabajo/6044587-ingeniero-trainee-proteccion-de-datos"
    
    await safe("navigate", {"url": url})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Page loaded ({len(text)} chars)")
    
    # Click "Postula ahora"
    await _auto_click_apply()
    await asyncio.sleep(4)
    
    forms = await safe("forms", {})
    print(f"Forms: {forms[:400] if forms and 'No forms' not in forms else 'none'}")
    
    if forms and "No forms" not in forms:
        profile = profile_repo.get_default_profile()
        print("  ✅ Filling form...")
        result = await _smart_fill_form(lambda t, a: safe(t, a) or "", forms, profile, submit=True)
        print(f"  Result: {result[:200] if result else 'empty'}")

async def try_iconstruye():
    print("\n=== ICONSTRUYE - Trainee Platform Engineering ===")
    url = "https://cl.trabajo.org/oferta-5486-81fb92590b02d689076dd59fe4956ae4"
    
    await safe("navigate", {"url": url})
    await asyncio.sleep(4)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Page loaded ({len(text)} chars)")
    print(f"Preview: {text[:300]}")
    
    await _auto_click_apply()
    await asyncio.sleep(4)
    
    forms = await safe("forms", {})
    print(f"Forms: {forms[:400] if forms and 'No forms' not in forms else 'none'}")

async def main():
    await ensure_browser()
    print("=== AUTO APPLY ===\n")
    
    await try_laborum()
    await try_trabajando()
    await try_iconstruye()
    
    await stop_browser()
    print("\n=== DONE ===")

asyncio.run(main())
