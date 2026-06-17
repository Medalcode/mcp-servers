import logging
import re
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

RSS_URL = "https://empleos.codelco.cl/services/rss/job/?locale=es_ES&keywords=({query})"


async def scan_codelco(query: str, location: str = "") -> list:
    if query:
        url = RSS_URL.format(query=query)
        if location:
            url += f"+({location})"
    else:
        url = "https://empleos.codelco.cl/services/rss/job/?locale=es_ES"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Codelco RSS request failed: %s", e)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.warning("Codelco RSS parse error: %s", e)
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

            loc = "Chile"
            if "Reg. Metropolitana" in title:
                loc = "Santiago, Chile"
            elif "Antofagasta" in title:
                loc = "Antofagasta, Chile"

            desc_clean = re.sub(r"<[^>]+>", "", desc).strip()[:500]
            jobs.append({
                "title": title,
                "company": "Codelco",
                "location": loc,
                "url": link,
                "description": desc_clean,
                "source": "Codelco",
                "date": date,
                "tags": [],
            })
        except Exception as e:
            logger.warning("Codelco RSS parse item error: %s", e)
            continue

    return jobs
