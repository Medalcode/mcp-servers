"""Register on FirstJob - JS click for terms."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool as browser, ensure_browser

async def main():
    await ensure_browser()

    print("=== FIRSTJOB REGISTER ===")
    
    await browser("navigate", {"url": "https://firstjob.me/usuarios/registro/nueva_cuenta"})
    await asyncio.sleep(3)

    # Fill fields
    await browser("fill", {"selector": "input[name='user[email]']", "value": "jonatthan.medalla@gmail.com"})
    await asyncio.sleep(0.5)
    await browser("fill", {"selector": "input[name='user[password]']", "value": "Muneca1213."})
    await asyncio.sleep(0.5)
    await browser("fill", {"selector": "input[name='user[password_confirmation]']", "value": "Muneca1213."})
    await asyncio.sleep(0.5)
    
    # Check terms via JavaScript (direct DOM click)
    result = await browser("run_script", {"script": """
        const cb = document.querySelector('input[name=\"user[terms]\"]');
        if (cb) {
            // Try direct click
            cb.click();
            // Also dispatch change event
            cb.dispatchEvent(new Event('change', {bubbles: true}));
            // Set checked property directly
            cb.checked = true;
            return 'Terms checkbox found, clicked, checked=' + cb.checked;
        }
        return 'Terms checkbox NOT found';
    """})
    print(f"  Terms: {result}")
    await asyncio.sleep(0.5)

    # Check marketing checkbox via JS
    await browser("run_script", {"script": """
        const cb = document.querySelector('input[name=\"user[email_marketing]\"]');
        if (cb) {
            cb.checked = true;
            cb.dispatchEvent(new Event('change', {bubbles: true}));
        }
    """})
    await asyncio.sleep(0.5)

    # Click submit via JS
    await browser("run_script", {"script": """
        const btn = document.querySelector('input[name=\"commit\"]');
        if (btn) {
            btn.click();
            return 'Clicked submit';
        }
        return 'Submit button not found';
    """})
    await asyncio.sleep(5)

    url = await browser("run_script", {"script": "return window.location.href"})
    text = await browser("run_script", {"script": "return document.body.innerText"})
    print(f"URL: {url}")
    print(f"Result:\n{text[:500]}")
    
    if "bienvenido" in text.lower() or "confirmación" in text.lower() or "gracias" in text.lower() or "/oferta" in url:
        print("\n✅ REGISTERED! Now applying...")
        await apply_to_offers()
    elif "aceptar los términos" in text.lower():
        print("\n❌ Terms still not accepted")
        # Debug: check checkbox state
        debug = await browser("run_script", {"script": """
            const cb = document.querySelector('input[name="user[terms]"]');
            return cb ? 'exists checked=' + cb.checked + ' type=' + cb.type + ' display=' + 
                getComputedStyle(cb).display + ' visibility=' + getComputedStyle(cb).visibility : 'not found';
        """})
        print(f"  Debug terms: {debug}")
        
        # Try clicking the label instead
        await browser("run_script", {"script": """
            const labels = document.querySelectorAll('label');
            for (const l of labels) {
                if (l.textContent.includes('términos')) {
                    l.click();
                    return 'Clicked label: ' + l.textContent.trim();
                }
            }
            return 'No label found';
        """})
        await asyncio.sleep(1)
        
        # Retry submit
        await browser("run_script", {"script": """
            document.querySelector('input[name="commit"]').click();
        """})
        await asyncio.sleep(5)
        
        url2 = await browser("run_script", {"script": "return window.location.href"})
        text2 = await browser("run_script", {"script": "return document.body.innerText"})
        print(f"URL: {url2}")
        print(f"Result: {text2[:500]}")
    else:
        print(f"\n❌ Registration failed - unexpected response")

    print("\n=== DONE ===")

async def apply_to_offers():
    from database.repos import profiles as profile_repo
    from tools.auto_apply_tools import _smart_fill_form
    
    profile = profile_repo.get_default_profile()
    offers = [
        ("https://firstjob.me/oferta/55131/practica-profesional-qa", "Práctica Profesional QA - Ripley"),
        ("https://firstjob.me/oferta/55120/practica-profesional-gobierno-de-datos", "Práctica Profesional Gobierno de Datos - Ripley"),
    ]
    
    for url, title in offers:
        print(f"\n--- Applying to: {title} ---")
        await browser("navigate", {"url": url})
        await asyncio.sleep(4)
        
        # Click Postular
        await browser("run_script", {"script": """
            const els = document.querySelectorAll('a, button, span, div, input');
            for (const el of els) {
                if (el.textContent.trim() === 'Postular' && el.offsetParent !== null) {
                    el.scrollIntoView({behavior: 'instant', block: 'center'});
                    el.click();
                    return 'Clicked';
                }
            }
            return 'Not found';
        """})
        await asyncio.sleep(5)
        
        forms = await browser("forms", {})
        print(f"Forms: {forms[:500] if forms else 'NONE'}")
        
        if forms and "NONE" not in forms:
            result = await _smart_fill_form(
                lambda t, a: browser(t, a),
                forms, profile, submit=True
            )
            print(f"Fill: {result[:200]}")
            await asyncio.sleep(3)
            
            verify = await browser("run_script", {"script": "return document.body.innerText"})
            if any(x in verify.lower() for x in ["postulaste", "gracias", "recibida", "enviada"]):
                print(f"✅ {title} - APPLIED!")
            else:
                print(f"❓ {title} - may need manual check")

asyncio.run(main())
