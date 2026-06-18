from services.scrapers.base_ddg import scan_duckduckgo

async def scan_nestle(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("jobs.nestle.com", "Nestlé", query, location, filters)
