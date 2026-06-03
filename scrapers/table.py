from scrapers.base import BaseScraper, ScrapeResult


class TableScraper(BaseScraper):
    async def scrape_tables(self, url: str, selector: str = "table") -> ScrapeResult:
        try:
            soup, final_url = await self._fetch(url)
            tables = soup.select(selector)
            if not tables:
                return ScrapeResult(url=final_url, status=200, error="No tables matched the selector")

            result = []
            for i, table in enumerate(tables):
                rows = table.find_all("tr")
                if not rows:
                    continue

                headers = []
                header_row = rows[0].find_all(["th", "td"])
                if header_row and all(th.name == "th" for th in header_row):
                    headers = [th.get_text(strip=True) for th in header_row]
                    data_rows = rows[1:]
                else:
                    data_rows = rows

                items = []
                for row in data_rows:
                    cells = row.find_all(["td", "th"])
                    if headers:
                        item = {}
                        for j, cell in enumerate(cells):
                            key = headers[j] if j < len(headers) else f"col_{j}"
                            item[key] = cell.get_text(strip=True)
                    else:
                        item = [cell.get_text(strip=True) for cell in cells]
                    items.append(item)

                result.append({
                    "index": i,
                    "headers": headers,
                    "rows": len(items),
                    "cols": max(len(h) for h in [headers] + items) if items else 0,
                    "data": items,
                })

            return ScrapeResult(url=final_url, status=200, data=result)
        except Exception as e:
            return ScrapeResult(url=url, status=0, error=str(e))
