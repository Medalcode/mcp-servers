from services.scrapers.base_ddg import scan_duckduckgo

async def scan_latam(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("careers.latam.com", "Latam Airlines", query, location, filters)
