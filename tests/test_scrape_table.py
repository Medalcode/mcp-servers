import pytest
from bs4 import BeautifulSoup
from scrapers.table import TableScraper


class MockTableScraper(TableScraper):
    def __init__(self, html, url="https://example.com"):
        super().__init__()
        self._html = html
        self._url = url

    async def _fetch(self, url):
        return BeautifulSoup(self._html, "html5lib"), self._url


@pytest.mark.anyio
async def test_table_with_headers():
    html = """
    <table>
        <tr><th>Name</th><th>Age</th></tr>
        <tr><td>Alice</td><td>30</td></tr>
        <tr><td>Bob</td><td>25</td></tr>
    </table>
    """
    scraper = MockTableScraper(html)
    result = await scraper.scrape_tables("https://example.com")
    assert result.status == 200
    data = result.data
    assert len(data) == 1
    assert data[0]["headers"] == ["Name", "Age"]
    assert len(data[0]["data"]) == 2
    assert data[0]["data"][0]["Name"] == "Alice"


@pytest.mark.anyio
async def test_table_without_headers():
    html = """
    <table>
        <tr><td>X</td><td>1</td></tr>
        <tr><td>Y</td><td>2</td></tr>
    </table>
    """
    scraper = MockTableScraper(html)
    result = await scraper.scrape_tables("https://example.com")
    assert result.status == 200
    data = result.data
    assert len(data) == 1
    assert data[0]["headers"] == []
    assert data[0]["data"][0] == ["X", "1"]


@pytest.mark.anyio
async def test_table_custom_selector():
    html = """
    <div class="data-table">
        <table>
            <tr><th>Col</th></tr>
            <tr><td>Val</td></tr>
        </table>
    </div>
    <table><tr><td>Other</td></tr></table>
    """
    scraper = MockTableScraper(html)
    result = await scraper.scrape_tables("https://example.com", ".data-table table")
    assert result.status == 200
    assert len(result.data) == 1
    assert result.data[0]["data"][0]["Col"] == "Val"


@pytest.mark.anyio
async def test_table_no_match():
    scraper = MockTableScraper("<html><body>No table</body></html>")
    result = await scraper.scrape_tables("https://example.com")
    assert result.error is not None
    assert "No tables matched" in result.error
