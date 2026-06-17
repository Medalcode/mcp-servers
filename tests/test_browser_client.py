import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call


@pytest.fixture(autouse=True)
def _reset_globals():
    from services import browser_client
    browser_client._browser_proc = None
    browser_client._next_req_id = 1


class TestEnsureBrowser:
    @patch("services.browser_client.sys.executable", "/usr/bin/python3")
    @patch("services.browser_client.asyncio.create_subprocess_exec")
    async def test_starts_subprocess(self, mock_create_subprocess):
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.stdout.readline = AsyncMock(side_effect=[
            b'{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}\n',
            b"",
        ])
        mock_proc.stdin.drain = AsyncMock()
        mock_create_subprocess.return_value = mock_proc

        from services.browser_client import ensure_browser
        result = await ensure_browser()

        assert result is mock_proc
        mock_create_subprocess.assert_called_once()
        args, kwargs = mock_create_subprocess.call_args
        assert "-m" in args
        assert "servers.browser" in args

    @patch("services.browser_client.sys.executable", "/usr/bin/python3")
    @patch("services.browser_client.asyncio.create_subprocess_exec")
    async def test_returns_existing_process(self, mock_create_subprocess):
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.stdout.readline = AsyncMock(return_value=b"")
        mock_proc.stdin.drain = AsyncMock()
        with patch("services.browser_client._browser_proc", mock_proc):
            from services.browser_client import ensure_browser
            result = await ensure_browser()
            assert result is mock_proc
            mock_create_subprocess.assert_not_called()


class TestCallTool:
    @patch("services.browser_client.ensure_browser")
    async def test_calls_tool_and_returns_text(self, mock_ensure):
        mock_proc = MagicMock()
        mock_proc.stdin.write = MagicMock()
        mock_proc.stdin.drain = AsyncMock()
        mock_proc.stdout.readline = AsyncMock(side_effect=[
            b'{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"Hello world"}]}}\n',
            b"",
        ])
        mock_ensure.return_value = mock_proc

        from services.browser_client import call_tool
        result = await call_tool("navigate", {"url": "http://example.com"})

        assert result == "Hello world"
        write_call = mock_proc.stdin.write.call_args[0][0]
        assert b"navigate" in write_call
        assert b"example.com" in write_call

    @patch("services.browser_client.ensure_browser")
    async def test_retries_on_timeout(self, mock_ensure):
        mock_proc = MagicMock()
        mock_proc.stdin.write = MagicMock()
        mock_proc.stdin.drain = AsyncMock()
        mock_proc.stdout.readline = AsyncMock(return_value=b"")
        mock_ensure.return_value = mock_proc

        with patch("services.browser_client.reset_browser", AsyncMock()):
            from services.browser_client import call_tool
            result = await call_tool("navigate", {}, max_retries=1)

        assert "failed after 2 attempts" in result

    @patch("services.browser_client.ensure_browser")
    async def test_returns_error_from_response(self, mock_ensure):
        error_response = b'{"jsonrpc":"2.0","id":1,"error":{"code":-32603,"message":"Internal error"}}\n'
        mock_proc = MagicMock()
        mock_proc.stdin.write = MagicMock()
        mock_proc.stdin.drain = AsyncMock()
        mock_proc.stdout.readline = AsyncMock(return_value=error_response)
        mock_ensure.return_value = mock_proc

        with patch("services.browser_client.reset_browser", AsyncMock()):
            from services.browser_client import call_tool
            result = await call_tool("navigate", max_retries=0)

        assert "BrowserMCP error" in result


class TestResetBrowser:
    async def test_resets_global(self):
        from services.browser_client import reset_browser
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.wait = AsyncMock()
        with patch("services.browser_client._browser_proc", mock_proc):
            with patch("services.browser_client.signal") as mock_signal:
                await reset_browser()
                mock_proc.send_signal.assert_called_once_with(mock_signal.SIGTERM)

    async def test_reset_no_process(self):
        from services.browser_client import reset_browser
        with patch("services.browser_client._browser_proc", None):
            await reset_browser()
