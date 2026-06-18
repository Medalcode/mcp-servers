from services.scrapers.base_ddg import scan_duckduckgo

async def scan_cencosud(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("oportunidades.cencosud.com", "Cencosud", query, location, filters)
