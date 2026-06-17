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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]


async def scan_getonboard(query: str, location: str = "Chile", filters: dict = None) -> list:
    api_urls = [
        f"https://www.getonbrd.cl/api/jobs?{urllib.parse.urlencode({'search': query, 'location': location, 'remote': 'true'})}",
        f"https://www.getonbrd.com/api/jobs?{urllib.parse.urlencode({'search': query, 'location': location, 'remote': 'true'})}",
        f"https://www.getonbrd.cl/api/v1/jobs?{urllib.parse.urlencode({'q': query, 'remote': 'true'})}",
    ]
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Referer": "https://www.getonbrd.cl/",
    }

    for api_url in api_urls:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = []
                    items = data if isinstance(data, list) else data.get("data", data.get("jobs", []))
                    for item in items:
                        if isinstance(item, dict) and item.get("title"):
                            company_raw = item.get("company", "Confidencial")
                            if isinstance(company_raw, dict):
                                company = company_raw.get("name", "Confidencial")
                            else:
                                company = str(company_raw) if company_raw else "Confidencial"
                            job_id = item.get("id", item.get("slug", ""))
                            url_base = "https://www.getonbrd.cl" if "getonbrd.cl" in api_url else "https://www.getonbrd.com"
                            jobs.append({
                                "title": item.get("title", ""),
                                "company": company,
                                "location": item.get("location", item.get("city", location)),
                                "url": f"{url_base}/job/{job_id}" if job_id else api_url,
                                "description": (item.get("description") or "")[:500],
                                "salary": item.get("salary", ""),
                                "source": "GetOnBoard",
                            })
                    if jobs:
                        return jobs
        except Exception as e:
            logger.warning("GetOnBoard API %s failed: %s", api_url, e)
            continue

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

    for card in soup.select("div[id^='job-'], div[data-job-id], article a[href*='/job/'], a[href*='/jobs/']"):
        try:
            card_el = card if card.name in ('article', 'div') else card.parent
            title_el = card.select_one("h2, h3, .job-title, [class*=title]")
            if not title_el:
                title_el = card
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            url_rel = ""
            if card.name == 'a':
                url_rel = card.get("href", "")
            else:
                a_tag = card.select_one("a[href*='/job/'], a[href*='/jobs/']")
                if a_tag:
                    url_rel = a_tag.get("href", "")
            if not url_rel:
                continue
            job_url = url_rel if url_rel.startswith("http") else f"https://www.getonbrd.cl{url_rel}"

            company = card.select_one(".company-name, .company, [class*=company], [class*=employer]")
            company = company.get_text(strip=True) if company else "Confidencial"

            loc = card.select_one(".location, [class*=location], [class*=ubication]")
            loc = loc.get_text(strip=True) if loc else location

            desc = card.select_one(".description, [class*=description], p, .job-description")
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
