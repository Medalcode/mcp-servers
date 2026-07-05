import httpx
import json
import logging
from database import get_connection

logger = logging.getLogger(__name__)


async def research_company(company_name: str) -> dict:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM companies WHERE name = ?", (company_name,))
    existing = cur.fetchone()
    if existing:
        return dict(existing)

    info = {
        "name": company_name,
        "website": "",
        "industry": "",
        "size": "",
        "description": "",
        "culture": "",
        "tech_stack": "",
        "glassdoor_rating": None,
        "linkedin_url": "",
        "careers_url": "",
        "notes": "",
    }

    search_queries = [
        f"{company_name} LinkedIn",
        f"{company_name} Glassdoor",
        f"{company_name} careers jobs",
        f"{company_name} crunchbase",
    ]

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for query in search_queries[:2]:
            try:
                resp = await client.get(
                    "https://www.google.com/search",
                    params={"q": query},
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
                )
                if "linkedin.com/company" in resp.text.lower() and not info["linkedin_url"]:
                    import re
                    m = re.search(r'https?://[a-z]+\.linkedin\.com/company/[^"&\s<>]+', resp.text, re.I)
                    if m:
                        info["linkedin_url"] = m.group(0).rstrip("/")
            except Exception as e:
                logger.warning("Google search failed for query '%s': %s", query, e)

    try:
        from services.ai_provider import _call_ai, _clean_json
        result = await _call_ai("company_research -- " + company_name[:50])
        cleaned = _clean_json(result)
        ai_data = json.loads(cleaned)
        info["website"] = ai_data.get("website", info["website"])
        info["industry"] = ai_data.get("industry", info["industry"])
        info["size"] = ai_data.get("size", info["size"])
        info["description"] = ai_data.get("description", info["description"])
        info["culture"] = ai_data.get("culture", info["culture"])
        info["tech_stack"] = ai_data.get("techStack", info["tech_stack"])
        info["careers_url"] = ai_data.get("careersUrl", info["careers_url"])
    except Exception as e:
        logger.warning("AI company research failed: %s", e)

    conn.execute("""INSERT INTO companies (name, website, industry, size, description, culture, tech_stack, linkedin_url, careers_url)
        VALUES (?,?,?,?,?,?,?,?,?)""",
                 (info["name"], info["website"], info["industry"], info["size"],
                  info["description"], info["culture"], info["tech_stack"],
                  info["linkedin_url"], info["careers_url"]))
    conn.commit()

    return info


async def get_company_insights(company_name: str) -> str:
    info = await research_company(company_name)

    lines = [f"=== {company_name} ==="]
    if info.get("website"):
        lines.append(f"Web: {info['website']}")
    if info.get("industry"):
        lines.append(f"Industria: {info['industry']}")
    if info.get("size"):
        lines.append(f"Tamaño: {info['size']}")
    if info.get("description"):
        lines.append(f"Descripción: {info['description']}")
    if info.get("tech_stack"):
        lines.append(f"Stack tecnológico: {info['tech_stack']}")
    if info.get("culture"):
        lines.append(f"Cultura: {info['culture']}")
    if info.get("linkedin_url"):
        lines.append(f"LinkedIn: {info['linkedin_url']}")
    if info.get("careers_url"):
        lines.append(f"Portal empleo: {info['careers_url']}")

    return "\n".join(lines)
