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
    scan_randstad, scan_bebee, scan_sonda,
    scan_bhp, scan_codelco,
    scan_freeport, scan_teck,
    scan_lundin, scan_glencore,
)
from services.scrapers.ibm import scan_ibm
from services.scrapers.microsoft import scan_microsoft
from services.scrapers.nestle import scan_nestle
from services.scrapers.cocacola import scan_cocacola
from services.scrapers.pepsico import scan_pepsico
from services.scrapers.sap import scan_sap
from services.scrapers.cencosud import scan_cencosud
from services.scrapers.falabella import scan_falabella
from services.scrapers.latam import scan_latam
from services.scrapers.entel import scan_entel
from services.scrapers.bci import scan_bci
from services.scrapers.linkedin import scan_linkedin

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
    ("Sonda", scan_sonda),
    ("BHP", scan_bhp),
    ("Codelco", scan_codelco),
    ("Freeport", scan_freeport),
    ("Teck", scan_teck),
    ("Lundin", scan_lundin),
    ("Glencore", scan_glencore),
    ("IBM", scan_ibm),
    ("Microsoft", scan_microsoft),
    ("Nestlé", scan_nestle),
    ("Coca-Cola", scan_cocacola),
    ("PepsiCo", scan_pepsico),
    ("SAP", scan_sap),
    ("Cencosud", scan_cencosud),
    ("Falabella", scan_falabella),
    ("Latam Airlines", scan_latam),
    ("Entel", scan_entel),
    ("Banco BCI", scan_bci),
    ("LinkedIn", scan_linkedin),
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


async def _run_scraper_with_retry(name: str, scraper_fn, query: str, location: str, filters: dict = None) -> ScraperResult:
    start = time.monotonic()
    max_retries = 2
    base_delay = 1.0
    
    for attempt in range(max_retries + 1):
        try:
            jobs = await scraper_fn(query, location, filters=filters)
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


def _matches_location(job_loc: str, query_loc: str) -> bool:
    if not query_loc or query_loc in ["chile", "remoto", ""]:
        return True
    if query_loc not in job_loc and job_loc != "chile" and "remoto" not in job_loc:
        if query_loc == "santiago" and "metropolitana" in job_loc:
            return True
        return False
    return True

async def search_all(query: str, location: str = "Chile",
                     remote_only: bool = False, use_scrapemcp_fallback: bool = True, filters: dict = None) -> list:
    sem = asyncio.Semaphore(5)
    
    async def _sem_task(name, fn):
        async with sem:
            return await _run_scraper_with_retry(name, fn, query, location, filters)

    active_scrapers = DEDICATED_SCRAPERS
    if filters and filters.get("scrapers"):
        selected = [s.lower() for s in filters["scrapers"]]
        active_scrapers = [(name, fn) for name, fn in DEDICATED_SCRAPERS if name.lower() in selected]
        logger.info(f"Filters selected: {selected}")
    
    logger.info(f"Active scrapers count: {len(active_scrapers)}")

    tasks = [
        _sem_task(name, fn)
        for name, fn in active_scrapers
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
                if _matches_location(j.get("location", "").lower(), location.lower()):
                    all_jobs.append(j)
    
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
