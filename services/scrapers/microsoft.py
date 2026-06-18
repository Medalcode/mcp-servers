from services.scrapers.base_ddg import scan_duckduckgo

async def scan_microsoft(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("careers.microsoft.com", "Microsoft", query, location, filters)
