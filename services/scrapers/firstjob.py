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

AREA_MAP = {
    "software": "Ingenieria-de-Software-y-Tecnologia",
    "data": "Estadistica-y-Datos",
    "design": "Diseno-y-Arquitectura",
    "it": "Ingenieria-de-Software-y-Tecnologia",
    "tech": "Ingenieria-de-Software-y-Tecnologia",
    "operations": "Gestion-de-Operaciones",
    "product": "Gestion-y-Desarrollo-de-Productos",
}


def _map_area(query: str) -> str | None:
    q = query.lower()
    for key, area in AREA_MAP.items():
        if key in q:
            return area
    return None


async def scan_firstjob(query: str, location: str = "Chile", filters: dict = None) -> list:
    area = _map_area(query)
    params = {}
    if area:
        params["area"] = area
    else:
        params["title"] = query

    country_map = {"Chile": "43", "Perú": "168", "Colombia": "47", "México": "138", "Argentina": "10"}
    if location in country_map:
        params["country[]"] = country_map[location]

    base_url = "https://firstjob.me/ofertas"
    url = f"{base_url}?{urllib.parse.urlencode(params, doseq=True)}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    jobs = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("FirstJob request failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select("div.card-job.hover-up")

    for card in cards:
        try:
            link = card.select_one("a[href*='/oferta/']")
            if not link:
                continue

            href = link.get("href", "")
            job_url = f"https://firstjob.me{href}" if href.startswith("/") else href

            title_el = card.select_one("h6.card-job-top--info-heading")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            company_el = card.select_one("span.card-job-top--company")
            company = company_el.get_text(strip=True) if company_el else "Confidencial"

            loc_el = card.select_one("span.card-job-top--location")
            loc = loc_el.get_text(strip=True).replace("Región Metropolitana de ", "").replace("Región ", "") if loc_el else location

            desc_el = card.select_one("div.card-job-description")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            type_el = card.select_one("span.disc-btn")
            job_type = type_el.get_text(strip=True) if type_el else ""

            tags = [span.get_text(strip=True) for span in card.select("span.background-blue-light")]

            jobs.append({
                "title": title,
                "company": company,
                "location": loc,
                "url": job_url,
                "description": desc[:500],
                "source": "FirstJob",
                "type": job_type,
                "tags": tags,
            })
        except Exception as e:
            logger.warning("FirstJob parse error: %s", e)
            continue

    return jobs
