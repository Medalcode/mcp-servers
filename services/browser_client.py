import asyncio
import json
import logging
import os
import signal
import sys
import time

logger = logging.getLogger(__name__)

MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_browser_proc: asyncio.subprocess.Process = None
_browser_proc_lock = asyncio.Lock()
_next_req_id = 1
_req_id_lock = asyncio.Lock()


async def _next_id() -> int:
    global _next_req_id
    async with _req_id_lock:
        cur = _next_req_id
        _next_req_id += 1
        return cur


async def _consume_stderr(proc) -> None:
    try:
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            text = line.decode().rstrip()
            if text:
                logger.debug("BrowserMCP stderr: %s", text)
    except Exception:
        pass


async def _read_json_response(proc, timeout=60) -> None:
    buf = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(proc.stdout.readline(), timeout=min(2.0, remaining))
        except asyncio.TimeoutError:
            continue
        if not raw:
            break
        line = raw.decode(errors="replace")
        buf += line
        stripped = buf.strip()
        if not stripped.startswith("{"):
            continue
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            if stripped.count("{") == stripped.count("}"):
                logger.warning("Balanced braces but JSON invalid: %s...", stripped[:100])
            continue
    raise TimeoutError("No valid JSON response from browser")


async def ensure_browser() -> asyncio.subprocess.Process:
    global _browser_proc
    async with _browser_proc_lock:
        if _browser_proc is not None and _browser_proc.returncode is None:
            return _browser_proc
        _SAFE_ENV_KEYS = {
            "BROWSER_ENGINE", "BROWSER_HEADLESS", "BROWSER_NO_SANDBOX", "BROWSER_STEALTH",
            "BROWSER_TEXT_MAX", "BROWSER_SCREENSHOT_MAX_BYTES",
            "CHROME_USER_DATA_DIR", "CHROME_WINDOW_SIZE", "CHROME_LANG",
            "CHROME_DEBUG_PORT", "CHROME_DEBUG_HOST", "CHROMEDRIVER_PATH",
            "DISPLAY", "XAUTHORITY",
            "SELENIUM_REMOTE_URL", "PATH", "HOME", "USER",
            "LANG", "LC_ALL", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS",
            "PYTHONPATH", "TMPDIR"
        }
        env = {k: os.environ[k] for k in _SAFE_ENV_KEYS if k in os.environ}
        env.update({
            "BROWSER_ENGINE": "selenium",
            "BROWSER_NO_SANDBOX": "true",
            "BROWSER_STEALTH": "true",
        })
        _browser_proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "servers.browser",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=MCP_DIR,
            env=env,
        )
        asyncio.ensure_future(_consume_stderr(_browser_proc))
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                               "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                          "clientInfo": {"name": "browserclient", "version": "0.1.0"}}}) + "\n"
        _browser_proc.stdin.write(init_req.encode())
        await _browser_proc.stdin.drain()
        resp = await _read_json_response(_browser_proc, timeout=10)
        logger.debug("BrowserMCP init: %s", str(resp.get("result", {}))[:100] if resp else "None")
        init_notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n"
        _browser_proc.stdin.write(init_notif.encode())
        await _browser_proc.stdin.drain()
    return _browser_proc


async def call_tool(tool: str, args: dict = None, max_retries: int = 2) -> str:
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            proc = await ensure_browser()
            req_id = await _next_id()
            req = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                              "params": {"name": tool, "arguments": args or {}}}) + "\n"
            proc.stdin.write(req.encode())
            await proc.stdin.drain()
            data = await _read_json_response(proc, timeout=60)
            if data.get("id") == req_id:
                if "error" in data:
                    raise RuntimeError(f"BrowserMCP error: {data['error']}")
                content = data.get("result", {}).get("content", [])
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return "\n".join(texts)
            logger.debug("Skipping response for id=%s", data.get("id"))
        except (asyncio.TimeoutError, TimeoutError) as e:
            last_error = str(e)
            logger.error("BrowserMCP timeout for %s (attempt %d/%d)", tool, attempt + 1, max_retries + 1)
            await reset_browser()
            if attempt < max_retries:
                await asyncio.sleep(1 * (attempt + 1))
        except Exception as e:
            last_error = str(e)
            logger.error("BrowserMCP call failed: %s (attempt %d/%d)", e, attempt + 1, max_retries + 1)
            await reset_browser()
            if attempt < max_retries:
                await asyncio.sleep(1 * (attempt + 1))
    return f"BrowserMCP failed after {max_retries + 1} attempts: {last_error}"


async def reset_browser() -> None:
    global _browser_proc
    async with _browser_proc_lock:
        if _browser_proc and _browser_proc.returncode is None:
            try:
                _browser_proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(_browser_proc.wait(), timeout=10)
                except asyncio.TimeoutError:
                    _browser_proc.kill()
                    await _browser_proc.wait()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning("reset_browser: %s", e)
        _browser_proc = None


async def stop_browser() -> None:
    await reset_browser()
