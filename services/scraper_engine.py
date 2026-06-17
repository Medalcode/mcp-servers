import asyncio
import httpx
import logging
import os
import random
import time
from dataclasses import dataclass, field


from services.scrapers import (
    scan_chiletrabajos, scan_computrabajo,
    scan_getonboard, scan_remoteok,
    scan_laborum, scan_firstjob,
    scan_indeed, scan_trabajando,
    scan_randstad, scan_bebee,
)

logger = logging.getLogger(__name__)


@dataclass
class ScraperResult:
    source: str
    success: bool
    jobs: list = field(default_factory=list)
    error: str | None = None
    duration: float = 0.0
    fallback_used: bool = False
    retries: int = 0


DEDICATED_SCRAPERS = [
    ("ChileTrabajos", scan_chiletrabajos),
    ("CompuTrabajo", scan_computrabajo),
    ("Laborum", scan_laborum),
    ("GetOnBoard", scan_getonboard),
    ("RemoteOK", scan_remoteok),
    ("FirstJob", scan_firstjob),
    ("Indeed", scan_indeed),
    ("Trabajando", scan_trabajando),
    ("Randstad", scan_randstad),
    ("BeBee", scan_bebee),
]

def _get_scrapemcp_url() -> str:
    return os.environ.get("SCRAPEMCP_URL", "")


def _is_scrapemcp_enabled() -> bool:
    return os.environ.get("SCRAPEMCP_ENABLED", "").lower() in ("1", "true", "yes")


async def _call_scrapemcp(query: str, location: str = "Chile") -> ScraperResult:
    if not _is_scrapemcp_enabled() or not _get_scrapemcp_url():
        return ScraperResult(source="ScrapeMCP", success=False, error="ScrapeMCP not configured")
    start = time.monotonic()
    url = _get_scrapemcp_url()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{url}/api/scrape", json={
                "url": f"https://www.google.com/search?q={query}+trabajo+{location}",
            })
            if resp.status_code == 200:
                data = resp.json()
                links = data.get("links", [])
                jobs = [{"title": link.get("text", query), "url": link.get("href", ""),
                         "company": "", "location": location, "source": "ScrapeMCP",
                         "description": ""} for link in links[:15]]
                return ScraperResult(
                    source="ScrapeMCP",
                    success=bool(jobs),
                    jobs=jobs,
                    duration=time.monotonic() - start,
                    fallback_used=True,
                )
    except Exception as e:
        logger.warning("ScrapeMCP fallback failed: %s", e)

    return ScraperResult(
        source="ScrapeMCP",
        success=False,
        error="ScrapeMCP unavailable",
        duration=time.monotonic() - start,
        fallback_used=True,
    )


async def _run_scraper_with_retry(name: str, scraper_fn, query: str, location: str) -> ScraperResult:
    start = time.monotonic()
    max_retries = 2
    base_delay = 1.0
    
    for attempt in range(max_retries + 1):
        try:
            jobs = await scraper_fn(query, location)
            if jobs:
                return ScraperResult(
                    source=name,
                    success=True,
                    jobs=jobs,
                    duration=time.monotonic() - start,
                    retries=attempt,
                )
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.info("%s returned empty, retrying in %.1fs (attempt %d/%d)",
                           name, delay, attempt + 1, max_retries)
                await asyncio.sleep(delay)
        except Exception as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning("%s failed (attempt %d/%d): %s. Retrying in %.1fs",
                              name, attempt + 1, max_retries, e, delay)
                await asyncio.sleep(delay)
            else:
                logger.error("%s failed after %d retries: %s", name, max_retries, e)
                return ScraperResult(
                    source=name,
                    success=False,
                    error=str(e),
                    duration=time.monotonic() - start,
                    retries=attempt,
                )
    
    return ScraperResult(
        source=name,
        success=True,
        jobs=[],
        duration=time.monotonic() - start,
        retries=max_retries,
    )


async def search_all(query: str, location: str = "Chile",
                     remote_only: bool = False, use_scrapemcp_fallback: bool = True) -> list:
    tasks = [
        _run_scraper_with_retry(name, fn, query, location)
        for name, fn in DEDICATED_SCRAPERS
    ]
    
    results = await asyncio.shield(asyncio.gather(*tasks, return_exceptions=True)) if tasks else []
    
    scraper_results = []
    for r in results:
        if isinstance(r, ScraperResult):
            scraper_results.append(r)
        elif isinstance(r, Exception):
            scraper_results.append(ScraperResult(
                source="unknown", success=False, error=str(r)
            ))
    
    for result in scraper_results:
        if not result.success:
            logger.info("%s failed (%s), attempting fallback", result.source, result.error)
    
    if use_scrapemcp_fallback:
        failed_sources = [r.source for r in scraper_results if not r.success]
        if failed_sources:
            fallback = await _call_scrapemcp(query, location)
            if fallback.success:
                scraper_results.append(fallback)
    
    all_jobs = []
    for r in scraper_results:
        if r.success:
            for j in r.jobs:
                j["_scraperSource"] = r.source
            all_jobs.extend(r.jobs)
    
    logger.info("Search complete: %d jobs from %d/%d scrapers (duration: %.1fs)",
                len(all_jobs),
                sum(1 for r in scraper_results if r.success),
                len(DEDICATED_SCRAPERS),
                sum(r.duration for r in scraper_results))
    
    return all_jobs


def get_stats(scraper_results: list[ScraperResult]) -> dict:
    return {
        "total": len(scraper_results),
        "successful": sum(1 for r in scraper_results if r.success),
        "failed": sum(1 for r in scraper_results if not r.success),
        "fallbackUsed": any(r.fallback_used for r in scraper_results),
        "sources": {
            r.source: {
                "success": r.success,
                "jobCount": len(r.jobs),
                "duration": round(r.duration, 2),
                "error": r.error,
                "retries": r.retries,
            }
            for r in scraper_results
        },
    }
