import asyncio
import ipaddress
import logging
import os
import re
import socket
import time
from urllib.parse import urlparse

from engines.selenium_engine import SeleniumEngine
from engines.base import BrowserEngine

logger = logging.getLogger(__name__)

_engine: BrowserEngine | None = None
_engine_lock = asyncio.Lock()

_PRIVATE_BLOCKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
_BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal", "169.254.169.254"}
_DNS_CACHE: dict[str, tuple[bool, float]] = {}
_DNS_CACHE_TTL = 300
_DNS_CACHE_MAX = 500


def _dns_cache_cleanup():
    now = time.monotonic()
    stale = [k for k, (_, ts) in _DNS_CACHE.items() if now - ts > _DNS_CACHE_TTL]
    for k in stale:
        del _DNS_CACHE[k]


def _dns_cache_set(key: str, value: bool):
    if len(_DNS_CACHE) >= _DNS_CACHE_MAX:
        _dns_cache_cleanup()
    _DNS_CACHE[key] = (value, time.monotonic())


def _is_private_hostname(hostname: str) -> bool:
    if not hostname:
        return False
    cache_key = hostname.lower()
    cached = _DNS_CACHE.get(cache_key)
    if cached is not None:
        value, ts = cached
        if time.monotonic() - ts <= _DNS_CACHE_TTL:
            return value
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5)
        try:
            addrinfo = socket.getaddrinfo(hostname, None)
        finally:
            socket.setdefaulttimeout(old_timeout)
        for _, _, _, _, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            addr = ipaddress.ip_address(ip_str)
            for block in _PRIVATE_BLOCKS:
                if addr in block:
                    _dns_cache_set(cache_key, True)
                    return True
    except (socket.gaierror, OSError):
        pass
    _dns_cache_set(cache_key, False)
    return False


def _dns_resolves(hostname: str) -> bool:
    if not hostname:
        return False
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except socket.gaierror:
        return False


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed (only http/https)")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials not allowed (user:password@host)")
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname: {hostname}")
    if re.search(r"\.internal$|\.local$|\.localhost$|\.test$", hostname.lower()):
        raise ValueError(f"Blocked domain: {hostname}")
    if hostname and _is_private_hostname(hostname):
        raise ValueError(f"Blocked private IP range for hostname: {hostname}")
    try:
        addr = ipaddress.ip_address(hostname)
        for block in _PRIVATE_BLOCKS:
            if addr in block:
                raise ValueError(f"Blocked private IP: {hostname}")
    except ValueError:
        if not _dns_resolves(hostname):
            raise ValueError(f"Hostname does not resolve: {hostname}")


def _validate_final_url(result_url: str) -> str | None:
    if not result_url:
        return None
    parsed = urlparse(result_url)
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return f"Navigation redirected to blocked hostname: {hostname}"
    if hostname and _is_private_hostname(hostname):
        return f"Navigation redirected to private IP: {hostname}"
    return None


_BLOCKED_JS_PATTERNS = [
    r"\bfetch\s*\(",
    r"\bxmlhttprequest\b",
    r"\bwebsocket\b",
    r"\bfilereader\b",
    r"\bimportscripts\b",
    r"\bworker\b",
    r"\bnavigator\.sendbeacon\b",
    r"\bdocument\.write\b",
    r"\bdocument\.open\b",
    r"\btop\.",
    r"\bparent\.",
    r"\b(alert|confirm|prompt)\s*\(",
]


def _validate_script(script: str) -> None:
    dangerous = [
        "eval", "function", "settimeout", "setinterval",
        "new function", "reflect.construct",
        "import(", "importscripts",
    ]
    script_lower = script.lower()
    for keyword in dangerous:
        if keyword in script_lower:
            raise ValueError(f"Script blocked: contains dangerous API '{keyword}'")
    for pattern in _BLOCKED_JS_PATTERNS:
        if re.search(pattern, script_lower):
            raise ValueError("Script blocked: contains dangerous API")


async def ensure_browser() -> None:
    global _engine
    async with _engine_lock:
        if _engine is not None:
            return
        _engine = SeleniumEngine()
        logger.info("Browser engine initialized: selenium")


async def call_tool(tool: str, args: dict | None = None, max_retries: int = 2) -> str:
    args = args or {}

    for attempt in range(max_retries + 1):
        try:
            await ensure_browser()
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(1 * (attempt + 1))
                continue
            return f"Browser init failed after {max_retries + 1} attempts: {e}"

        try:
            result = await _run_on_engine(tool, args)
            return _format_result(result)
        except ValueError as e:
            return f"BrowserMCP error: {e}"
        except Exception as e:
            logger.error("Browser tool %s failed (attempt %d/%d): %s", tool, attempt + 1, max_retries + 1, e)
            if attempt < max_retries:
                await reset_browser()
                await asyncio.sleep(1 * (attempt + 1))
                continue
            return f"BrowserMCP failed after {max_retries + 1} attempts: {e}"

    return "BrowserMCP failed: max retries exceeded"


def _run_sync(method, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, lambda: method(*args, **kwargs))


async def _run_on_engine(tool: str, args: dict):
    global _engine

    if tool == "navigate":
        url = args["url"]
        _validate_url(url)
        result = await _run_sync(_engine.navigate, url)
        redirect_error = _validate_final_url(result.url)
        if redirect_error:
            return redirect_error
        return f"Title: {result.title}\nURL: {result.url}\n---\n{result.text}"

    elif tool == "extract":
        selector = args["selector"]
        results = await _run_sync(_engine.extract, selector)
        if not results:
            return "No elements matched"
        return "\n---\n".join(results)

    elif tool == "links":
        links = await _run_sync(_engine.get_links)
        if not links:
            return "No links found"
        lines = []
        for i, link in enumerate(links, 1):
            icon = "🔗" if link.is_internal else "🌐"
            lines.append(f"{i}. {icon} {link.text or '(no text)'}")
            lines.append(f"   {link.href}")
        return "\n".join(lines)

    elif tool == "forms":
        forms_list = await _run_sync(_engine.get_forms)
        if not forms_list:
            return "No forms found"
        output = []
        for i, form in enumerate(forms_list, 1):
            output.append(f"Form #{i}: {form.method} -> {form.action}")
            for field in form.fields:
                req = " *" if field.required else ""
                output.append(f"  [{field.tag}] {field.name} ({field.type}){req}")
                if field.label:
                    output.append(f"       Label: {field.label}")
        return "\n".join(output)

    elif tool == "screenshot":
        data = await _run_sync(_engine.screenshot)
        if data is None:
            return "Screenshot not available"
        import base64
        max_bytes = int(os.environ.get("BROWSER_SCREENSHOT_MAX_BYTES", "5242880"))
        if len(data) > max_bytes:
            return f"Screenshot too large ({len(data)} bytes, max {max_bytes})"
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"

    elif tool == "click":
        selector = args["selector"]
        result = await _run_sync(_engine.click, selector)
        return result

    elif tool == "click_by_text":
        text = args["text"]
        result = await _run_sync(_engine.click_by_text, text)
        return result

    elif tool == "run_script":
        script = args["script"]
        _validate_script(script)
        result = await _run_sync(_engine.run_script, script)
        return result

    elif tool == "fill":
        selector = args["selector"]
        value = args["value"]
        result = await _run_sync(_engine.fill, selector, value)
        return result

    elif tool == "scroll":
        direction = args.get("direction", "down")
        result = await _run_sync(_engine.scroll, direction)
        return result

    elif tool == "wait":
        ms = args.get("ms", 1000)
        result = await _run_sync(_engine.wait, ms)
        return result

    elif tool == "engine_info":
        return f"Active engine: {_engine.name}"

    elif tool == "browser_health_check":
        return f"BrowserMCP OK: Active engine: {_engine.name}"

    else:
        raise ValueError(f"Unknown tool: {tool}")


def _format_result(result) -> str:
    if result is None:
        return "OK"
    return str(result)


async def reset_browser() -> None:
    global _engine
    async with _engine_lock:
        if _engine is not None:
            try:
                await _run_sync(_engine.close)
            except Exception as e:
                logger.warning("reset_browser: %s", e)
            _engine = None


async def stop_browser() -> None:
    await reset_browser()
