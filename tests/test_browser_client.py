import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def _reset_globals():
    from services import browser_client
    browser_client._engine = None


class TestEnsureBrowser:
    @patch("services.browser_client.SeleniumEngine")
    async def test_initializes_engine(self, mock_engine_cls):
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine

        from services.browser_client import ensure_browser
        await ensure_browser()

        mock_engine_cls.assert_called_once()

    @patch("services.browser_client.SeleniumEngine")
    async def test_does_not_reinitialize(self, mock_engine_cls):
        from services.browser_client import ensure_browser
        await ensure_browser()
        mock_engine_cls.reset_mock()
        await ensure_browser()
        mock_engine_cls.assert_not_called()


class TestCallTool:
    @patch("services.browser_client.SeleniumEngine")
    async def test_engine_info_needs_no_browser(self, mock_engine_cls):
        from services.browser_client import call_tool
        result = await call_tool("engine_info", {})
        assert "Active engine" in result

    @patch("services.browser_client.SeleniumEngine")
    async def test_navigate_validates_url(self, mock_engine_cls):
        from services.browser_client import call_tool
        result = await call_tool("navigate", {"url": "javascript:alert(1)"})
        assert "error" in result.lower()

    @patch("services.browser_client.SeleniumEngine")
    async def test_navigate_blocks_localhost(self, mock_engine_cls):
        from services.browser_client import call_tool
        result = await call_tool("navigate", {"url": "http://localhost:8080"})
        assert "blocked" in result.lower()

    @patch("services.browser_client.SeleniumEngine")
    async def test_run_script_validates_script(self, mock_engine_cls):
        from services.browser_client import call_tool
        result = await call_tool("run_script", {"script": "eval('x')"})
        assert "blocked" in result.lower()

    @patch("services.browser_client.SeleniumEngine")
    async def test_unknown_tool_returns_error(self, mock_engine_cls):
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine

        from services.browser_client import call_tool
        result = await call_tool("nonexistent_tool", {})
        assert "error" in result.lower()

    @patch("services.browser_client.SeleniumEngine")
    async def test_browser_health_check(self, mock_engine_cls):
        from services.browser_client import call_tool
        result = await call_tool("browser_health_check", {})
        assert "BrowserMCP OK" in result


class TestResetBrowser:
    @patch("services.browser_client.SeleniumEngine")
    async def test_resets_engine(self, mock_engine_cls):
        from services.browser_client import ensure_browser, reset_browser
        await ensure_browser()
        mock_engine = mock_engine_cls.return_value

        await reset_browser()
        mock_engine.close.assert_called_once()

    @patch("services.browser_client.SeleniumEngine")
    async def test_reset_no_engine(self, mock_engine_cls):
        from services.browser_client import reset_browser
        await reset_browser()
