import urllib.parse
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


async def scan_chiletrabajos(query: str, location: str = "") -> list:
    params = {"2": query, "filterSearch": "Buscar"}
    if location:
        params["9"] = location
    search_url = f"https://www.chiletrabajos.cl/encuentra_un_empleo?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(search_url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("ChileTrabajos request failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for item in soup.select("div.job-item"):
        try:
            title_el = item.select_one("h2.title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            url_rel = title_el.get("href", "")
            url = url_rel if url_rel.startswith("http") else f"https://www.chiletrabajos.cl{url_rel}"

            meta_h3s = item.select("h3.meta")
            company = "Confidencial"
            loc = location or "Chile"

            if len(meta_h3s) >= 1:
                meta_text = meta_h3s[0].get_text(strip=True)
                parts = [p.strip() for p in meta_text.split(",")]
                if len(parts) >= 2:
                    company = parts[0]
                    loc = parts[1]
                elif parts:
                    company = parts[0]

            desc_el = item.select_one("h3.meta:last-of-type")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            date_text = ""
            if len(meta_h3s) >= 2:
                date_text = meta_h3s[-1].get_text(strip=True)

            if title and company:
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "url": url, "description": desc[:500], "source": "ChileTrabajos",
                    "date": date_text,
                })
        except Exception as e:
            logger.warning("ChileTrabajos parse error: %s", e)
            continue

    return jobs
