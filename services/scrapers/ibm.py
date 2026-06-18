from services.scrapers.base_ddg import scan_duckduckgo

async def scan_ibm(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("careers.ibm.com", "IBM", query, location, filters)
