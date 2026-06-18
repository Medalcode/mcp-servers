from services.scrapers.base_ddg import scan_duckduckgo

async def scan_sap(query: str, location: str = "", filters: dict = None) -> list:
    return await scan_duckduckgo("jobs.sap.com", "SAP", query, location, filters)
