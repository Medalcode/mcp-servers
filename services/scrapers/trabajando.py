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


async def scan_trabajando(query: str, location: str = "Chile", filters: dict = None) -> list:
    params = {"q": query, "l": location}
    url = f"https://www.trabajando.com/cl/ofertas-de-trabajo?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Trabajando request failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for card in soup.select("article.oferta, div.oferta, div[class*=oferta], div.job-item, tr.oferta"):
        try:
            title_el = card.select_one("h2 a, h3 a, a[href*='/oferta/']")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_rel = title_el.get("href", "")
            job_url = url_rel if url_rel.startswith("http") else f"https://www.trabajando.cl{url_rel}"

            company = card.select_one(".empresa, .company, [class*=empresa]")
            company = company.get_text(strip=True) if company else "Confidencial"

            loc = card.select_one(".ubicacion, .location, [class*=ubicacion]")
            loc = loc.get_text(strip=True) if loc else location

            desc = card.select_one(".descripcion, .description, .resumen, p")
            desc = desc.get_text(strip=True) if desc else ""

            if title:
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "url": job_url, "description": desc[:500],
                    "source": "Trabajando.cl",
                })
        except Exception as e:
            logger.warning("Trabajando parse error: %s", e)
            continue

    return jobs
