import pytest
from bs4 import BeautifulSoup
from scrapers.list_scraper import ListScraper


class MockListScraper(ListScraper):
    def __init__(self, html, url="https://example.com"):
        super().__init__()
        self._html = html
        self._url = url

    async def _fetch(self, url):
        return BeautifulSoup(self._html, "html5lib"), self._url


@pytest.mark.anyio
async def test_scrape_list_basic():
    html = """
    <ul>
        <li class="item"><h2 class="title">Item 1</h2><span class="price">$10</span></li>
        <li class="item"><h2 class="title">Item 2</h2><span class="price">$20</span></li>
    </ul>
    """
    scraper = MockListScraper(html)
    result = await scraper.scrape_list("https://example.com", ".item", {
        "title": ".title",
        "price": ".price",
    })
    assert result.status == 200
    assert result.data["count"] == 2
    assert result.data["items"][0]["title"] == "Item 1"
    assert result.data["items"][1]["price"] == "$20"


@pytest.mark.anyio
async def test_scrape_list_with_links():
    html = '<div class="item"><a class="link" href="/page1">Page 1</a></div>'
    scraper = MockListScraper(html)
    result = await scraper.scrape_list("https://example.com", ".item", {
        "link": ".link",
    })
    assert result.data["items"][0]["link"]["text"] == "Page 1"
    assert "example.com/page1" in result.data["items"][0]["link"]["href"]


@pytest.mark.anyio
async def test_scrape_list_no_match():
    scraper = MockListScraper("<html><body>Nothing</body></html>")
    result = await scraper.scrape_list("https://example.com", ".item", {"t": ".title"})
    assert result.error is not None


@pytest.mark.anyio
async def test_scrape_list_optional_field():
    html = '<div class="item"><span class="a">A</span></div>'
    scraper = MockListScraper(html)
    result = await scraper.scrape_list("https://example.com", ".item", {
        "a": ".a",
        "b": ".b",
    })
    assert result.data["items"][0]["a"] == "A"
    assert result.data["items"][0]["b"] is None
