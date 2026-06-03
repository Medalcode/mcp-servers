import re
from urllib.parse import urljoin

from scrapers.base import BaseScraper, ScrapeResult


class PageScraper(BaseScraper):
    async def scrape(self, url: str, selectors: dict[str, str] | None = None) -> ScrapeResult:
        try:
            soup, final_url = await self._fetch(url)
            result = {}

            if selectors:
                for key, selector in selectors.items():
                    elements = soup.select(selector)
                    result[key] = [
                        {
                            "text": el.get_text(strip=True),
                            "html": str(el),
                            "attrs": el.attrs,
                        }
                        for el in elements
                    ]
            else:
                result = {
                    "title": soup.title.string.strip() if soup.title and soup.title.string else "",
                    "meta": self._extract_meta(soup),
                    "text": re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))[:5000],
                    "word_count": len(soup.get_text(separator=" ", strip=True).split()),
                }

            return ScrapeResult(url=final_url, status=200, data=result)
        except Exception as e:
            return ScrapeResult(url=url, status=0, error=str(e))

    async def inspect(self, url: str) -> ScrapeResult:
        try:
            soup, final_url = await self._fetch(url)
            return ScrapeResult(url=final_url, status=200, data={
                "title": soup.title.string.strip() if soup.title and soup.title.string else "",
                "meta_tags": len(soup.find_all("meta")),
                "headings": {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)},
                "links": len(soup.find_all("a", href=True)),
                "images": len(soup.find_all("img")),
                "tables": len(soup.find_all("table")),
                "forms": len(soup.find_all("form")),
                "scripts": len(soup.find_all("script")),
                "stylesheets": len(soup.find_all("link", rel="stylesheet")),
                "word_count": len(soup.get_text(separator=" ", strip=True).split()),
                "has_json_ld": bool(soup.find("script", type="application/ld+json")),
                "charset": str(soup.original_encoding),
            })
        except Exception as e:
            return ScrapeResult(url=url, status=0, error=str(e))

    def _extract_meta(self, soup) -> dict:
        meta = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property") or ""
            content = tag.get("content", "")
            if name and content:
                meta[name] = content
        return meta
