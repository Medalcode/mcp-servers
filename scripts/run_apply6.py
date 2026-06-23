"""Login + apply with session persistence."""
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
    
    # Login
    print("=== LOGIN ===")
    await safe("navigate", {"url": "https://www.trabajando.cl/ingresa-a-tu-cuenta"})
    await asyncio.sleep(3)
    await safe("fill", {"selector": "input[name='email']", "value": "jonatthan.medalla@gmail.com"})
    await asyncio.sleep(0.5)
    await safe("fill", {"selector": "input[type='password']", "value": "Muneca1213."})
    await asyncio.sleep(0.5)
    await safe("run_script", {"script": "document.querySelector('button[type=\"submit\"]')?.click()"})
    await asyncio.sleep(5)
    
    # Check where we ended up
    url = await safe("run_script", {"script": "return window.location.href"})
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"URL after login: {url[:100]}")
    
    if "inválido" in (text or "").lower():
        print("❌ Login failed")
        return
    
    print("✅ Logged in! Navigating to job...")
    
    # Navigate to the job offer (session cookies should persist since same browser)
    await safe("navigate", {"url": "https://www.trabajando.cl/trabajo/6044587-ingeniero-trainee-proteccion-de-datos"})
    await asyncio.sleep(5)
    
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Job page loaded, has 'Postular': {'postular' in (text or '').lower()}")
    
    # Find postular button details via JS
    btn_info = await safe("run_script", {"script": """
        const btn = document.querySelector('#applyOfferSticky');
        if (btn) {
            return 'Found btn, classes=' + btn.className + ' html=' + btn.outerHTML.substring(0, 300);
        }
        // Look for any postular button
        const all = document.querySelectorAll('button, a');
        for (const el of all) {
            const t = el.textContent.trim().toLowerCase();
            if (t.includes('postul')) {
                return 'Found: ' + el.tagName + ' id=' + el.id + ' class=' + el.className + ' html=' + el.outerHTML.substring(0, 300);
            }
        }
        return 'No postular found';
    """})
    print(f"Button info: {btn_info}")
    
    # Try clicking
    await safe("run_script", {"script": """
        const btn = document.querySelector('#applyOfferSticky') || document.querySelector('button:has(div)');
        if (btn && btn.textContent.trim().toLowerCase().includes('postul')) {
            btn.click();
            return 'Clicked';
        }
        return 'No button clicked';
    """})
    await asyncio.sleep(5)
    
    url2 = await safe("run_script", {"script": "return window.location.href"})
    print(f"URL after click: {url2[:100]}")
    
    text2 = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"After click text: {text2[:400] if text2 else 'none'}")
    
    # Turn off headless temporarily? No, let's just try harder
    # Maybe the apply button opens a new tab/window? Let's check
    windows = await safe("run_script", {"script": "return window.open('', '', '') !== null ? 'can open' : 'cannot';"})
    # Well that won't work. Let me try clicking the link href directly
    
    # Extract the actual URL from the button/link
    href = await safe("run_script", {"script": """
        const btn = document.querySelector('#applyOfferSticky');
        if (btn) {
            const parent = btn.closest('a');
            if (parent) return parent.href;
        }
        // Try to find the apply URL in the page
        const links = document.querySelectorAll('a');
        for (const a of links) {
            if (a.href && a.href.includes('postular')) return a.href;
        }
        return 'no apply link found';
    """})
    print(f"Apply URL: {href}")
    
    forms = await safe("forms", {})
    print(f"Forms: {forms[:500] if forms and 'No forms' not in forms else 'none'}")

    await stop_browser()

asyncio.run(main())
