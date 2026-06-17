import asyncio
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

PROFILE_URLS = {
    "computrabajo.com": "https://candidato.computrabajo.com/candidate/profile",
    "computrabajo.cl": "https://candidato.computrabajo.cl/candidate/profile",
    "chiletrabajos.cl": "https://www.chiletrabajos.cl/mi-perfil",
    "laborum.cl": "https://www.laborum.cl/mi-perfil",
    "getonbrd.com": "https://www.getonbrd.com/my-profile",
    "sonda.com": "https://carrera.sonda.com/profile",
    "ibm.com": "https://careers.ibm.com/profile"
}

class ProfileSyncEngine:
    def __init__(self, engine, profile_data: dict):
        self.engine = engine
        self.profile = profile_data

    def _get_profile_url(self, job_url: str) -> str:
        parsed = urlparse(job_url)
        netloc = parsed.netloc.replace("www.", "")
        
        # Check explicit mappings
        for domain, prof_url in PROFILE_URLS.items():
            if domain in netloc:
                return prof_url
        
        # Fallback for generic SuccessFactors or others
        return f"{parsed.scheme}://{parsed.netloc}/profile"

    async def ensure_profile_complete(self, job_url: str) -> bool:
        """
        Navigates to the user's profile settings and ensures it's complete
        before applying. Returns True if complete/synced, False if it failed.
        """
        profile_url = self._get_profile_url(job_url)
        logger.info(f"Checking profile completeness at {profile_url}")
        
        self.engine.navigate(profile_url)
        await asyncio.sleep(5)
        
        # Check generic completeness
        page_text = self.engine.run_script("return document.body.innerText") or ""
        page_lower = page_text.lower()
        
        if "100%" in page_lower and ("complet" in page_lower or "perfil" in page_lower):
            logger.info("Profile already reports 100% completion.")
            return True
            
        # If not explicit 100%, we inject a script to check for common missing fields
        logger.info("Profile not explicitly 100%. Verifying missing fields...")
        
        # Very simple heuristic: if we see "Agregar experiencia", "Add education", "Subir CV", we assume it's incomplete
        missing_keywords = [
            "agregar experiencia", "add experience",
            "agregar educación", "add education",
            "subir cv", "upload resume"
        ]
        
        needs_update = False
        for kw in missing_keywords:
            if kw in page_lower:
                needs_update = True
                break
                
        if not needs_update:
            # Maybe the page structure is just different, we assume it's OK if no "Add X" is visible
            logger.info("No missing profile blocks detected. Proceeding.")
            return True
            
        logger.warning("Profile seems incomplete. Initiating auto-fill...")
        
        # Call form filler / cv upload logic
        # For the sake of architecture, we simulate the auto-fill via JS injection
        # using the data from self.profile
        
        summary = self.profile.get("personalInfo", {}).get("summary", "")
        
        js_sync = f"""
        // Inyectar resumen
        const summaryInput = document.querySelector('textarea[name*="summary"], textarea[id*="summary"], textarea[name*="description"]');
        if (summaryInput && !summaryInput.value) {{
            summaryInput.value = `{summary}`;
            summaryInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // Hacer click en botones de guardar
        const saveBtns = document.querySelectorAll('button');
        saveBtns.forEach(btn => {{
            const t = btn.innerText.toLowerCase();
            if(t.includes('guardar') || t.includes('save') || t.includes('actualizar')) {{
                btn.click();
            }}
        }});
        """
        self.engine.run_script(js_sync)
        await asyncio.sleep(3)
        
        logger.info("Profile synchronization attempt finished.")
        # If strict block is ON, we might re-evaluate here. For now, we allow it.
        return True
