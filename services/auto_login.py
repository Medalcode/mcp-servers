import os
import asyncio
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Map domains to their .env prefix
DOMAIN_MAP = {
    "getonboard.com": "GETONBOARD",
    "computrabajo.com": "COMPUTRABAJO",
    "computrabajo.cl": "COMPUTRABAJO",
    "laborum.cl": "LABORUM",
    "chiletrabajos.cl": "CHILETRABAJOS",
    "trabajando.cl": "TRABAJANDO",
    "indeed.com": "INDEED",
    "indeed.cl": "INDEED",
    "sonda.com": "SONDA",
    "ibm.com": "IBM",
}

async def attempt_auto_login(driver_caller, url: str) -> bool:
    """
    Attempts to log in to the portal matching the URL.
    Returns True if login was attempted and seems successful, False otherwise.
    """
    domain = urlparse(url).netloc.lower()
    prefix = None
    for d, p in DOMAIN_MAP.items():
        if d in domain:
            prefix = p
            break
            
    if not prefix:
        logger.warning(f"Auto-login not supported for domain: {domain}")
        return False
        
    user = os.getenv(f"{prefix}_USER")
    password = os.getenv(f"{prefix}_PASS")
    
    if not user or not password:
        logger.warning(f"Credentials not found in .env for {prefix} ({prefix}_USER, {prefix}_PASS).")
        return False
        
    logger.info(f"Attempting auto-login for {prefix}...")
    
    # Wait for page to settle
    await asyncio.sleep(2)
    
    try:
        # Identify user field
        user_selectors = ["input[type='email']", "input[name*='email']", "input[name*='user']", "#email", "#username"]
        user_filled = False
        for sel in user_selectors:
            try:
                res = await driver_caller("fill", {"selector": sel, "value": user})
                if "Error" not in res:
                    user_filled = True
                    break
            except Exception:
                continue
                
        # Identify password field
        pass_selectors = ["input[type='password']", "input[name*='pass']", "#password", "#pwd"]
        pass_filled = False
        for sel in pass_selectors:
            try:
                res = await driver_caller("fill", {"selector": sel, "value": password})
                if "Error" not in res:
                    pass_filled = True
                    break
            except Exception:
                continue
        
        if not (user_filled and pass_filled):
            logger.warning(f"Could not find or fill login fields for {prefix}")
            return False

        # Submit
        clicked = False
        try:
            res = await driver_caller("click_by_text", {"text": "Ingresar|Entrar|Log in|Inicia sesión|Iniciar sesión|Continuar"})
            if "Clicked" in res:
                clicked = True
        except Exception:
            pass
            
        if not clicked:
            submit_selectors = ["button[type='submit']", "input[type='submit']", "form button"]
            for sel in submit_selectors:
                try:
                    res = await driver_caller("click", {"selector": sel})
                    if "Error" not in res:
                        break
                except Exception:
                    continue
                    
        # Wait for redirect/login processing
        await asyncio.sleep(5)
        
        # Verify success (check if still on login by looking for password field or error message)
        page_text = await driver_caller("run_script", {"script": "return document.body.innerText"})
        page_lower = (page_text or "").lower()
        if "contraseña incorrecta" in page_lower or "credenciales inválidas" in page_lower or "incorrect password" in page_lower:
            logger.error(f"Login failed for {prefix}: Incorrect credentials.")
            return False
            
        logger.info(f"Auto-login for {prefix} completed.")
        return True
            
    except Exception as e:
        logger.error(f"Auto-login error on {prefix}: {e}")
        
    return False
