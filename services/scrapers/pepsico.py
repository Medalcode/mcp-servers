from services.scrapers.base_ddg import scan_duckduckgo

async def scan_pepsico(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("pepsicojobs.com", "PepsiCo", query, location, filters)
