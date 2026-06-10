import json
import logging
import random
import re
import urllib.parse

import httpx

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


def _extract_route_data(html: str) -> dict | None:
    idx = html.find("__ROUTE_DATA__")
    if idx < 0:
        return None
    start = html.index("{", idx)
    depth = 0
    in_str = False
    escaped = False
    end = start
    for i in range(start, len(html)):
        ch = html[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_str:
            escaped = True
            continue
        if ch == '"' and not escaped:
            in_str = not in_str
            continue
        if not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
    try:
        return json.loads(html[start:end])
    except json.JSONDecodeError:
        return None


async def scan_randstad(query: str, location: str = "") -> list:
    slug = query.lower().replace(" ", "-")
    search_url = f"https://www.randstad.cl/trabajos/q-{urllib.parse.quote(slug)}/"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(search_url, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Randstad request failed: %s", e)
        return []

    data = _extract_route_data(resp.text)
    if not data:
        logger.warning("Randstad: no route data found")
        return []

    hits = data.get("searchResults", {}).get("hits", {}).get("hits", [])
    jobs = []
    for hit in hits:
        try:
            src = hit.get("_source", {})
            ji = src.get("JobInformation", {})
            jl = src.get("JobLocation", {})
            ji2 = src.get("BlueXSanitized", {})
            city = jl.get("City", "")
            region = jl.get("Region", "")

            location_str = city
            if region:
                location_str += ", " + region

            title_slug = ji2.get("Title", "")
            city_slug = ji2.get("City", "")
            job_id = hit.get("_id", "")
            url_slug = f"{title_slug}_{city_slug}_{job_id}" if title_slug and city_slug else ""

            salary_min = src.get("Salary", {}).get("SalaryMin", "0")
            salary_str = f"${int(salary_min):,}" if salary_min and salary_min != "0" else ""

            title = ji.get("Title", "").strip()
            if not title:
                continue

            if location and location.lower() not in location_str.lower():
                continue

            jobs.append({
                "title": title,
                "company": src.get("JobIdentity", {}).get("CompanyName", "Randstad Chile"),
                "location": location_str,
                "url": f"https://www.randstad.cl/trabajos/{url_slug}/" if url_slug else search_url,
                "description": (ji.get("Description") or "")[:500],
                "salary": salary_str,
                "jobType": ji.get("JobType", ""),
                "source": "Randstad",
            })
        except Exception as e:
            logger.warning("Randstad parse error: %s", e)
            continue

    return jobs
