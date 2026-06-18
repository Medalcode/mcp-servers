from services.scrapers.base_ddg import scan_duckduckgo

async def scan_entel(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("trabajaenentel.cl", "Entel", query, location, filters)
