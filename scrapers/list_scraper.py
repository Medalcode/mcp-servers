import asyncio
import logging
import os
import time
from collections import deque
from urllib.parse import urljoin, urlparse

from scrapers.base import BaseScraper, ScrapeResult

logger = logging.getLogger("scrapemcp.list_scraper")

_MAX_RECURSIVE_PAGES = int(os.getenv("MAX_RECURSIVE_PAGES", "10"))
_RECURSIVE_DELAY = float(os.getenv("RECURSIVE_DELAY", "1"))


class ListScraper(BaseScraper):
    async def scrape_list(self, url: str, item_selector: str, fields: dict[str, str]) -> ScrapeResult:
        try:
            soup, final_url = await self._fetch(url)
            items = soup.select(item_selector)
            if not items:
                return ScrapeResult(url=final_url, status=200, error="No items matched the selector")

            result = []
            for item in items:
                entry = {}
                for key, selector in fields.items():
                    el = item.select_one(selector)
                    if el:
                        if el.name == "a" and el.get("href"):
                            entry[key] = {
                                "text": el.get_text(strip=True),
                                "href": urljoin(final_url, el["href"]),
                            }
                        elif el.name == "img" and el.get("src"):
                            entry[key] = {
                                "alt": el.get("alt", ""),
                                "src": urljoin(final_url, el["src"]),
                            }
                        else:
                            entry[key] = el.get_text(strip=True)
                    else:
                        entry[key] = None
                result.append(entry)

            return ScrapeResult(url=final_url, status=200, data={
                "count": len(result),
                "items": result,
            })
        except Exception as e:
            return ScrapeResult(url=url, status=0, error=str(e))

    async def scrape_recursive(self, start_url: str, link_selector: str, item_selector: str,
                                fields: dict[str, str], max_pages: int = 10) -> ScrapeResult:
        visited = set()
        all_items = []
        to_visit = deque([start_url])
        pages = 0
        start_time = time.monotonic()
        total_timeout = 120.0

        while to_visit and pages < max_pages:
            if time.monotonic() - start_time > total_timeout:
                logger.warning("Total timeout reached, stopping crawl")
                break

            url = to_visit.popleft()
            if url in visited:
                continue
            visited.add(url)

            try:
                soup, final_url = await self._fetch(url)
                items = soup.select(item_selector)
                for item in items:
                    entry = {}
                    for key, selector in fields.items():
                        el = item.select_one(selector)
                        entry[key] = el.get_text(strip=True) if el else None
                    all_items.append(entry)

                logger.info("Scraped page %d: %s", pages + 1, url)

                for link in soup.select(link_selector):
                    href = link.get("href")
                    if href:
                        full = urljoin(final_url, href)
                        if full not in visited and urlparse(full).netloc == urlparse(start_url).netloc:
                            to_visit.append(full)

                pages += 1
                await asyncio.sleep(_RECURSIVE_DELAY)
            except Exception:
                logger.exception("Failed to scrape page: %s", url)
                continue

        return ScrapeResult(url=start_url, status=200, data={
            "pages_scraped": pages,
            "total_items": len(all_items),
            "items": all_items,
        }, pages_scraped=pages)
