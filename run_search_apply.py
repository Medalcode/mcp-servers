"""Search for trainee/intern jobs and try to apply."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool as browser, stop_browser, ensure_browser

OFFER_URLS = [
    # GetOnBoard - needs login first then apply
    ("GetOnBoard AgendaPro", "https://www.getonbrd.com/jobs/customer-support/ejecutivo-de-soporte-trainee-agendapro-santiago-b27f/applications/new"),
    ("GetOnBoard BC Tech", "https://www.getonbrd.com/empleos/ingenieria-informatica/analista-de-automatizacion-y-datos-bc-tecnologia-santiago/applications/new"),
    # SONDA via SuccessFactors - may work with existing account
    ("SONDA Fresh Graduates", "https://career5.successfactors.eu/career?career_company=sonda&career_job_req_id=6889&company=sonda&lang=en_US&job_location=chile&navBarLevel=JOB_SEARCH&selected_lang=en_US"),
    ("SONDA Internship", "https://career5.successfactors.eu/career?career_company=sonda&career_job_req_id=6897&company=sonda&lang=en_US&job_location=chile&navBarLevel=JOB_SEARCH&selected_lang=en_US"),
    ("SONDA Analista Funcional", "https://career5.successfactors.eu/career?career_company=sonda&career_job_req_id=6894&company=sonda&lang=en_US&job_location=chile&navBarLevel=JOB_SEARCH&selected_lang=en_US"),
    # LinkedIn Easy Apply jobs
    ("LinkedIn Trainee search", "https://www.linkedin.com/jobs/search/?keywords=trainee%20informatica&location=Chile"),
]

async def main():
    await ensure_browser()
    print("=== EXPLORING JOB OFFERS ===\n")

    for name, url in OFFER_URLS[:3]:  # First 3 to start
        print(f"\n--- {name} ---")
        result = await browser("navigate", {"url": url})
        await asyncio.sleep(4)
        
        text = await browser("run_script", {"script": "return document.body.innerText"})
        print(f"  Page: {text[:400]}")
        
        url_current = await browser("run_script", {"script": "return window.location.href"})
        print(f"  URL: {url_current[:100]}")
        
        forms = await browser("forms", {})
        print(f"  Forms: {forms[:300] if forms and 'No forms' not in forms else 'none'}")

    print("\n=== DONE ===")
    await stop_browser()

asyncio.run(main())
