from services.scrapers.base_ddg import scan_duckduckgo

async def scan_falabella(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("trabajaen.falabella.com", "Falabella", query, location, filters)
