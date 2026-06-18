from services.scrapers.base_ddg import scan_duckduckgo

async def scan_bci(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("bci.cl", "Banco BCI", query, location, filters)
