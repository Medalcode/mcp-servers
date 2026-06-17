import httpx
import logging
from bs4 import BeautifulSoup
import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


async def scan_remoteok(query: str, location: str = "", filters: dict = None) -> list:
    url = f"https://remoteok.com/remote-{query.replace(' ', '-')}-jobs"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("RemoteOK request failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for card in soup.select("tr.job"):
        try:
            title_el = card.select_one("td.company h2 a, td.company a.preventLink")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_rel = title_el.get("href", "")
            job_url = f"https://remoteok.com{url_rel}" if url_rel.startswith("/") else url_rel

            company = card.select_one("td.company h3, td.company span.companyLink a")
            company = company.get_text(strip=True) if company else "Confidencial"

            desc = card.select_one("td.company .description")
            desc = desc.get_text(strip=True) if desc else ""

            tags = [t.get_text(strip=True) for t in card.select("td.tags a")]
            location_text = card.select_one(".location")
            location_text = location_text.get_text(strip=True) if location_text else "Remote"

            if title:
                jobs.append({
                    "title": title, "company": company, "location": location_text,
                    "url": job_url, "description": desc[:500],
                    "tags": tags, "source": "RemoteOK",
                })
        except Exception as e:
            logger.warning("RemoteOK parse error: %s", e)
            continue

    return jobs
