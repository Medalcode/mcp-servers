import urllib.parse
import httpx
import logging
from bs4 import BeautifulSoup
import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

async def scan_sonda(query: str, location: str = "Chile") -> list:
    """Scrape job postings from SONDA Careers (SAP SuccessFactors)."""
    params = {"q": query, "locationsearch": location}
    url = f"https://carrera.sonda.com/search/?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f"SONDA request failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for row in soup.select("tr.data-row"):
        try:
            title_el = row.select_one("a.jobTitle-link")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_rel = title_el.get("href", "")
            job_url = f"https://carrera.sonda.com{url_rel}" if url_rel.startswith("/") else url_rel

            loc_el = row.select_one(".jobLocation")
            loc = loc_el.get_text(strip=True) if loc_el else location
            
            dept_el = row.select_one(".jobDepartment, .jobFacility")
            dept = dept_el.get_text(strip=True) if dept_el else "General"

            jobs.append({
                "title": title,
                "company": "SONDA",
                "location": loc,
                "url": job_url,
                "description": dept,
                "source": "carrera.sonda.com",
            })
        except Exception as e:
            logger.warning(f"SONDA parse error: {e}")
            continue

    return jobs
