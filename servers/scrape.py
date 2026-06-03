import json
from mcp.server.fastmcp import FastMCP

from scrapers.page import PageScraper
from scrapers.table import TableScraper
from scrapers.list_scraper import ListScraper
from scrapers.sitemap import SitemapScraper, _SITEMAP_URL_LIMIT
from scrapers.exporters import to_csv, to_markdown

mcp = FastMCP("ScrapeMCP")

page_scraper = PageScraper()
table_scraper = TableScraper()
list_scraper = ListScraper()
sitemap_scraper = SitemapScraper()


@mcp.tool()
async def scrape(url: str, selectors: dict[str, str] | None = None) -> str:
    result = await page_scraper.scrape(url, selectors)
    if result.error:
        return f"Error: {result.error}"
    return json.dumps(result.data, indent=2, ensure_ascii=False)


@mcp.tool()
async def inspect(url: str) -> str:
    result = await page_scraper.inspect(url)
    if result.error:
        return f"Error: {result.error}"
    return json.dumps(result.data, indent=2, ensure_ascii=False)


@mcp.tool()
async def tables(url: str, selector: str = "table") -> str:
    result = await table_scraper.scrape_tables(url, selector)
    if result.error:
        return f"Error: {result.error}"
    return json.dumps(result.data, indent=2, ensure_ascii=False)


@mcp.tool()
async def scrape_list(url: str, item_selector: str, fields: dict[str, str]) -> str:
    result = await list_scraper.scrape_list(url, item_selector, fields)
    if result.error:
        return f"Error: {result.error}"
    return json.dumps(result.data, indent=2, ensure_ascii=False)


@mcp.tool()
async def scrape_recursive(start_url: str, link_selector: str, item_selector: str,
                            fields: dict[str, str], max_pages: int = 10) -> str:
    result = await list_scraper.scrape_recursive(
        start_url, link_selector, item_selector,
        fields, max_pages,
    )
    if result.error:
        return f"Error: {result.error}"
    return json.dumps(result.data, indent=2, ensure_ascii=False)


@mcp.tool()
async def sitemap(url: str) -> str:
    result = await sitemap_scraper.parse_sitemap(url)
    if result.error:
        return f"Error: {result.error}"
    data = result.data
    data["urls"] = data["urls"][:_SITEMAP_URL_LIMIT]
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
async def scrape_sitemap(url: str, max_pages: int = 20) -> str:
    result = await sitemap_scraper.scrape_sitemap(url, max_pages)
    if result.error:
        return f"Error: {result.error}"
    return json.dumps(result.data, indent=2, ensure_ascii=False)


@mcp.tool()
def export(data: str, format: str = "csv") -> str:
    if len(data) > 10 * 1024 * 1024:
        return "Error: Data exceeds maximum size of 10MB"
    parsed = json.loads(data)
    if format == "csv":
        return to_csv(parsed)
    if format == "json":
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    if format == "markdown":
        return to_markdown(parsed)
    return json.dumps(parsed, indent=2)


def main():
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
