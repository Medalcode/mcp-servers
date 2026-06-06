import pytest
from bs4 import BeautifulSoup
from scrapers.page import PageScraper
from scrapers.base import ScrapeResult


class MockPageScraper(PageScraper):
    def __init__(self, html, url="https://example.com"):
        super().__init__()
        self._html = html
        self._url = url

    async def _fetch(self, url):
        return BeautifulSoup(self._html, "html5lib"), self._url


@pytest.mark.anyio
async def test_scrape_page_basic():
    html = "<html><head><title>Test</title></head><body><p>Hello world</p></body></html>"
    scraper = MockPageScraper(html)
    result = await scraper.scrape("https://example.com")
    assert result.status == 200
    assert result.data["title"] == "Test"
    assert "Hello world" in result.data["text"]
    assert result.data["word_count"] > 0


@pytest.mark.anyio
async def test_scrape_page_custom_selectors():
    html = '<html><body><div class="item">A</div><div class="item">B</div></body></html>'
    scraper = MockPageScraper(html)
    result = await scraper.scrape("https://example.com", {"items": ".item"})
    assert result.status == 200
    assert len(result.data["items"]) == 2
    assert result.data["items"][0]["text"] == "A"


@pytest.mark.anyio
async def test_scrape_page_no_title():
    html = "<html><body><p>No title here</p></body></html>"
    scraper = MockPageScraper(html)
    result = await scraper.scrape("https://example.com")
    assert result.data["title"] == ""


@pytest.mark.anyio
async def test_scrape_page_meta():
    html = '<html><head><meta name="description" content="A test page"></head><body><p>Content</p></body></html>'
    scraper = MockPageScraper(html)
    result = await scraper.scrape("https://example.com")
    assert result.data["meta"]["description"] == "A test page"


@pytest.mark.anyio
async def test_inspect_page():
    html = "<html><head><title>Test</title></head><body><h1>Heading</h1><p>Text</p><a href='/link'>Link</a></body></html>"
    scraper = MockPageScraper(html)
    result = await scraper.inspect("https://example.com")
    assert result.data["title"] == "Test"
    assert result.data["links"] == 1
    assert result.data["headings"]["h1"] == 1
