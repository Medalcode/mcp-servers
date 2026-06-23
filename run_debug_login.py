"""Debug login flow on Trabajando.com."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool, stop_browser, ensure_browser

async def safe(tool, args=None):
    r = await call_tool(tool, args or {})
    if not r or r.startswith("BrowserMCP failed"):
        return ""
    return r

async def main():
    await ensure_browser()
    
    print("=== DEBUG LOGIN ===")
    
    # Go to login page
    await safe("navigate", {"url": "https://www.trabajando.cl/ingresa-a-tu-cuenta"})
    await asyncio.sleep(3)
    
    # Get page info
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Login page text:\n{text[:600]}\n")
    
    forms = await safe("forms", {})
    print(f"Forms:\n{forms}\n")
    
    # Fill email
    email = os.getenv("TRABAJANDO_EMAIL", "test@example.com")
    await safe("fill", {"selector": "input[name='email']", "value": email})
    await asyncio.sleep(0.5)
    
    # Fill password
    password = os.getenv("TRABAJANDO_PASSWORD", "password")
    await safe("fill", {"selector": "input[type='password']", "value": password})
    await asyncio.sleep(0.5)
    
    # Submit via JS - try multiple strategies
    print("Submitting login...")
    result = await safe("run_script", {"script": """
        // Try to find and click submit button
        const btn = document.querySelector('button[type="submit"]');
        if (btn) {
            btn.click();
            return 'Clicked submit button';
        }
        // Try form submit
        const form = document.querySelector('form');
        if (form) {
            form.submit();
            return 'Submitted form directly';
        }
        return 'No submit mechanism found';
    """})
    print(f"Submit result: {result}")
    
    await asyncio.sleep(5)
    
    url = await safe("run_script", {"script": "return window.location.href"})
    text = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"\nURL after submit: {url}")
    print(f"Text after submit:\n{text[:500]}")
    
    # Check if logged in - look for user name or logout
    if text:
        if "inválido" in text.lower():
            print("\n❌ LOGIN FAILED - invalid credentials")
        elif "Cerrar sesión" in text or "Mi cuenta" in text or "jonatthan" in text.lower():
            print("\n✅ LOGIN SUCCESSFUL!")
        else:
            print("\n❓ Unknown state")
    
    # Try to navigate to job page
    print("\n=== NAVIGATING TO JOB ===")
    await safe("navigate", {"url": "https://www.trabajando.cl/trabajo/6044587-ingeniero-trainee-proteccion-de-datos"})
    await asyncio.sleep(5)
    
    text2 = await safe("run_script", {"script": "return document.body.innerText"})
    print(f"Job page has 'Postular': {'postular' in (text2 or '').lower()}")
    
    # Try the button
    result2 = await safe("run_script", {"script": """
        // Get session info
        const cookies = document.cookie;
        const loginLinks = document.querySelectorAll('a[href*="ingresa"], a[href*="login"]');
        const userMenu = document.querySelector('[class*="user"], [class*="account"], [class*="session"]');
        return 'cookies: ' + cookies.substring(0, 100) + 
               ' | loginLinks: ' + loginLinks.length + 
               ' | userMenu: ' + (userMenu ? userMenu.textContent.trim().substring(0,50) : 'none');
    """})
    print(f"Session check: {result2}")

    await stop_browser()

asyncio.run(main())
