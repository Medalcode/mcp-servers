from services.scrapers.base_ddg import scan_duckduckgo

async def scan_cocacola(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("careers.coca-colacompany.com", "Coca-Cola", query, location, filters)
