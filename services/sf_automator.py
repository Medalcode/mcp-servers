import asyncio
import os
import logging

from engines.selenium_engine import SeleniumEngine
from services.email_reader import EmailVerificationReader

logger = logging.getLogger(__name__)

class SuccessFactorsAutomator:
    def __init__(self, engine: SeleniumEngine):
        self.engine = engine
        self.email = os.environ.get("GMAIL_USER")
        self.password = os.environ.get("IBM_PASS", "Muneca1213##")  # Defaulting to user's master pass
        self.email_reader = EmailVerificationReader()

    async def register_account(self, base_url: str):
        """Attempts to register a new account on a SuccessFactors portal."""
        logger.info(f"Starting SF registration process for {base_url}...")
        
        # Navigate to portal
        self.engine.navigate(base_url)
        await asyncio.sleep(5)
        
        # 1. Look for "Create an account" or "Crear una cuenta"
        try:
            # Common paths for SF
            create_account_urls = [
                "a[href*='createAccount']", 
                "a[href*='register']"
            ]
            clicked = False
            for sel in create_account_urls:
                try:
                    res = self.engine.click(sel)
                    if "Error" not in res:
                        clicked = True
                        break
                except:
                    pass
            
            if not clicked:
                # Try clicking by text
                try:
                    res = self.engine.click_by_text("Crear una cuenta|Create an account")
                    if "Error" not in res:
                        clicked = True
                except:
                    pass
            
            if not clicked:
                logger.warning("Could not find 'Create account' button. Portal may not be standard SF or page didn't load.")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to registration: {e}")
            return False
            
        await asyncio.sleep(5)
        
        # 2. Fill out the registration form
        logger.info("Filling out registration form...")
        
        # We execute a JS snippet to try to fill all generic SF fields
        js_fill = f"""
        function fillIfPresent(sel, val) {{
            const el = document.querySelector(sel);
            if(el) {{
                el.value = val;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}
        fillIfPresent('input[type="email"], input[id*="email"]', '{self.email}');
        fillIfPresent('input[id*="retypedEmail"]', '{self.email}');
        fillIfPresent('input[type="password"], input[id*="password"]', '{self.password}');
        fillIfPresent('input[id*="retypedPassword"]', '{self.password}');
        fillIfPresent('input[id*="firstName"]', 'Jonatthan');
        fillIfPresent('input[id*="lastName"]', 'Medalla');
        
        // Country select
        const countrySel = document.querySelector('select[id*="country"]');
        if(countrySel) {{
            for(let i=0; i<countrySel.options.length; i++) {{
                if(countrySel.options[i].text.toLowerCase().includes('chile')) {{
                    countrySel.selectedIndex = i;
                    countrySel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    break;
                }}
            }}
        }}
        
        // Accept terms (often multiple checkboxes)
        const checkboxes = document.querySelectorAll('input[type="checkbox"], input[id*="terms"]');
        checkboxes.forEach(cb => {{
            if(!cb.checked) {{
                cb.click();
            }}
        }});
        """
        
        self.engine.run_script(js_fill)
        await asyncio.sleep(2)
        
        # Click Create Account button
        self.engine.run_script("""
        const btns = document.querySelectorAll('button');
        btns.forEach(btn => {
            const txt = btn.innerText.toLowerCase();
            if(txt.includes('crear cuenta') || txt.includes('create account') || txt.includes('register')) {
                btn.click();
            }
        });
        """)
        
        await asyncio.sleep(8)
        
        # 3. Check for verification code screen
        page_text = self.engine.run_script("return document.body.innerText") or ""
        page_lower = page_text.lower()
        
        if "código de verificación" in page_lower or "verification code" in page_lower or "pin" in page_lower:
            logger.info("Verification code required. Waiting 15s for email...")
            await asyncio.sleep(15)
            
            code = self.email_reader.fetch_latest_verification_code()
            if code:
                logger.info(f"Intercepted verification code: {code}")
                # Inject code
                self.engine.run_script(f"""
                const pinInput = document.querySelector('input[type="text"], input[id*="pin"], input[id*="code"]');
                if(pinInput) {{
                    pinInput.value = '{code}';
                    pinInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    const verifyBtn = document.querySelector('button[id*="verify"], button[id*="submit"]');
                    if(verifyBtn) verifyBtn.click();
                }}
                """)
                await asyncio.sleep(5)
            else:
                logger.warning("Could not find verification code in recent emails.")
                return False
                
        logger.info("Registration flow completed.")
        return True
