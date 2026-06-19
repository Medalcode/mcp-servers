import logging
import re
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

RSS_URL = "https://careers.glencorecopper.com/services/rss/job/?locale=en_US&keywords=({query})"


async def scan_glencore(query: str, location: str = "", filters: dict = None) -> list:
    url = RSS_URL.format(query=query)
    if location:
        url += f"+({location})"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Glencore RSS request failed: %s", e)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.warning("Glencore RSS parse error: %s", e)
        return []

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

            loc = location if location else "Chile"
            desc_clean = re.sub(r"<[^>]+>", "", desc).strip()[:500]
            jobs.append({
                "title": title,
                "company": "Glencore",
                "location": loc,
                "url": link,
                "description": desc_clean,
                "source": "Glencore",
                "date": date,
                "tags": [],
            })
        except Exception as e:
            logger.warning("Glencore RSS parse item error: %s", e)
            continue

    return jobs
