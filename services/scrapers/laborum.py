import asyncio
import httpx
import logging
import os
import random
import time
import uuid

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
]

SITE_ID = "BMCL"
BASE_URL = "https://www.laborum.cl"
SEARCH_URL = f"{BASE_URL}/api/avisos/searchV2"
TOTAL_URL = f"{BASE_URL}/api/avisos/total"
HOMEPAGE_URL = f"{BASE_URL}/empleos-python"
RATE_LIMIT = float(os.environ.get("LABORUM_RATE_LIMIT", "0.5"))
MAX_RETRIES = 2


async def _new_session(client: httpx.AsyncClient) -> str | None:
    try:
        resp = await client.get(TOTAL_URL, headers={
            "x-site-id": SITE_ID,
            "x-pre-session-token": str(uuid.uuid4()),
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{BASE_URL}/",
        })
        resp.raise_for_status()
        jwt = resp.headers.get("x-session-jwt")
        logger.debug("Laborum session JWT: %s", "obtained" if jwt else "none")
        return jwt
    except Exception as e:
        logger.warning("Laborum session init failed: %s", e)
        return None


async def _search_page(client: httpx.AsyncClient, jwt: str, query: str, page: int = 0, sort: str = "RECIENTES") -> dict | None:
    headers = {
        "x-site-id": SITE_ID,
        "x-session-jwt": jwt,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/empleos-{query.lower().replace(' ', '-')}",
        "User-Agent": random.choice(USER_AGENTS),
    }
    payload = {
        "filtros": [],
        "query": query,
        "internacional": False,
    }
    params = {"pageSize": 20, "page": page, "sort": sort}

    try:
        resp = await client.post(SEARCH_URL, params=params, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.info("Laborum JWT expired, returning None to trigger refresh")
            return None
        logger.warning("Laborum search HTTP %d: %s", e.response.status_code, e)
        return None
    except Exception as e:
        logger.warning("Laborum search error: %s", e)
        return None


def _parse_job(item: dict) -> dict:
    return {
        "title": (item.get("titulo") or "").strip(),
        "company": (item.get("empresa") or "Confidencial").strip(),
        "location": (item.get("localizacion") or item.get("ubicacion") or "Chile").strip(),
        "url": f"{BASE_URL}/empleo/{item.get('id', '')}",
        "description": (item.get("detalle") or "")[:500],
        "source": "Laborum",
        "date": (item.get("fechaPublicacion") or "").strip(),
        "salary": (item.get("salario") or "").strip(),
        "tags": [
            t for t in [
                item.get("modalidadTrabajo"),
                item.get("tipoTrabajo"),
                item.get("nivelLaboral"),
            ] if t
        ],
    }


async def scan_laborum(query: str, location: str = "") -> list:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        client.headers.update({"User-Agent": random.choice(USER_AGENTS)})

        resp = await client.get(HOMEPAGE_URL, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        })
        resp.raise_for_status()
        await asyncio.sleep(0.3)

        jwt = await _new_session(client)
        if not jwt:
            logger.error("Laborum: could not establish session")
            return []

        all_jobs = []
        page = 0
        consecutive_empty = 0

        while consecutive_empty < 2:
            await asyncio.sleep(RATE_LIMIT)

            data = await _search_page(client, jwt, query, page)
            if data is None:
                jwt = await _new_session(client)
                if not jwt:
                    break
                data = await _search_page(client, jwt, query, page)

            if data is None:
                break

            items = data.get("content") or []
            total = data.get("total") or 0

            for item in items:
                job = _parse_job(item)
                if job["title"]:
                    all_jobs.append(job)

            if not items:
                consecutive_empty += 1
            else:
                consecutive_empty = 0

            page += 1
            if total <= page * 20:
                break

        logger.info("Laborum: %d jobs for '%s'", len(all_jobs), query)
        return all_jobs
