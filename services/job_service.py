import asyncio
import json
import logging

from services.ai_provider import _clean_json
from services.scraper_engine import search_all
from services.scrapers import (
    scan_chiletrabajos, scan_computrabajo,
    scan_getonboard, scan_remoteok,
    scan_laborum, scan_firstjob, scan_linkedin
)

logger = logging.getLogger(__name__)

async def mass_register_sf(urls: list[str]) -> dict:
    from engines.selenium_engine import SeleniumEngine
    from services.sf_automator import SuccessFactorsAutomator
    
    results = {}
    engine = SeleniumEngine()
    
    try:
        automator = SuccessFactorsAutomator(engine)
        for url in urls:
            try:
                success = await automator.register_account(url)
                results[url] = "SUCCESS" if success else "FAILED"
            except Exception as e:
                logger.error(f"Error registering at {url}: {e}")
                results[url] = f"ERROR: {e}"
    finally:
        engine.close()
        
    return results

ALL_SCRAPERS = [
    ("ChileTrabajos", scan_chiletrabajos),
    ("CompuTrabajo", scan_computrabajo),
    ("Laborum", scan_laborum),
    ("GetOnBoard", scan_getonboard),
    ("RemoteOK", scan_remoteok),
    ("FirstJob", scan_firstjob),
    ("LinkedIn", scan_linkedin),
]


async def search_jobs(query: str, location: str = "Chile", remote_only: bool = False,
                      use_new_engine: bool = True, filters: dict = None) -> list:
    if use_new_engine:
        all_jobs = await search_all(query, location, remote_only, filters=filters)
    else:
        tasks = [scanner(query, location) for name, scanner in ALL_SCRAPERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

    all_jobs = [normalize(j) for j in all_jobs if j.get("title")]

    # Strict Keyword Match (if a query was provided, it must be in title or description)
    if query and query.strip():
        q_lower = query.strip().lower()
        # Some portals do fuzzy match, we enforce exact term presence
        all_jobs = [
            j for j in all_jobs
            if q_lower in j["title"].lower() or q_lower in j["description"].lower()
        ]

    if remote_only:
        remote_terms = ["remote", "remoto", "teletrabajo", "home office",
                        "anywhere", "latam", "global", "100% remoto"]
        all_jobs = [
            j for j in all_jobs
            if any(t in (j.get("location") or "").lower() for t in remote_terms)
        ]
        
    if filters:
        if filters.get("company"):
            c_filter = filters["company"].lower()
            all_jobs = [j for j in all_jobs if c_filter in (j.get("company") or "").lower()]
            
        if filters.get("exclude"):
            excludes = [e.strip().lower() for e in filters["exclude"].split(",")]
            all_jobs = [j for j in all_jobs if not any(e in (j.get("title") or "").lower() or e in (j.get("description") or "").lower() for e in excludes if e)]

    all_jobs = deduplicate(all_jobs)

    for job in all_jobs:
        score, matched = calculate_match(job, query)
        job["matchScore"] = score
        job["matchedKeywords"] = matched[:5]

    all_jobs.sort(key=lambda j: j["matchScore"], reverse=True)
    return all_jobs


async def search_jobs_with_ai(query: str, profile: dict, location: str = "Chile",
                               remote_only: bool = False, use_new_engine: bool = True, filters: dict = None) -> list:
    jobs = await search_jobs(query, location, remote_only, use_new_engine, filters)

    if not jobs:
        return []

    from services.ai_provider import _call_ai

    pi = profile.get("personalInfo", {})
    skills = ", ".join(profile.get("skills", [])[:10])
    exp_summary = "; ".join(
        f"{e['title']} en {e['company']}" for e in profile.get("experience", [])[:3]
    )

    job_lines = "\n".join(f'{i+1}. {j["title"]} @ {j["company"]} - {j.get("description","")[:200]}' for i, j in enumerate(jobs[:15]))
    prompt = f"""Eres un reclutador experto. Analiza estas ofertas de trabajo y el perfil del candidato, y asigna un puntaje de compatibilidad (0-100) a cada oferta basado en qué tan bien calza con el candidato.

PERFIL DEL CANDIDATO:
- Título: {pi.get('currentTitle', '')}
- Experiencia: {exp_summary}
- Habilidades: {skills}
- Resumen: {pi.get('summary', '')}

OFERTAS:
{job_lines}

Responde ÚNICAMENTE con un array JSON donde cada elemento tiene: {{"index": int, "score": int (0-100), "reason": str}}

Devuelve SOLO el JSON array, sin texto adicional."""
    try:
        result = await _call_ai(prompt)
        cleaned = _clean_json(result)
        scores = json.loads(cleaned)
        score_map = {s["index"] - 1: s for s in scores if isinstance(s, dict)}
        for i, job in enumerate(jobs):
            if i in score_map:
                job["aiScore"] = score_map[i]["score"]
                job["aiReason"] = score_map[i].get("reason", "")
    except Exception as e:
        logger.warning("AI job matching failed: %s", e)

    jobs.sort(key=lambda j: j.get("aiScore", j.get("matchScore", 0)), reverse=True)
    return jobs


def normalize(job: dict) -> dict:
    import re
    
    # Clean location (remove breadcrumbs, multiple spaces, keep last segment if separated by >)
    raw_loc = job.get("location", "Chile") or "Chile"
    if ">" in raw_loc:
        raw_loc = raw_loc.split(">")[-1]
    
    # Remove separators often used by DDG like " | " or " - " at the end
    raw_loc = re.sub(r'[-\|].*$', '', raw_loc).strip()
    
    return {
        "title": job.get("title", "").strip(),
        "company": (job.get("company") or "Confidencial").strip(),
        "location": raw_loc or "Chile",
        "url": job.get("url", ""),
        "description": (job.get("description") or "")[:500],
        "source": job.get("source", "unknown"),
        "date": job.get("date", ""),
        "salary": job.get("salary", ""),
        "tags": job.get("tags", []),
    }


def deduplicate(jobs: list) -> list:
    seen = set()
    result = []
    for job in jobs:
        title = job.get("title", "").lower().strip()
        company = job.get("company", "").lower().strip()
        location = job.get("location", "").lower().strip()[:30]
        key = f"{title}|{company}|{location}"
        if key not in seen:
            seen.add(key)
            result.append(job)
        else:
            existing = next((j for j in result if f"{j['title'].lower()}|{j['company'].lower()}|{j.get('location','').lower()[:30]}" == key), None)
            if existing:
                existing_desc = existing.get("description", "")
                job_desc = job.get("description", "")
                if len(job_desc) > len(existing_desc):
                    result.remove(existing)
                    result.append(job)
    return result


def calculate_match(job: dict, query: str) -> tuple:
    score = 0
    matched = []
    text_lower = f"{job['title']} {job['description']}".lower()
    query_words = query.lower().split()

    for word in query_words:
        if len(word) > 2 and word in text_lower:
            score += 10
            matched.append(word)

    score = min(score, 100)
    return score, matched
