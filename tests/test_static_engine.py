from engines.static import StaticEngine


class MockResponse:
    def __init__(self, text, url, headers=None):
        self.content = text.encode()
        self.text = text
        self.url = url
        self.headers = headers or {"content-type": "text/html"}
    def raise_for_status(self):
        pass


class MockSession:
    def __init__(self, mock_response):
        self.headers = {}
        self.mock_response = mock_response
    def get(self, url, timeout=15):
        return self.mock_response
    def close(self):
        pass


def test_static_engine_links():
    html = '<html><body><a href="/test">Link 1</a><a href="https://external.com">Link 2</a></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))

    engine.navigate("https://example.com")
    links = engine.get_links()

    assert len(links) == 2
    assert links[0].href == "https://example.com/test"
    assert links[0].is_internal is True
    assert links[1].href == "https://external.com"
    assert links[1].is_internal is False


def test_static_engine_extract():
    html = '<html><body><p class="text">Hello</p><p class="text">World</p></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))
    engine.navigate("https://example.com")
    result = engine.extract(".text")
    assert result == ["Hello", "World"]


def test_static_engine_extract_empty():
    engine = StaticEngine()
    result = engine.extract(".nonexistent")
    assert result == []


def test_static_engine_forms():
    html = '<html><body><form action="/submit"><input type="text" name="name"><input type="email" name="email" required></form></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))
    engine.navigate("https://example.com")
    forms = engine.get_forms()
    assert len(forms) == 1
    assert forms[0].action == "/submit"
    assert forms[0].method == "GET"
    assert len(forms[0].fields) == 2
    assert forms[0].fields[0].name == "name"
    assert forms[0].fields[1].name == "email"
    assert forms[0].fields[1].required is True


def test_static_engine_forms_label():
    html = '<html><body><form><label for="name">Nombre:</label><input id="name" type="text" name="name"></form></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))
    engine.navigate("https://example.com")
    forms = engine.get_forms()
    assert len(forms) == 1
    assert forms[0].fields[0].label == "Nombre:"


def test_static_engine_forms_parent_label():
    html = '<html><body><form><label>Email:<input type="email" name="email"></label></form></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))
    engine.navigate("https://example.com")
    forms = engine.get_forms()
    assert len(forms) == 1
    assert forms[0].fields[0].label == "Email:"


def test_static_engine_navigate_title():
    html = '<html><head><title>Test Page</title></head><body><p>Content</p></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))
    result = engine.navigate("https://example.com")
    assert result.title == "Test Page"
    assert "Content" in result.text


def test_static_engine_navigate_no_title():
    html = '<html><body><p>No title</p></body></html>'
    engine = StaticEngine()
    engine._session = MockSession(MockResponse(html, "https://example.com"))
    result = engine.navigate("https://example.com")
    assert result.title == ""


def test_static_engine_navigate_not_html():
    engine = StaticEngine()
    resp = MockResponse("plain text", "https://example.com/file.txt", {"content-type": "text/plain"})
    engine._session = MockSession(resp)
    result = engine.navigate("https://example.com/file.txt")
    assert result.error is not None
    assert "Not HTML" in result.error


def test_static_engine_click_returns_message():
    engine = StaticEngine()
    assert "requires a browser engine" in engine.click("button")


def test_static_engine_fill_returns_message():
    engine = StaticEngine()
    assert "requires a browser engine" in engine.fill("#input", "value")


def test_static_engine_scroll_returns_message():
    engine = StaticEngine()
    assert "requires a browser engine" in engine.scroll("down")


def test_static_engine_wait_returns_message():
    engine = StaticEngine()
    assert "requires a browser engine" in engine.wait(1000)


def test_static_engine_screenshot_returns_none():
    engine = StaticEngine()
    assert engine.screenshot() is None
