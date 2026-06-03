import re
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


async def scan_indeed(query: str, location: str = "Chile") -> list:
    params = {"q": query, "l": location, "sort": "date"}
    url = f"https://cl.indeed.com/trabajo?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Indeed request failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []

    for card in soup.select("div.job_seen_beacon, div.jobsearch-SerpJobCard, div.cardOutline, li.css-1ac2h1w, div.slider_container li"):
        try:
            title_el = card.select_one("h2 a, h2.jobTitle a, a.jobTitle, a[data-jk]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_rel = title_el.get("href", "")
            job_url = f"https://cl.indeed.com{url_rel}" if url_rel.startswith("/") else url_rel

            company = card.select_one('[data-testid="company-name"], span.companyName, .company a, .companyName')
            company = company.get_text(strip=True) if company else "Confidencial"

            location_el = card.select_one('[data-testid="text-location"], div.companyLocation, .location')
            loc = location_el.get_text(strip=True) if location_el else location

            desc_el = card.select_one('[data-testid="job-snippet"], div.job-snippet, .summary, ul li')
            desc = desc_el.get_text(strip=True) if desc_el else ""

            salary_el = card.select_one('[data-testid="attribute_snippet_testid"], .salary-snippet, .salary')
            salary = salary_el.get_text(strip=True) if salary_el else ""

            date_el = card.select_one('[data-testid="job-date"], .date, .jobsearch-SerpJobCard-footer')
            date = date_el.get_text(strip=True) if date_el else ""

            if title:
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "url": job_url, "description": desc[:500], "salary": salary,
                    "date": date, "source": "Indeed",
                })
        except Exception as e:
            logger.warning("Indeed parse error: %s", e)
            continue

    return jobs
