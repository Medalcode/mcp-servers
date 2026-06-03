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


async def scan_getonboard(query: str, location: str = "Chile") -> list:
    params = {"search": query, "location": location, "remote": "true"}
    url = f"https://www.getonbrd.cl/api/jobs?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Referer": "https://www.getonbrd.cl/",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                jobs = []
                for item in data if isinstance(data, list) else data.get("data", []):
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("company", {}).get("name", "Confidencial") if isinstance(item.get("company"), dict) else str(item.get("company", "Confidencial")),
                        "location": item.get("location", location),
                        "url": f"https://www.getonbrd.cl/job/{item.get('id', '')}",
                        "description": (item.get("description") or "")[:500],
                        "salary": item.get("salary", ""),
                        "source": "GetOnBoard",
                    })
                return jobs
    except Exception as e:
        logger.warning("GetOnBoard API failed: %s", e)

    params = {"q": query, "location": location}
    url = f"https://www.getonbrd.cl/jobs?{urllib.parse.urlencode(params)}"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": random.choice(USER_AGENTS)})
            resp.raise_for_status()
    except Exception as e:
        logger.warning("GetOnBoard HTML fallback failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for card in soup.select("div.job-item, article.job-card, div[class*=job]"):
        try:
            title_el = card.select_one("h2 a, h3 a, a[href*='/job/']")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_rel = title_el.get("href", "")
            job_url = url_rel if url_rel.startswith("http") else f"https://www.getonbrd.cl{url_rel}"

            company = card.select_one(".company-name, .company, [class*=company]")
            company = company.get_text(strip=True) if company else "Confidencial"

            loc = card.select_one(".location, [class*=location]")
            loc = loc.get_text(strip=True) if loc else location

            desc = card.select_one(".description, [class*=description], p")
            desc = desc.get_text(strip=True) if desc else ""

            if title:
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "url": job_url, "description": desc[:500],
                    "source": "GetOnBoard",
                })
        except Exception as e:
            logger.warning("GetOnBoard parse error: %s", e)
            continue

    return jobs
