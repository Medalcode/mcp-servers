import json
import logging
import random
import urllib.parse

import httpx

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

API_URL = "https://bebee.com/api/jobs"


def _parse_location(location_name: str) -> tuple[str, str]:
    if not location_name:
        return "", ""
    parts = [p.strip() for p in location_name.split(",")]
    city = parts[0] if parts else ""
    region = parts[1] if len(parts) > 1 else ""
    return city, region


async def scan_bebee(query: str, location: str = "") -> list:
    params = {"q": query, "country": "CL", "limit": 50}
    search_url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(search_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("BeBee API request failed: %s", e)
        return []

    jobs = []
    for item in data.get("jobs", []):
        try:
            title = item.get("title", "").strip()
            if not title:
                continue

            location_name = item.get("location_name", "")
            city, region = _parse_location(location_name)
            country_code = item.get("country_code", "")

            if country_code != "CL":
                continue

            if location and location.lower() not in location_name.lower():
                continue

            description = (item.get("description") or "")[:500]

            contract_map = {
                "full_time": "Tiempo completo",
                "part_time": "Tiempo parcial",
                "contract": "Contrato",
                "temporary": "Temporal",
                "internship": "Prácticas",
            }
            contract_type = contract_map.get(item.get("contract_type", ""), "")

            remote_policy = item.get("remote_policy", "")
            if remote_policy == "full_remote":
                remote_label = "100% Remoto"
            elif remote_policy == "hybrid":
                remote_label = "Híbrido"
            elif remote_policy == "on_site":
                remote_label = "Presencial"
            else:
                remote_label = ""

            jobs.append({
                "title": title,
                "company": item.get("publisher_name", ""),
                "location": location_name.replace(", CL", "").strip(),
                "url": item.get("url", ""),
                "description": description,
                "contractType": contract_type,
                "remotePolicy": remote_label,
                "salary": "",
                "source": "BeBee",
                "published": item.get("started_date", ""),
            })
        except Exception as e:
            logger.warning("BeBee parse error: %s", e)
            continue

    return jobs
