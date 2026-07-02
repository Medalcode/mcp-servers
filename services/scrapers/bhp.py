import logging
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BHP_RSS_URL = "https://careers.bhp.com/services/rss/job/?locale=es_ES&keywords=({query})"


async def scan_bhp(query: str, location: str = "", filters: dict = None) -> list:
    rss_url = BHP_RSS_URL.format(query=query)
    if location:
        rss_url += f"+({location})"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(rss_url)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("BHP RSS request failed: %s", e)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.warning("BHP RSS parse error: %s", e)
        return []

    ns = {"": "http://www.w3.org/2005/Atom"}
    jobs = []
    for item in root.iter("item"):
        try:
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            date_el = item.find("pubDate")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            date = date_el.text.strip() if date_el is not None and date_el.text else ""

            if not title or not link:
                continue

            desc_clean = BeautifulSoup(desc, "lxml").get_text(strip=True)[:500]

            location_str = "Chile"
            if location:
                location_str = location

            jobs.append({
                "title": title,
                "company": "BHP",
                "location": location_str,
                "url": link,
                "description": desc_clean,
                "source": "BHP",
                "date": date,
                "tags": [],
            })
        except Exception as e:
            logger.warning("BHP RSS parse item error: %s", e)
            continue

    return jobs
