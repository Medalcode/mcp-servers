import os
import re
import xml.etree.ElementTree as ET

from scrapers.base import BaseScraper, ScrapeResult

_SITEMAP_URL_LIMIT = int(os.getenv("SITEMAP_URL_LIMIT", "50"))


class SitemapScraper(BaseScraper):
    async def parse_sitemap(self, url: str) -> ScrapeResult:
        try:
            base = url.rstrip("/")

            sitemap_url = None
            try:
                robots_resp = await self._session.get(base + "/robots.txt", follow_redirects=True)
                if robots_resp.status_code == 200:
                    for line in robots_resp.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

            if not sitemap_url:
                sitemap_url = base + "/sitemap.xml"

            resp = await self._session.get(sitemap_url, follow_redirects=True)
            resp.raise_for_status()

            try:
                root = ET.fromstring(resp.content)
            except ET.ParseError as e:
                return ScrapeResult(url=sitemap_url, status=0, error=f"XML parse error: {e}")

            ns_match = re.match(r"\{(.*)\}", root.tag)
            ns = {"ns": ns_match.group(1)} if ns_match else {}

            urls = []
            if ns:
                for url_elem in root.findall(".//ns:url", ns):
                    loc = url_elem.find("ns:loc", ns)
                    if loc is not None and loc.text:
                        urls.append(loc.text)
                if not urls:
                    for sitemap_elem in root.findall(".//ns:sitemap", ns):
                        loc = sitemap_elem.find("ns:loc", ns)
                        if loc is not None and loc.text:
                            urls.append(loc.text)
            else:
                for url_elem in root.findall(".//url"):
                    loc = url_elem.find("loc")
                    if loc is not None and loc.text:
                        urls.append(loc.text)
                if not urls:
                    for sitemap_elem in root.findall(".//sitemap"):
                        loc = sitemap_elem.find("loc")
                        if loc is not None and loc.text:
                            urls.append(loc.text)

            return ScrapeResult(url=sitemap_url, status=200, data={
                "total": len(urls),
                "urls": urls,
            })
        except Exception as e:
            return ScrapeResult(url=url, status=0, error=str(e))

    async def scrape_sitemap(self, url: str, max_pages: int = 20) -> ScrapeResult:
        sitemap_result = await self.parse_sitemap(url)
        if sitemap_result.error:
            return sitemap_result

        all_urls = sitemap_result.data["urls"][:max_pages]
        pages = []
        for page_url in all_urls:
            try:
                soup, final_url = await self._fetch(page_url)
                pages.append({
                    "url": final_url,
                    "title": soup.title.string.strip() if soup.title and soup.title.string else "",
                    "word_count": len(soup.get_text(separator=" ", strip=True).split()),
                })
            except Exception:
                pages.append({"url": page_url, "error": "Failed to fetch"})

        return ScrapeResult(url=url, status=200, data={
            "total_in_sitemap": sitemap_result.data["total"],
            "scraped": len(pages),
            "pages": pages,
        }, pages_scraped=len(pages))
