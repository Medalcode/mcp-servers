import httpx
import logging
from bs4 import BeautifulSoup
import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


async def scan_computrabajo(query: str, location: str = "") -> list:
    norm_q = query.lower().strip().replace(" ", "-")
    search_url = f"https://cl.computrabajo.com/trabajo-de-{norm_q}"
    if location and location.lower() != "remoto":
        norm_loc = location.lower().strip().replace(" ", "-")
        search_url += f"-en-{norm_loc}"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(search_url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("CompuTrabajo request failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for item in soup.select("article.box_offer"):
        try:
            title_el = item.select_one("h2.fs18 a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_rel = title_el.get("href", "")
            url = url_rel if url_rel.startswith("http") else f"https://cl.computrabajo.com{url_rel}"

            company = item.select_one(".fs16.fc_base.mt5 a")
            company = company.get_text(strip=True) if company else "Empresa Confidencial"

            location_text = item.select_one(".fs16.fc_base.mt5 span.mr10")
            location_text = location_text.get_text(strip=True) if location_text else "Chile"

            desc = item.select_one("p.fs13.fc_aux")
            desc = desc.get_text(strip=True) if desc else ""

            if title and url:
                jobs.append({
                    "title": title, "company": company, "location": location_text,
                    "url": url, "description": desc[:500], "source": "CompuTrabajo",
                })
        except Exception as e:
            logger.warning("CompuTrabajo parse error: %s", e)
            continue

    return jobs
